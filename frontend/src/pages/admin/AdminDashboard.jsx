import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getAdminDashboard } from "../../services/api";
import RiskBadge from "../../components/RiskBadge";

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all"); // 'all', 'unassigned', 'high_risk', 'active', 'delivered'

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

    if (filter === "unassigned") return status === "unassigned";
    if (filter === "high_risk") return risk === "HIGH";
    if (filter === "active") return ["assigned", "picked_up", "out_for_delivery"].includes(status);
    if (filter === "delivered") return status === "delivered";
    return true;
  });

  return (
    <div className="animate-fade-in" style={{ maxWidth: "1180px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Title */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Realtime Dispatch & Risk Engine
          </span>
          <h1 style={{ fontSize: "1.85rem", fontWeight: "800", color: "#0f172a", marginTop: "2px" }}>
            DELIVERY OPERATIONS
          </h1>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            type="button"
            onClick={fetchDashboard}
            className="btn-modern btn-modern-secondary btn-modern-sm"
          >
            ↻ Refresh Operations
          </button>
          <Link to="/admin/prediction" className="btn-modern btn-modern-primary btn-modern-sm">
            ⚡ Run ML Prediction
          </Link>
        </div>
      </div>

      {error && (
        <div style={{ padding: "14px", background: "#fef2f2", color: "#dc2626", borderRadius: "8px", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {/* Top 4 Real Operations KPI Metric Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
          gap: "16px",
          marginBottom: "28px",
        }}
      >
        <div className="card-modern" style={{ borderLeft: "4px solid #2563eb" }}>
          <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Today's Orders
          </span>
          <div style={{ fontSize: "2.25rem", fontWeight: "800", color: "#0f172a", marginTop: "4px" }}>
            {data?.today_orders ?? 0}
          </div>
          <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Registered delivery requests</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #16a34a" }}>
          <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Active Deliveries
          </span>
          <div style={{ fontSize: "2.25rem", fontWeight: "800", color: "#16a34a", marginTop: "4px" }}>
            {data?.active_deliveries ?? 0}
          </div>
          <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Currently in transit or assigned</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #d97706" }}>
          <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Unassigned
          </span>
          <div style={{ fontSize: "2.25rem", fontWeight: "800", color: "#d97706", marginTop: "4px" }}>
            {data?.unassigned ?? 0}
          </div>
          <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Awaiting rider dispatch</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #dc2626" }}>
          <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            High Risk
          </span>
          <div style={{ fontSize: "2.25rem", fontWeight: "800", color: "#dc2626", marginTop: "4px" }}>
            {data?.high_risk ?? 0}
          </div>
          <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Flagged by ML failure model</span>
        </div>
      </div>

      {/* Active Operations Table Section */}
      <div className="card-modern" style={{ padding: "20px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
            marginBottom: "18px",
            borderBottom: "1px solid #f1f5f9",
            paddingBottom: "14px",
          }}
        >
          <div>
            <h2 style={{ fontSize: "1.15rem", fontWeight: "800", color: "#0f172a", textTransform: "uppercase", letterSpacing: "0.03em" }}>
              ACTIVE DELIVERY OPERATIONS
            </h2>
            <p style={{ fontSize: "0.85rem", color: "#64748b", margin: 0 }}>
              Live lifecycle, risk status, and algorithmic rider assignment
            </p>
          </div>

          {/* Filter Pills */}
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            {[
              { id: "all", label: "All" },
              { id: "unassigned", label: `Unassigned (${data?.unassigned ?? 0})` },
              { id: "high_risk", label: `High Risk (${data?.high_risk ?? 0})` },
              { id: "active", label: "In Transit" },
              { id: "delivered", label: "Delivered" },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => setFilter(tab.id)}
                style={{
                  fontSize: "0.8rem",
                  fontWeight: "600",
                  padding: "5px 12px",
                  borderRadius: "6px",
                  border: filter === tab.id ? "1px solid #2563eb" : "1px solid #e2e8f0",
                  backgroundColor: filter === tab.id ? "#eff6ff" : "#ffffff",
                  color: filter === tab.id ? "#2563eb" : "#64748b",
                  cursor: "pointer",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        {loading ? (
          <p style={{ textAlign: "center", padding: "32px", color: "#64748b" }}>Loading operational deliveries...</p>
        ) : filteredOperations.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
            No operations match the selected filter.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.9rem" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e2e8f0", color: "#64748b", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  <th style={{ padding: "10px 12px" }}>Order</th>
                  <th style={{ padding: "10px 12px" }}>Customer</th>
                  <th style={{ padding: "10px 12px" }}>Area</th>
                  <th style={{ padding: "10px 12px" }}>Risk</th>
                  <th style={{ padding: "10px 12px" }}>Rider</th>
                  <th style={{ padding: "10px 12px" }}>Status</th>
                  <th style={{ padding: "10px 12px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredOperations.map((op) => {
                  const isUnassigned = String(op.status || "").toLowerCase() === "unassigned";

                  return (
                    <tr
                      key={op.delivery_id || op.order_id}
                      style={{
                        borderBottom: "1px solid #f1f5f9",
                        transition: "background 0.15s",
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "#f8fafc")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                    >
                      <td style={{ padding: "12px", fontWeight: "700", color: "#0f172a" }}>
                        #{op.order_id}
                      </td>
                      <td style={{ padding: "12px", color: "#334155" }}>
                        {op.customer_phone || "—"}
                      </td>
                      <td style={{ padding: "12px", color: "#334155" }}>
                        <span style={{ fontWeight: "600" }}>{op.area}</span>
                      </td>
                      <td style={{ padding: "12px" }}>
                        <RiskBadge risk={op.risk} size="small" />
                      </td>
                      <td style={{ padding: "12px", color: op.rider ? "#0f172a" : "#94a3b8", fontWeight: op.rider ? "600" : "400" }}>
                        {op.rider ? `🚴 ${op.rider}` : "—"}
                      </td>
                      <td style={{ padding: "12px" }}>
                        <span
                          className={`badge-modern ${
                            op.status === "delivered"
                              ? "badge-status success"
                              : isUnassigned
                              ? "badge-modern badge-medium"
                              : "badge-status active"
                          }`}
                          style={{ fontSize: "0.725rem" }}
                        >
                          {String(op.status || "unassigned").replace(/_/g, " ")}
                        </span>
                      </td>
                      <td style={{ padding: "12px", textAlign: "right" }}>
                        <div style={{ display: "inline-flex", gap: "8px" }}>
                          {isUnassigned && (
                            <button
                              type="button"
                              onClick={() => navigate(`/admin/dispatch?deliveryId=${op.delivery_id}`)}
                              className="btn-modern btn-modern-primary btn-modern-sm"
                              style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                            >
                              Dispatch
                            </button>
                          )}
                          <button
                            type="button"
                            onClick={() => navigate(`/admin/deliveries/${op.delivery_id}`)}
                            className="btn-modern btn-modern-secondary btn-modern-sm"
                            style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                          >
                            Lifecycle →
                          </button>
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
