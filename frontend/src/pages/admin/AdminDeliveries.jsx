import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getAdminDeliveries } from "../../services/api";
import RiskBadge from "../../components/RiskBadge";

const AdminDeliveries = () => {
  const navigate = useNavigate();
  const [deliveries, setDeliveries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");

  const fetchDeliveries = async () => {
    try {
      setLoading(true);
      const res = await getAdminDeliveries();
      setDeliveries(res);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load deliveries");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeliveries();
  }, []);

  const filtered = deliveries.filter((d) => {
    const q = search.toLowerCase();
    const matchesSearch =
      !q ||
      String(d.order_id).includes(q) ||
      String(d.customer_phone || "").toLowerCase().includes(q) ||
      String(d.area || "").toLowerCase().includes(q) ||
      String(d.item_name || "").toLowerCase().includes(q) ||
      String(d.rider_name || "").toLowerCase().includes(q);

    const status = String(d.status || "").toLowerCase();
    const matchesStatus =
      statusFilter === "all" ||
      (statusFilter === "unassigned" && status === "unassigned") ||
      (statusFilter === "active" && ["assigned", "picked_up", "out_for_delivery"].includes(status)) ||
      (statusFilter === "delivered" && status === "delivered") ||
      (statusFilter === "failed" && ["failed", "unreachable", "returned", "cancelled"].includes(status));

    const risk = String(d.risk || "").toUpperCase();
    const matchesRisk = riskFilter === "all" || risk === riskFilter;

    return matchesSearch && matchesStatus && matchesRisk;
  });

  return (
    <div className="animate-fade-in" style={{ maxWidth: "1200px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <h1 style={{ fontSize: "1.65rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
            Deliveries
          </h1>
          <p style={{ fontSize: "0.875rem", color: "#64748b", margin: "3px 0 0" }}>
            All operational delivery records, risk evaluations, and active tracking
          </p>
        </div>

        <button
          type="button"
          onClick={fetchDeliveries}
          className="btn-modern btn-modern-secondary btn-modern-sm"
        >
          ↻ Refresh Deliveries
        </button>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "#fef2f2", color: "#dc2626", borderRadius: "8px", border: "1px solid #fecaca", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {/* Filters Bar */}
      <div
        className="card-modern"
        style={{
          padding: "16px 20px",
          marginBottom: "20px",
          display: "flex",
          gap: "12px",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", gap: "12px", flexWrap: "wrap", alignItems: "center", flex: "1" }}>
          <input
            type="text"
            className="form-control-modern"
            placeholder="Search by Order #, Phone, Area, Rider..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ maxWidth: "320px", fontSize: "0.875rem" }}
          />

          <select
            className="form-control-modern"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ width: "auto", fontSize: "0.875rem" }}
          >
            <option value="all">All Statuses</option>
            <option value="unassigned">Unassigned</option>
            <option value="active">Active (In Transit)</option>
            <option value="delivered">Delivered</option>
            <option value="failed">Failed / Unreachable</option>
          </select>

          <select
            className="form-control-modern"
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            style={{ width: "auto", fontSize: "0.875rem" }}
          >
            <option value="all">All Risk Levels</option>
            <option value="LOW">LOW Risk</option>
            <option value="MEDIUM">MEDIUM Risk</option>
            <option value="HIGH">HIGH Risk</option>
          </select>
        </div>

        <span style={{ fontSize: "0.825rem", color: "#64748b" }}>
          Showing {filtered.length} of {deliveries.length}
        </span>
      </div>

      {/* Deliveries Table */}
      <div className="card-modern" style={{ padding: "20px" }}>
        {loading ? (
          <p style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
            Loading deliveries list...
          </p>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
            <p>No deliveries found matching the filters.</p>
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
                  <th style={{ padding: "10px 12px" }}>Area & Address</th>
                  <th style={{ padding: "10px 12px" }}>Risk</th>
                  <th style={{ padding: "10px 12px" }}>Failure Probability</th>
                  <th style={{ padding: "10px 12px" }}>Rider</th>
                  <th style={{ padding: "10px 12px" }}>Status</th>
                  <th style={{ padding: "10px 12px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((d) => {
                  const probFormatted =
                    d.probability != null ? `${(Number(d.probability) * 100).toFixed(1)}%` : "—";
                  const isUnassigned = d.status === "unassigned";

                  return (
                    <tr
                      key={d.delivery_id}
                      style={{ borderBottom: "1px solid #f1f5f9", transition: "background 0.15s" }}
                      onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#f8fafc")}
                      onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "transparent")}
                    >
                      <td style={{ padding: "12px" }}>
                        <div style={{ fontWeight: "700", color: "#0f172a" }}>
                          Order #{d.order_id}
                        </div>
                        <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                          {d.item_name} (Qty: {d.quantity || 1})
                        </span>
                      </td>

                      <td style={{ padding: "12px", color: "#334155", fontWeight: "500" }}>
                        {d.customer_phone}
                      </td>

                      <td style={{ padding: "12px" }}>
                        <div style={{ fontWeight: "600", color: "#0f172a" }}>{d.area}</div>
                        <span style={{ fontSize: "0.75rem", color: "#64748b", display: "block", maxWidth: "220px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {d.address}
                        </span>
                      </td>

                      <td style={{ padding: "12px" }}>
                        <RiskBadge risk={d.risk} size="small" />
                      </td>

                      <td style={{ padding: "12px", fontWeight: "700", color: "#0f172a" }}>
                        {probFormatted}
                      </td>

                      <td style={{ padding: "12px" }}>
                        {d.rider_name ? (
                          <span style={{ fontWeight: "600", color: "#0f172a" }}>🚴 {d.rider_name}</span>
                        ) : (
                          <span style={{ color: "#d97706", fontWeight: "600", fontSize: "0.8rem" }}>Unassigned</span>
                        )}
                      </td>

                      <td style={{ padding: "12px" }}>
                        <span className={`badge-modern badge-status ${d.status === "delivered" ? "success" : d.status === "unassigned" ? "neutral" : "active"}`}>
                          {String(d.status).replace(/_/g, " ")}
                        </span>
                      </td>

                      <td style={{ padding: "12px", textAlign: "right" }}>
                        <div style={{ display: "flex", justifyContent: "flex-end", gap: "6px" }}>
                          {isUnassigned && (
                            <button
                              type="button"
                              onClick={() => navigate(`/admin/dispatch?deliveryId=${d.delivery_id}`)}
                              className="btn-modern btn-modern-primary btn-modern-sm"
                              style={{ padding: "4px 10px", fontSize: "0.775rem" }}
                            >
                              Dispatch
                            </button>
                          )}
                          <Link
                            to={`/admin/deliveries/${d.delivery_id}`}
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

export default AdminDeliveries;
