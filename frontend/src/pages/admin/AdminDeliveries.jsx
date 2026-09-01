import { useEffect, useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getAdminDeliveries, getErrorMessage } from "../../services/api";
import RiskBadge from "../../components/RiskBadge";

const AdminDeliveries = () => {
  const navigate = useNavigate();
  const [deliveries, setDeliveries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [riderFilter, setRiderFilter] = useState("all");
  
  // Pagination State
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);

  const fetchDeliveries = async () => {
    try {
      setLoading(true);
      setError("");
      const res = await getAdminDeliveries();
      setDeliveries(Array.isArray(res) ? res : res.items || []);
    } catch (err) {
      setError(getErrorMessage(err, "Deliveries list could not be loaded. Please verify connection."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeliveries();
  }, []);

  // Distinct riders for filter dropdown
  const distinctRiders = useMemo(() => {
    const map = new Map();
    deliveries.forEach((d) => {
      if (d.rider_id && d.rider_name) {
        map.set(d.rider_id, d.rider_name);
      }
    });
    return Array.from(map.entries()).map(([id, name]) => ({ id, name }));
  }, [deliveries]);

  const filtered = useMemo(() => {
    return deliveries.filter((d) => {
      const q = search.trim().toLowerCase();
      const matchesSearch =
        !q ||
        String(d.order_id).toLowerCase().includes(q) ||
        String(d.customer_phone || "").toLowerCase().includes(q) ||
        String(d.area || "").toLowerCase().includes(q) ||
        String(d.address || "").toLowerCase().includes(q) ||
        String(d.item_name || "").toLowerCase().includes(q) ||
        String(d.rider_name || "").toLowerCase().includes(q);

      const status = String(d.status || "").toLowerCase();
      let matchesStatus = true;
      if (statusFilter === "all") {
        matchesStatus = true;
      } else if (statusFilter === "unassigned") {
        matchesStatus = status === "unassigned";
      } else if (statusFilter === "active") {
        matchesStatus = ["assigned", "picked_up", "out_for_delivery"].includes(status);
      } else if (statusFilter === "assigned") {
        matchesStatus = status === "assigned";
      } else if (statusFilter === "picked_up") {
        matchesStatus = status === "picked_up";
      } else if (statusFilter === "out_for_delivery") {
        matchesStatus = status === "out_for_delivery";
      } else if (statusFilter === "delivered") {
        matchesStatus = status === "delivered";
      } else if (statusFilter === "failed") {
        matchesStatus = ["failed", "unreachable", "returned", "cancelled"].includes(status);
      }

      const risk = String(d.risk || "").toUpperCase();
      const matchesRisk = riskFilter === "all" || risk === riskFilter;

      const matchesRider =
        riderFilter === "all" ||
        (riderFilter === "unassigned" && !d.rider_id) ||
        String(d.rider_id) === String(riderFilter);

      return matchesSearch && matchesStatus && matchesRisk && matchesRider;
    });
  }, [deliveries, search, statusFilter, riskFilter, riderFilter]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [search, statusFilter, riskFilter, riderFilter, pageSize]);

  // Pagination calculation
  const totalRecords = filtered.length;
  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));
  const currentPage = Math.min(page, totalPages);
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedDeliveries = filtered.slice(startIndex, startIndex + pageSize);

  const handlePrevPage = () => {
    setPage((prev) => Math.max(prev - 1, 1));
  };

  const handleNextPage = () => {
    setPage((prev) => Math.min(prev + 1, totalPages));
  };

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
        <div
          className="card-modern"
          style={{
            padding: "14px 18px",
            background: "#fef2f2",
            borderColor: "#fecaca",
            marginBottom: "20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontWeight: "700", color: "#dc2626", fontSize: "0.9rem" }}>
              Unable to load deliveries
            </div>
            <p style={{ fontSize: "0.825rem", color: "#991b1b", margin: "2px 0 0" }}>{error}</p>
          </div>
          <button
            type="button"
            onClick={fetchDeliveries}
            className="btn-modern btn-modern-primary btn-modern-sm"
          >
            Retry
          </button>
        </div>
      )}

      {/* Filters Bar */}
      <div
        className="card-modern"
        style={{
          padding: "14px 18px",
          marginBottom: "20px",
          display: "flex",
          gap: "10px",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", alignItems: "center", flex: "1" }}>
          <input
            type="text"
            className="form-control-modern"
            placeholder="Search Order #, Phone, Area, Rider..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ maxWidth: "260px", fontSize: "0.825rem", padding: "6px 12px" }}
          />

          <select
            className="form-control-modern"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            style={{ width: "auto", fontSize: "0.825rem", padding: "6px 12px" }}
          >
            <option value="all">All Statuses</option>
            <option value="unassigned">Unassigned (Awaiting Rider)</option>
            <option value="active">Active (In Transit)</option>
            <option value="assigned">Assigned</option>
            <option value="picked_up">Picked Up</option>
            <option value="out_for_delivery">Out for Delivery</option>
            <option value="delivered">Delivered</option>
            <option value="failed">Failed / Unreachable</option>
          </select>

          <select
            className="form-control-modern"
            value={riskFilter}
            onChange={(e) => setRiskFilter(e.target.value)}
            style={{ width: "auto", fontSize: "0.825rem", padding: "6px 12px" }}
          >
            <option value="all">All Risk Levels</option>
            <option value="LOW">LOW Risk</option>
            <option value="MEDIUM">MEDIUM Risk</option>
            <option value="HIGH">HIGH Risk</option>
          </select>

          {distinctRiders.length > 0 && (
            <select
              className="form-control-modern"
              value={riderFilter}
              onChange={(e) => setRiderFilter(e.target.value)}
              style={{ width: "auto", fontSize: "0.825rem", padding: "6px 12px" }}
            >
              <option value="all">All Riders</option>
              <option value="unassigned">No Rider Assigned</option>
              {distinctRiders.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          )}

          <select
            className="form-control-modern"
            value={pageSize}
            onChange={(e) => setPageSize(Number(e.target.value))}
            style={{ width: "auto", fontSize: "0.825rem", padding: "6px 10px" }}
          >
            <option value={10}>10 / page</option>
            <option value={20}>20 / page</option>
            <option value={50}>50 / page</option>
          </select>
        </div>

        <span style={{ fontSize: "0.825rem", color: "#64748b" }}>
          Showing {filtered.length === 0 ? 0 : startIndex + 1}–{Math.min(startIndex + pageSize, totalRecords)} of {totalRecords}
        </span>
      </div>

      {/* Deliveries Table */}
      <div className="card-modern" style={{ padding: "20px" }}>
        {loading ? (
          <p style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
            Loading deliveries list...
          </p>
        ) : paginatedDeliveries.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
            <p>No deliveries found matching the filters.</p>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.85rem" }}>
              <thead>
                <tr
                  style={{
                    borderBottom: "2px solid #e2e8f0",
                    color: "#64748b",
                    fontSize: "0.725rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.05em",
                  }}
                >
                  <th style={{ padding: "8px 10px" }}>Order</th>
                  <th style={{ padding: "8px 10px" }}>Customer</th>
                  <th style={{ padding: "8px 10px" }}>Area & Address</th>
                  <th style={{ padding: "8px 10px" }}>ML Risk</th>
                  <th style={{ padding: "8px 10px" }}>Failure Prob</th>
                  <th style={{ padding: "8px 10px" }}>Rider</th>
                  <th style={{ padding: "8px 10px" }}>Status</th>
                  <th style={{ padding: "8px 10px", textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {paginatedDeliveries.map((d) => {
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
                      <td style={{ padding: "10px" }}>
                        <div style={{ fontWeight: "700", color: "#0f172a" }}>
                          Order #{d.order_id}
                        </div>
                        <span style={{ fontSize: "0.725rem", color: "#64748b" }}>
                          {d.item_name} {d.quantity > 1 ? `(Qty: ${d.quantity})` : ""} • Rs. {Number(d.total_price || 0).toLocaleString()}
                        </span>
                      </td>

                      <td style={{ padding: "10px", color: "#334155", fontWeight: "500" }}>
                        {d.customer_phone}
                        <div style={{ fontSize: "0.725rem", color: "#64748b" }}>
                          {d.payment_method?.toUpperCase() || (d.is_cod ? "COD" : "PREPAID")}
                        </div>
                      </td>

                      <td style={{ padding: "10px" }}>
                        <div style={{ fontWeight: "600", color: "#0f172a" }}>{d.area}</div>
                        <span style={{ fontSize: "0.725rem", color: "#64748b", display: "block", maxWidth: "200px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {d.address}
                        </span>
                      </td>

                      <td style={{ padding: "10px" }}>
                        <RiskBadge risk={d.risk} size="small" />
                      </td>

                      <td style={{ padding: "10px", fontWeight: "700", color: "#0f172a" }}>
                        {probFormatted}
                      </td>

                      <td style={{ padding: "10px" }}>
                        {d.rider_name ? (
                          <div>
                            <div style={{ fontWeight: "600", color: "#0f172a" }}>
                              {d.rider_name}
                            </div>
                            {d.rider_load !== undefined && d.rider_load !== null && (
                              <span style={{ fontSize: "0.725rem", color: "#64748b" }}>
                                Load: {d.rider_load} / {d.rider_capacity || 20}
                              </span>
                            )}
                          </div>
                        ) : (
                          <div>
                            <span style={{ color: "#d97706", fontWeight: "600", fontSize: "0.775rem", display: "flex", alignItems: "center", gap: "4px" }}>
                              Awaiting Rider
                            </span>
                            <span style={{ fontSize: "0.7rem", color: "#92400e" }}>
                              Waiting for available rider
                            </span>
                          </div>
                        )}
                      </td>

                      <td style={{ padding: "10px" }}>
                        <span className={`badge-modern badge-status ${d.status === "delivered" ? "success" : d.status === "unassigned" ? "neutral" : d.status === "failed" || d.status === "unreachable" ? "danger" : "active"}`}>
                          {String(d.status).replace(/_/g, " ")}
                        </span>
                      </td>

                      <td style={{ padding: "10px", textAlign: "right" }}>
                        <div style={{ display: "flex", justifyContent: "flex-end", gap: "6px" }}>
                          {isUnassigned && (
                            <button
                              type="button"
                              onClick={() => navigate(`/admin/dispatch?deliveryId=${d.delivery_id}`)}
                              className="btn-modern btn-modern-primary btn-modern-sm"
                              style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                            >
                              Dispatch
                            </button>
                          )}
                          <Link
                            to={`/admin/deliveries/${d.delivery_id}`}
                            className="btn-modern btn-modern-secondary btn-modern-sm"
                            style={{ padding: "4px 8px", fontSize: "0.75rem" }}
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

        {/* Pagination Footer */}
        {totalRecords > 0 && (
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "10px",
              marginTop: "16px",
              paddingTop: "14px",
              borderTop: "1px solid #f1f5f9",
            }}
          >
            <div style={{ fontSize: "0.825rem", color: "#64748b" }}>
              Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong> ({totalRecords} total deliveries)
            </div>

            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              <button
                type="button"
                onClick={handlePrevPage}
                disabled={currentPage <= 1}
                className="btn-modern btn-modern-secondary btn-modern-sm"
                style={{
                  opacity: currentPage <= 1 ? 0.5 : 1,
                  cursor: currentPage <= 1 ? "not-allowed" : "pointer",
                  padding: "4px 10px",
                  fontSize: "0.8rem",
                }}
              >
                ← Previous
              </button>

              <span style={{ fontSize: "0.825rem", color: "#0f172a", fontWeight: "600", padding: "0 6px" }}>
                {currentPage}
              </span>

              <button
                type="button"
                onClick={handleNextPage}
                disabled={currentPage >= totalPages}
                className="btn-modern btn-modern-secondary btn-modern-sm"
                style={{
                  opacity: currentPage >= totalPages ? 0.5 : 1,
                  cursor: currentPage >= totalPages ? "not-allowed" : "pointer",
                  padding: "4px 10px",
                  fontSize: "0.8rem",
                }}
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDeliveries;
