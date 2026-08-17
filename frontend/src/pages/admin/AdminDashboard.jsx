import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getAdminDashboard } from "../../services/api";
import RiskBadge from "../../components/RiskBadge";

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all"); // 'all', 'high_risk', 'unassigned', 'active', 'delivered'

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const res = await getAdminDashboard();
      setData(res);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load operations dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const operations = data?.operations || [];

  const filteredOperations = operations.filter((op) => {
    const status = String(op.status || "").toLowerCase();
    const risk = String(op.risk || "").toUpperCase();

    if (filter === "high_risk") return risk === "HIGH";
    if (filter === "unassigned") return status === "unassigned";
    if (filter === "active") return ["assigned", "picked_up", "out_for_delivery"].includes(status);
    if (filter === "delivered") return status === "delivered";
    return true;
  });

  return (
    <div className="animate-fade-in" style={{ maxWidth: "1200px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Page Title & Actions */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <h1 style={{ fontSize: "1.65rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
            Operations Dashboard
          </h1>
          <p style={{ fontSize: "0.875rem", color: "#64748b", margin: "3px 0 0" }}>
            Real-time delivery status, ML failure risk assessment, and dispatch operations
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            type="button"
            onClick={fetchDashboard}
            className="btn-modern btn-modern-secondary btn-modern-sm"
          >
            ↻ Refresh
          </button>
          <Link to="/admin/prediction" className="btn-modern btn-modern-primary btn-modern-sm">
            + Run ML Prediction
          </Link>
        </div>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "#fef2f2", color: "#dc2626", borderRadius: "8px", border: "1px solid #fecaca", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {/* Top 5 Summary Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: "14px",
          marginBottom: "24px",
        }}
      >
        <div className="card-modern" style={{ borderLeft: "4px solid #2563eb", padding: "16px 18px" }}>
          <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            New Orders
          </span>
          <div style={{ fontSize: "1.85rem", fontWeight: "800", color: "#0f172a", marginTop: "2px" }}>
            {data?.new_orders ?? data?.today_orders ?? 0}
          </div>
          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Registered requests</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #dc2626", padding: "16px 18px" }}>
          <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#dc2626", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            High Risk
          </span>
          <div style={{ fontSize: "1.85rem", fontWeight: "800", color: "#dc2626", marginTop: "2px" }}>
            {data?.high_risk ?? 0}
          </div>
          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Requires admin review</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #d97706", padding: "16px 18px" }}>
          <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#d97706", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Unassigned Deliveries
          </span>
          <div style={{ fontSize: "1.85rem", fontWeight: "800", color: "#d97706", marginTop: "2px" }}>
            {data?.unassigned ?? 0}
          </div>
          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Pending rider dispatch</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #0284c7", padding: "16px 18px" }}>
          <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#0284c7", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Active Deliveries
          </span>
          <div style={{ fontSize: "1.85rem", fontWeight: "800", color: "#0284c7", marginTop: "2px" }}>
            {data?.active_deliveries ?? 0}
          </div>
          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>In transit / assigned</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #16a34a", padding: "16px 18px" }}>
          <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#16a34a", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Completed Today
          </span>
          <div style={{ fontSize: "1.85rem", fontWeight: "800", color: "#16a34a", marginTop: "2px" }}>
            {data?.completed_today ?? 0}
          </div>
          <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Successfully delivered</span>
        </div>
      </div>

      {/* Main Section: Delivery Operations */}
      <div className="card-modern" style={{ padding: "20px" }}>
        {/* Table Title & Filter Tabs */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
            marginBottom: "16px",
            borderBottom: "1px solid #f1f5f9",
            paddingBottom: "14px",
          }}
        >
          <div>
            <h2 style={{ fontSize: "1.2rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
              Delivery Operations
            </h2>
            <span style={{ fontSize: "0.825rem", color: "#64748b" }}>
              Showing {filteredOperations.length} of {operations.length} deliveries
            </span>
          </div>

          {/* Filter tabs */}
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {[
              { id: "all", label: "All" },
              { id: "high_risk", label: `High Risk (${data?.high_risk ?? 0})` },
              { id: "unassigned", label: `Unassigned (${data?.unassigned ?? 0})` },
              { id: "active", label: `In Transit (${data?.active_deliveries ?? 0})` },
              { id: "delivered", label: `Delivered (${data?.completed_today ?? 0})` },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setFilter(tab.id)}
                style={{
                  padding: "5px 12px",
                  fontSize: "0.8rem",
                  fontWeight: "600",
                  borderRadius: "6px",
                  border: filter === tab.id ? "1px solid #2563eb" : "1px solid #e2e8f0",
                  backgroundColor: filter === tab.id ? "#eff6ff" : "#ffffff",
                  color: filter === tab.id ? "#2563eb" : "#64748b",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        {loading ? (
          <p style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
            Loading operations queue...
          </p>
        ) : filteredOperations.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
            <p>No delivery operations matching the selected filter.</p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.875rem" }}>
              <thead>
                <tr
                  style={{
                    borderBottom: "2px solid #e2e8f0",
                    color: "#64748b",
                    fontSize: "0.75rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  <th style={{ padding: "10px 12px" }}>Order</th>
                  <th style={{ padding: "10px 12px" }}>Customer</th>
                  <th style={{ padding: "10px 12px" }}>Delivery Area</th>
                  <th style={{ padding: "10px 12px" }}>Risk</th>
                  <th style={{ padding: "10px 12px" }}>Failure Probability</th>
                  <th style={{ padding: "10px 12px" }}>Rider</th>
                  <th style={{ padding: "10px 12px" }}>Delivery Status</th>
                  <th style={{ padding: "10px 12px", textAlign: "right" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredOperations.map((op) => {
                  const probFormatted =
                    op.probability != null ? `${(Number(op.probability) * 100).toFixed(1)}%` : "—";
                  const isUnassigned = op.status === "unassigned";

                  return (
                    <tr
                      key={op.delivery_id}
                      style={{
                        borderBottom: "1px solid #f1f5f9",
                        transition: "background 0.15s",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#f8fafc")}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                    >
                      {/* Order Column */}
                      <td style={{ padding: "12px" }}>
                        <div style={{ fontWeight: "700", color: "#0f172a" }}>
                          Order #{op.order_id}
                        </div>
                        <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                          {op.item_name} • Rs. {Number(op.total_price || 0).toLocaleString()}
                        </span>
                      </td>

                      {/* Customer Column */}
                      <td style={{ padding: "12px", color: "#334155", fontWeight: "500" }}>
                        {op.customer_phone}
                      </td>

                      {/* Delivery Area Column */}
                      <td style={{ padding: "12px" }}>
                        <div style={{ fontWeight: "600", color: "#0f172a" }}>{op.area}</div>
                        <span style={{ fontSize: "0.75rem", color: "#64748b", display: "block", maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {op.address}
                        </span>
                      </td>

                      {/* Risk Badge Column */}
                      <td style={{ padding: "12px" }}>
                        <RiskBadge risk={op.risk} size="small" />
                      </td>

                      {/* Failure Probability Column */}
                      <td style={{ padding: "12px", fontWeight: "700", color: "#0f172a" }}>
                        {probFormatted}
                      </td>

                      {/* Rider Column */}
                      <td style={{ padding: "12px" }}>
                        {op.rider ? (
                          <div style={{ fontWeight: "600", color: "#0f172a" }}>
                            🚴 {op.rider}
                          </div>
                        ) : (
                          <span style={{ color: "#d97706", fontWeight: "600", fontSize: "0.8rem" }}>
                            Unassigned
                          </span>
                        )}
                      </td>

                      {/* Delivery Status Column */}
                      <td style={{ padding: "12px" }}>
                        <span className={`badge-modern badge-status ${op.status === "delivered" ? "success" : op.status === "unassigned" ? "neutral" : "active"}`}>
                          {String(op.status).replace(/_/g, " ")}
                        </span>
                      </td>

                      {/* Action Column */}
                      <td style={{ padding: "12px", textAlign: "right" }}>
                        <div style={{ display: "flex", justifyContent: "flex-end", gap: "6px" }}>
                          {isUnassigned && (
                            <button
                              type="button"
                              onClick={() => navigate(`/admin/dispatch?deliveryId=${op.delivery_id}`)}
                              className="btn-modern btn-modern-primary btn-modern-sm"
                              style={{ padding: "4px 10px", fontSize: "0.775rem" }}
                            >
                              Dispatch
                            </button>
                          )}
                          <Link
                            to={`/admin/deliveries/${op.delivery_id}`}
                            className="btn-modern btn-modern-secondary btn-modern-sm"
                            style={{ padding: "4px 10px", fontSize: "0.775rem" }}
                          >
                            Details
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
    </div>
  );
};

export default AdminDashboard;
