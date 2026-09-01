import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  getAdminCustomers,
  updateAdminCustomerStatus,
  getErrorMessage,
} from "../../services/api";

const AdminCustomers = () => {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [actionLoadingId, setActionLoadingId] = useState(null);
  const [actionMessage, setActionMessage] = useState("");

  const fetchCustomers = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getAdminCustomers();
      setCustomers(data || []);
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          "Failed to load customer list. Please verify backend connection."
        )
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
  }, []);

  const handleToggleStatus = async (customer) => {
    const newStatus = !customer.is_verified;
    const confirmText = newStatus
      ? `Activate account for customer ${customer.phone}?`
      : `Deactivate account for customer ${customer.phone}? Deactivated customers cannot log in.`;

    if (!window.confirm(confirmText)) {
      return;
    }

    try {
      setActionLoadingId(customer.id);
      setActionMessage("");
      const res = await updateAdminCustomerStatus(customer.id, newStatus);
      setCustomers((prev) =>
        prev.map((c) => (c.id === customer.id ? res.customer : c))
      );
      setActionMessage(res.message);
      setTimeout(() => setActionMessage(""), 4000);
    } catch (err) {
      alert(
        getErrorMessage(err, "Failed to update customer verification status.")
      );
    } finally {
      setActionLoadingId(null);
    }
  };

  // Filtered list
  const filteredCustomers = useMemo(() => {
    return customers.filter((c) => {
      const q = search.trim().toLowerCase();
      const matchesSearch =
        !q ||
        String(c.id).includes(q) ||
        String(c.phone || "").toLowerCase().includes(q);

      let matchesStatus = true;
      if (statusFilter === "verified") {
        matchesStatus = c.is_verified === true;
      } else if (statusFilter === "unverified") {
        matchesStatus = c.is_verified === false;
      }

      return matchesSearch && matchesStatus;
    });
  }, [customers, search, statusFilter]);

  // Overall metrics
  const totalCount = customers.length;
  const verifiedCount = customers.filter((c) => c.is_verified).length;
  const unverifiedCount = totalCount - verifiedCount;
  const totalOrdersSum = customers.reduce(
    (acc, c) => acc + (c.total_orders || 0),
    0
  );
  const successfulDeliveriesSum = customers.reduce(
    (acc, c) => acc + (c.successful_deliveries || 0),
    0
  );
  const avgSuccessRate =
    totalOrdersSum > 0
      ? ((successfulDeliveriesSum / totalOrdersSum) * 100).toFixed(1) + "%"
      : "100%";

  return (
    <div
      className="animate-fade-in"
      style={{ maxWidth: "1200px", margin: "0 auto", paddingBottom: "48px" }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
          marginBottom: "20px",
        }}
      >
        <div>
          <h1
            style={{
              fontSize: "1.65rem",
              fontWeight: "700",
              color: "#0f172a",
              margin: 0,
            }}
          >
            Customer Management
          </h1>
          <p
            style={{
              fontSize: "0.875rem",
              color: "#64748b",
              margin: "3px 0 0",
            }}
          >
            Registered customer accounts, verification status, and historical
            delivery statistics
          </p>
        </div>

        <button
          type="button"
          onClick={fetchCustomers}
          className="btn-modern btn-modern-secondary btn-modern-sm"
        >
          Refresh Directory
        </button>
      </div>

      {actionMessage && (
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
          {actionMessage}
        </div>
      )}

      {/* Summary Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "14px",
          marginBottom: "20px",
        }}
      >
        <div
          className="card-modern"
          style={{ padding: "16px 20px" }}
        >
          <span
            style={{
              fontSize: "0.75rem",
              fontWeight: "600",
              color: "#64748b",
            }}
          >
            Total Customers
          </span>
          <div
            style={{
              fontSize: "1.65rem",
              fontWeight: "700",
              color: "#0f172a",
              marginTop: "2px",
            }}
          >
            {totalCount}
          </div>
        </div>

        <div
          className="card-modern"
          style={{ padding: "16px 20px" }}
        >
          <span
            style={{
              fontSize: "0.75rem",
              fontWeight: "600",
              color: "#64748b",
            }}
          >
            Verified Accounts
          </span>
          <div
            style={{
              fontSize: "1.65rem",
              fontWeight: "700",
              color: "#16a34a",
              marginTop: "2px",
            }}
          >
            {verifiedCount}
          </div>
        </div>

        <div
          className="card-modern"
          style={{ padding: "16px 20px" }}
        >
          <span
            style={{
              fontSize: "0.75rem",
              fontWeight: "600",
              color: "#64748b",
            }}
          >
            Unverified Accounts
          </span>
          <div
            style={{
              fontSize: "1.65rem",
              fontWeight: "700",
              color: "#d97706",
              marginTop: "2px",
            }}
          >
            {unverifiedCount}
          </div>
        </div>

        <div
          className="card-modern"
          style={{ padding: "16px 20px" }}
        >
          <span
            style={{
              fontSize: "0.75rem",
              fontWeight: "600",
              color: "#64748b",
            }}
          >
            Aggregated Reliability
          </span>
          <div
            style={{
              fontSize: "1.65rem",
              fontWeight: "700",
              color: "#2563eb",
              marginTop: "2px",
            }}
          >
            {avgSuccessRate}
          </div>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div
        className="card-modern"
        style={{
          padding: "16px 20px",
          marginBottom: "16px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ flex: "1 1 280px", maxWidth: "420px" }}>
          <input
            type="text"
            className="form-control-modern"
            placeholder="Search by phone number or ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
          <span style={{ fontSize: "0.825rem", color: "#64748b" }}>Status:</span>
          <button
            type="button"
            onClick={() => setStatusFilter("all")}
            className={`btn-modern btn-modern-sm ${
              statusFilter === "all"
                ? "btn-modern-primary"
                : "btn-modern-secondary"
            }`}
          >
            All ({totalCount})
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter("verified")}
            className={`btn-modern btn-modern-sm ${
              statusFilter === "verified"
                ? "btn-modern-primary"
                : "btn-modern-secondary"
            }`}
          >
            Verified ({verifiedCount})
          </button>
          <button
            type="button"
            onClick={() => setStatusFilter("unverified")}
            className={`btn-modern btn-modern-sm ${
              statusFilter === "unverified"
                ? "btn-modern-primary"
                : "btn-modern-secondary"
            }`}
          >
            Unverified ({unverifiedCount})
          </button>
        </div>
      </div>

      {/* Customers Table */}
      <div className="card-modern" style={{ padding: "0", overflow: "hidden" }}>
        {loading ? (
          <div style={{ textAlign: "center", padding: "48px 20px" }}>
            <p style={{ color: "#64748b" }}>Loading customers...</p>
          </div>
        ) : error ? (
          <div style={{ padding: "24px", color: "#dc2626" }}>{error}</div>
        ) : filteredCustomers.length === 0 ? (
          <div style={{ textAlign: "center", padding: "48px 20px" }}>
            <p style={{ color: "#64748b", margin: 0 }}>
              No customers found matching search criteria.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.875rem",
                textAlign: "left",
              }}
            >
              <thead>
                <tr
                  style={{
                    backgroundColor: "#f8fafc",
                    borderBottom: "1px solid #e2e8f0",
                    color: "#64748b",
                    fontSize: "0.775rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.03em",
                  }}
                >
                  <th style={{ padding: "12px 16px" }}>ID</th>
                  <th style={{ padding: "12px 16px" }}>Mobile</th>
                  <th style={{ padding: "12px 16px" }}>Account Status</th>
                  <th style={{ padding: "12px 16px" }}>Orders</th>
                  <th style={{ padding: "12px 16px" }}>Success / Fail</th>
                  <th style={{ padding: "12px 16px" }}>Success Rate</th>
                  <th style={{ padding: "12px 16px" }}>Last Delivery</th>
                  <th style={{ padding: "12px 16px", textAlign: "right" }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {filteredCustomers.map((c) => {
                  const sRate =
                    c.success_rate !== undefined
                      ? `${c.success_rate}%`
                      : c.total_orders > 0
                      ? `${((c.successful_deliveries / c.total_orders) * 100).toFixed(1)}%`
                      : "100%";

                  const lastDeliveryText = c.last_successful_delivery
                    ? new Date(c.last_successful_delivery).toLocaleDateString(
                        "en-US",
                        {
                          month: "short",
                          day: "numeric",
                        }
                      )
                    : "—";

                  return (
                    <tr
                      key={c.id}
                      style={{
                        borderBottom: "1px solid #f1f5f9",
                        transition: "background 0.15s ease",
                      }}
                    >
                      <td style={{ padding: "12px 16px", fontWeight: "600" }}>
                        #{c.id}
                      </td>
                      <td
                        style={{
                          padding: "12px 16px",
                          fontWeight: "600",
                          color: "#0f172a",
                        }}
                      >
                        {c.phone}
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        {c.is_verified ? (
                          <span
                            className="badge-modern badge-status success"
                            style={{ fontSize: "0.725rem" }}
                          >
                            Verified
                          </span>
                        ) : (
                          <span
                            className="badge-modern badge-status"
                            style={{
                              fontSize: "0.725rem",
                              background: "#fffbeb",
                              color: "#d97706",
                              borderColor: "#fde68a",
                            }}
                          >
                            Unverified
                          </span>
                        )}
                      </td>
                      <td
                        style={{
                          padding: "12px 16px",
                          fontWeight: "600",
                          color: "#0f172a",
                        }}
                      >
                        {c.total_orders ?? 0}
                      </td>
                      <td style={{ padding: "12px 16px", color: "#475569" }}>
                        <span style={{ color: "#16a34a", fontWeight: "600" }}>
                          {c.successful_deliveries ?? 0}
                        </span>
                        {" / "}
                        <span
                          style={{
                            color:
                              (c.failed_deliveries ?? 0) > 0
                                ? "#dc2626"
                                : "#64748b",
                            fontWeight: "600",
                          }}
                        >
                          {c.failed_deliveries ?? 0}
                        </span>
                      </td>
                      <td style={{ padding: "12px 16px" }}>
                        <span
                          style={{
                            fontWeight: "700",
                            color:
                              parseFloat(sRate) >= 80
                                ? "#16a34a"
                                : parseFloat(sRate) >= 50
                                ? "#d97706"
                                : "#dc2626",
                          }}
                        >
                          {sRate}
                        </span>
                      </td>
                      <td style={{ padding: "12px 16px", color: "#64748b" }}>
                        {lastDeliveryText}
                      </td>
                      <td
                        style={{
                          padding: "12px 16px",
                          textAlign: "right",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            gap: "6px",
                            justifyContent: "flex-end",
                            alignItems: "center",
                          }}
                        >
                          <button
                            type="button"
                            onClick={() => handleToggleStatus(c)}
                            disabled={actionLoadingId === c.id}
                            className={`btn-modern btn-modern-sm ${
                              c.is_verified
                                ? "btn-modern-danger"
                                : "btn-modern-secondary"
                            }`}
                            style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                            title={
                              c.is_verified
                                ? "Deactivate Customer"
                                : "Activate Customer"
                            }
                          >
                            {actionLoadingId === c.id
                              ? "..."
                              : c.is_verified
                              ? "Deactivate"
                              : "Activate"}
                          </button>

                          <Link
                            to={`/admin/customers/${c.id}`}
                            className="btn-modern btn-modern-primary btn-modern-sm"
                            style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                          >
                            View Profile
                          </Link>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Info notice */}
      <div
        style={{
          marginTop: "16px",
          padding: "12px 16px",
          background: "#f8fafc",
          border: "1px solid #e2e8f0",
          borderRadius: "8px",
          fontSize: "0.8rem",
          color: "#64748b",
        }}
      >
        <strong>Note:</strong> Delivery statistics and reliability metrics are
        system-calculated based on operational events (dispatch, delivery completion, failure logs). Manual modification of statistics is prohibited.
      </div>
    </div>
  );
};

export default AdminCustomers;
