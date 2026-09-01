import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  getAdminCustomerDetail,
  updateAdminCustomerStatus,
  getErrorMessage,
} from "../../services/api";
import RiskBadge from "../../components/RiskBadge";

const AdminCustomerDetail = () => {
  const { id } = useParams();
  const [customer, setCustomer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toggleLoading, setToggleLoading] = useState(false);
  const [feedback, setFeedback] = useState("");

  const fetchCustomer = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getAdminCustomerDetail(id);
      setCustomer(data);
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          "Failed to load customer profile details. Customer may not exist."
        )
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomer();
  }, [id]);

  const handleToggleStatus = async () => {
    if (!customer) return;
    const newStatus = !customer.is_verified;
    const confirmText = newStatus
      ? `Activate account for customer ${customer.phone}?`
      : `Deactivate account for customer ${customer.phone}? Customer will no longer be able to log in.`;

    if (!window.confirm(confirmText)) {
      return;
    }

    try {
      setToggleLoading(true);
      setFeedback("");
      const res = await updateAdminCustomerStatus(customer.id, newStatus);
      setCustomer((prev) => ({
        ...prev,
        ...res.customer,
      }));
      setFeedback(res.message);
      setTimeout(() => setFeedback(""), 4000);
    } catch (err) {
      alert(getErrorMessage(err, "Failed to update account status."));
    } finally {
      setToggleLoading(false);
    }
  };

  if (loading) {
    return (
      <div
        className="card-modern"
        style={{
          textAlign: "center",
          padding: "48px 24px",
          maxWidth: "1000px",
          margin: "0 auto",
        }}
      >
        <p style={{ color: "#64748b" }}>Loading customer profile...</p>
      </div>
    );
  }

  if (error || !customer) {
    return (
      <div
        className="card-modern"
        style={{
          maxWidth: "1000px",
          margin: "0 auto",
          borderColor: "#fecaca",
          backgroundColor: "#fef2f2",
        }}
      >
        <p style={{ color: "#dc2626", marginBottom: "12px" }}>{error}</p>
        <Link
          to="/admin/customers"
          className="btn-modern btn-modern-primary btn-modern-sm"
        >
          ← Back to Customers Directory
        </Link>
      </div>
    );
  }

  const successRate =
    customer.success_rate !== undefined
      ? `${customer.success_rate}%`
      : customer.total_orders > 0
      ? `${((customer.successful_deliveries / customer.total_orders) * 100).toFixed(1)}%`
      : "100%";

  const failureRate =
    customer.failure_rate !== undefined
      ? `${customer.failure_rate}%`
      : customer.total_orders > 0
      ? `${((customer.failed_deliveries / customer.total_orders) * 100).toFixed(1)}%`
      : "0%";

  const formattedDate = customer.created_at
    ? new Date(customer.created_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "N/A";

  const formattedLastDelivery = customer.last_successful_delivery
    ? new Date(customer.last_successful_delivery).toLocaleString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "No completed deliveries yet";

  const orders = customer.orders || [];

  return (
    <div
      className="animate-fade-in"
      style={{ maxWidth: "1080px", margin: "0 auto", paddingBottom: "48px" }}
    >
      {/* Breadcrumb Navigation */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          marginBottom: "16px",
          fontSize: "0.85rem",
          color: "#64748b",
        }}
      >
        <Link to="/admin/dashboard" style={{ color: "#64748b" }}>
          Dashboard
        </Link>
        <span>/</span>
        <Link to="/admin/customers" style={{ color: "#64748b" }}>
          Customers
        </Link>
        <span>/</span>
        <span style={{ color: "#0f172a", fontWeight: "600" }}>
          Customer #{customer.id}
        </span>
      </div>

      {feedback && (
        <div
          style={{
            padding: "10px 14px",
            background: "#f0fdf4",
            border: "1px solid #bbf7d0",
            borderRadius: "8px",
            color: "#16a34a",
            fontSize: "0.875rem",
            marginBottom: "16px",
          }}
        >
          {feedback}
        </div>
      )}

      {/* Customer Header Card */}
      <div
        className="card-modern"
        style={{ padding: "24px", marginBottom: "20px" }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: "16px",
            borderBottom: "1px solid #f1f5f9",
            paddingBottom: "18px",
            marginBottom: "18px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span
                style={{
                  fontSize: "1.45rem",
                  fontWeight: "700",
                  color: "#0f172a",
                }}
              >
                {customer.phone}
              </span>
              {customer.is_verified ? (
                <span
                  className="badge-modern badge-status success"
                  style={{ fontSize: "0.75rem", padding: "4px 10px" }}
                >
                  Verified Account
                </span>
              ) : (
                <span
                  className="badge-modern badge-status"
                  style={{
                    fontSize: "0.75rem",
                    padding: "4px 10px",
                    background: "#fffbeb",
                    color: "#d97706",
                    borderColor: "#fde68a",
                  }}
                >
                  Unverified
                </span>
              )}
            </div>

            <div
              style={{
                fontSize: "0.825rem",
                color: "#64748b",
                marginTop: "4px",
              }}
            >
              Customer ID: <strong>#{customer.id}</strong> • Member since:{" "}
              <strong>{formattedDate}</strong>
            </div>
          </div>

          <div style={{ display: "flex", gap: "8px" }}>
            <button
              type="button"
              onClick={handleToggleStatus}
              disabled={toggleLoading}
              className={`btn-modern btn-modern-sm ${
                customer.is_verified
                  ? "btn-modern-danger"
                  : "btn-modern-primary"
              }`}
            >
              {toggleLoading
                ? "Updating..."
                : customer.is_verified
                ? "Deactivate Account"
                : "Activate Account"}
            </button>
          </div>
        </div>

        {/* System Delivery Statistics Breakdown */}
        <div>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "12px",
            }}
          >
            <h2
              style={{
                fontSize: "0.95rem",
                fontWeight: "700",
                color: "#0f172a",
                margin: 0,
              }}
            >
              System-Calculated Delivery History
            </h2>
            <span
              style={{
                fontSize: "0.725rem",
                color: "#64748b",
                background: "#f8fafc",
                padding: "2px 8px",
                borderRadius: "4px",
                border: "1px solid #e2e8f0",
              }}
            >
              Immutable Operational Stats
            </span>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
              gap: "10px",
              marginBottom: "14px",
            }}
          >
            <div
              style={{
                padding: "12px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontSize: "0.725rem",
                  fontWeight: "600",
                  color: "#64748b",
                }}
              >
                Total Orders
              </span>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: "700",
                  color: "#0f172a",
                  marginTop: "2px",
                }}
              >
                {customer.total_orders ?? 0}
              </div>
            </div>

            <div
              style={{
                padding: "12px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontSize: "0.725rem",
                  fontWeight: "600",
                  color: "#64748b",
                }}
              >
                Successful
              </span>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: "700",
                  color: "#16a34a",
                  marginTop: "2px",
                }}
              >
                {customer.successful_deliveries ?? 0}
              </div>
            </div>

            <div
              style={{
                padding: "12px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontSize: "0.725rem",
                  fontWeight: "600",
                  color: "#64748b",
                }}
              >
                Failed
              </span>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: "700",
                  color: "#dc2626",
                  marginTop: "2px",
                }}
              >
                {customer.failed_deliveries ?? 0}
              </div>
            </div>

            <div
              style={{
                padding: "12px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontSize: "0.725rem",
                  fontWeight: "600",
                  color: "#64748b",
                }}
              >
                Unreachable
              </span>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: "700",
                  color: "#d97706",
                  marginTop: "2px",
                }}
              >
                {customer.unreachable_count ?? 0}
              </div>
            </div>

            <div
              style={{
                padding: "12px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontSize: "0.725rem",
                  fontWeight: "600",
                  color: "#64748b",
                }}
              >
                Cancellations
              </span>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: "700",
                  color: "#64748b",
                  marginTop: "2px",
                }}
              >
                {customer.cancellation_count ?? 0}
              </div>
            </div>

            <div
              style={{
                padding: "12px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontSize: "0.725rem",
                  fontWeight: "600",
                  color: "#64748b",
                }}
              >
                Success Rate
              </span>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: "700",
                  color: "#2563eb",
                  marginTop: "2px",
                }}
              >
                {successRate}
              </div>
            </div>

            <div
              style={{
                padding: "12px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontSize: "0.725rem",
                  fontWeight: "600",
                  color: "#64748b",
                }}
              >
                Failure Rate
              </span>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: "700",
                  color: "#475569",
                  marginTop: "2px",
                }}
              >
                {failureRate}
              </div>
            </div>
          </div>

          <div
            style={{
              fontSize: "0.8rem",
              color: "#64748b",
              background: "#f8fafc",
              padding: "8px 12px",
              borderRadius: "6px",
              border: "1px solid #e2e8f0",
            }}
          >
            Last Successful Delivery: <strong>{formattedLastDelivery}</strong>
          </div>
        </div>
      </div>

      {/* Customer Orders & Delivery History */}
      <div className="card-modern" style={{ padding: "24px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "16px",
          }}
        >
          <div>
            <h2
              style={{
                fontSize: "1.05rem",
                fontWeight: "700",
                color: "#0f172a",
                margin: 0,
              }}
            >
              Customer Order & Delivery History
            </h2>
            <p
              style={{
                fontSize: "0.825rem",
                color: "#64748b",
                margin: "3px 0 0",
              }}
            >
              All orders and corresponding delivery dispatches placed by this
              customer
            </p>
          </div>

          <span style={{ fontSize: "0.825rem", color: "#64748b" }}>
            Total Records: <strong>{orders.length}</strong>
          </span>
        </div>

        {orders.length === 0 ? (
          <div
            style={{
              padding: "36px 20px",
              textAlign: "center",
              background: "#f8fafc",
              borderRadius: "8px",
              border: "1px solid #e2e8f0",
            }}
          >
            <p style={{ color: "#64748b", margin: 0, fontSize: "0.875rem" }}>
              No orders found for this customer.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.85rem",
                textAlign: "left",
              }}
            >
              <thead>
                <tr
                  style={{
                    backgroundColor: "#f8fafc",
                    borderBottom: "1px solid #e2e8f0",
                    color: "#64748b",
                    fontSize: "0.75rem",
                    textTransform: "uppercase",
                  }}
                >
                  <th style={{ padding: "10px 12px" }}>Order ID</th>
                  <th style={{ padding: "10px 12px" }}>Placed Date</th>
                  <th style={{ padding: "10px 12px" }}>Item & Amount</th>
                  <th style={{ padding: "10px 12px" }}>Payment</th>
                  <th style={{ padding: "10px 12px" }}>Risk Level</th>
                  <th style={{ padding: "10px 12px" }}>Delivery Status</th>
                  <th style={{ padding: "10px 12px" }}>Assigned Rider</th>
                  <th style={{ padding: "10px 12px", textAlign: "right" }}>
                    Action
                  </th>
                </tr>
              </thead>
              <tbody>
                {orders.map((ord) => (
                  <tr
                    key={ord.id}
                    style={{
                      borderBottom: "1px solid #f1f5f9",
                    }}
                  >
                    <td style={{ padding: "10px 12px", fontWeight: "600" }}>
                      #{ord.id}
                    </td>
                    <td style={{ padding: "10px 12px", color: "#64748b" }}>
                      {ord.created_at
                        ? new Date(ord.created_at).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "—"}
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <div style={{ fontWeight: "600", color: "#0f172a" }}>
                        {ord.item_name}
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                        Qty: {ord.quantity} • Rs. {ord.total_price}
                      </div>
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <span
                        className="badge-modern badge-status"
                        style={{ fontSize: "0.7rem" }}
                      >
                        {ord.payment_method?.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      {ord.risk_level ? (
                        <RiskBadge risk={ord.risk_level} />
                      ) : (
                        <span style={{ color: "#94a3b8" }}>—</span>
                      )}
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      <span
                        className={`badge-modern badge-status ${
                          ord.delivery_status === "delivered"
                            ? "success"
                            : ord.delivery_status === "failed"
                            ? "danger"
                            : "active"
                        }`}
                        style={{ fontSize: "0.7rem" }}
                      >
                        {ord.delivery_status}
                      </span>
                    </td>
                    <td style={{ padding: "10px 12px" }}>
                      {ord.rider_name ? (
                        <div>
                          <span style={{ fontWeight: "600", color: "#0f172a" }}>
                            {ord.rider_name}
                          </span>
                          {ord.rider_phone && (
                            <div
                              style={{
                                fontSize: "0.725rem",
                                color: "#64748b",
                              }}
                            >
                              {ord.rider_phone}
                            </div>
                          )}
                        </div>
                      ) : (
                        <span style={{ color: "#94a3b8" }}>Unassigned</span>
                      )}
                    </td>
                    <td style={{ padding: "10px 12px", textAlign: "right" }}>
                      <Link
                        to="/admin/deliveries"
                        className="btn-modern btn-modern-secondary btn-modern-sm"
                        style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                      >
                        Deliveries
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminCustomerDetail;
