import { useEffect, useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getAdminDashboard, getErrorMessage } from "../../services/api";
import RiskBadge from "../../components/RiskBadge";

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [riderFilter, setRiderFilter] = useState("all");
  const [search, setSearch] = useState("");
  
  // Pagination State
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      setError("");
      const res = await getAdminDashboard();
      setData(res);
    } catch (err) {
      setError(getErrorMessage(err, "Delivery summary could not be loaded. Please verify backend service and connection."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const operations = data?.operations || [];
  const riders = data?.riders || [];

  // Filtered operations
  const filteredOperations = useMemo(() => {
    return operations.filter((op) => {
      const q = search.trim().toLowerCase();
      const matchesSearch =
        !q ||
        String(op.order_id).toLowerCase().includes(q) ||
        String(op.customer_phone || "").toLowerCase().includes(q) ||
        String(op.area || "").toLowerCase().includes(q) ||
        String(op.address || "").toLowerCase().includes(q) ||
        String(op.rider || "").toLowerCase().includes(q) ||
        String(op.item_name || "").toLowerCase().includes(q);

      const status = String(op.status || "").toLowerCase();
      let matchesStatus = true;
      if (statusFilter === "high_risk") {
        matchesStatus = String(op.risk || "").toUpperCase() === "HIGH";
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

      const risk = String(op.risk || "").toUpperCase();
      const matchesRisk = riskFilter === "all" || risk === riskFilter;

      const matchesRider =
        riderFilter === "all" ||
        (riderFilter === "unassigned" && !op.rider_id) ||
        String(op.rider_id) === String(riderFilter);

      return matchesSearch && matchesStatus && matchesRisk && matchesRider;
    });
  }, [operations, search, statusFilter, riskFilter, riderFilter]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [search, statusFilter, riskFilter, riderFilter, pageSize]);

  // Paginated slice
  const totalRecords = filteredOperations.length;
  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));
  const currentPage = Math.min(page, totalPages);
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedOperations = filteredOperations.slice(startIndex, startIndex + pageSize);

  const handlePrevPage = () => {
    setPage((prev) => Math.max(prev - 1, 1));
  };

  const handleNextPage = () => {
    setPage((prev) => Math.min(prev + 1, totalPages));
  };

  if (loading && !data) {
    return (
      <div className="card-modern" style={{ textAlign: "center", padding: "48px 20px" }}>
        <p style={{ color: "#64748b", fontSize: "0.95rem" }}>Loading operations dashboard data...</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="animate-fade-in" style={{ maxWidth: "1200px", margin: "0 auto", paddingBottom: "48px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
          <div>
            <h1 style={{ fontSize: "1.65rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
              Operations Dashboard
            </h1>
            <p style={{ fontSize: "0.875rem", color: "#64748b", margin: "3px 0 0" }}>
              Real-time delivery status, ML failure risk assessment, automated rider dispatch, and exception handling
            </p>
          </div>
        </div>

        <div
          className="card-modern"
          style={{
            padding: "20px 24px",
            background: "#fef2f2",
            borderColor: "#fecaca",
            marginBottom: "20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "14px",
          }}
        >
          <div>
            <div style={{ fontWeight: "700", color: "#dc2626", fontSize: "1rem" }}>
              Unable to load dashboard data
            </div>
            <p style={{ fontSize: "0.875rem", color: "#991b1b", margin: "4px 0 0" }}>{error}</p>
          </div>
          <button
            type="button"
            onClick={fetchDashboard}
            className="btn-modern btn-modern-primary"
            style={{ padding: "8px 20px" }}
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in" style={{ maxWidth: "1200px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <h1 style={{ fontSize: "1.65rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
            Operations Dashboard
          </h1>
          <p style={{ fontSize: "0.875rem", color: "#64748b", margin: "3px 0 0" }}>
            Real-time delivery status, ML failure risk assessment, automated rider dispatch, and exception handling
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

      {/* Non-fatal refresh error banner */}
      {error && (
        <div
          className="card-modern"
          style={{
            padding: "16px 20px",
            background: "#fef2f2",
            borderColor: "#fecaca",
            marginBottom: "20px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <div style={{ fontWeight: "700", color: "#dc2626", fontSize: "0.95rem" }}>
              Unable to load dashboard data
            </div>
            <p style={{ fontSize: "0.85rem", color: "#991b1b", margin: "4px 0 0" }}>{error}</p>
          </div>
          <button
            type="button"
            onClick={fetchDashboard}
            className="btn-modern btn-modern-primary btn-modern-sm"
          >
            Retry
          </button>
        </div>
      )}

      {/* KPI Summary Cards Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
          gap: "12px",
          marginBottom: "24px",
        }}
      >
        <div className="card-modern" style={{ borderLeft: "4px solid #2563eb", padding: "14px 16px" }}>
          <span style={{ fontSize: "0.725rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Total Orders
          </span>
          <div style={{ fontSize: "1.75rem", fontWeight: "800", color: "#0f172a", marginTop: "2px" }}>
            {data?.total_orders ?? data?.today_orders ?? 0}
          </div>
          <span style={{ fontSize: "0.725rem", color: "#64748b" }}>Lifetime created</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #d97706", padding: "14px 16px" }}>
          <span style={{ fontSize: "0.725rem", fontWeight: "700", color: "#d97706", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Unassigned
          </span>
          <div style={{ fontSize: "1.75rem", fontWeight: "800", color: "#d97706", marginTop: "2px" }}>
            {data?.unassigned ?? 0}
          </div>
          <span style={{ fontSize: "0.725rem", color: "#64748b" }}>Awaiting available rider</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #0284c7", padding: "14px 16px" }}>
          <span style={{ fontSize: "0.725rem", fontWeight: "700", color: "#0284c7", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Active / In Transit
          </span>
          <div style={{ fontSize: "1.75rem", fontWeight: "800", color: "#0284c7", marginTop: "2px" }}>
            {data?.active_deliveries ?? 0}
          </div>
          <span style={{ fontSize: "0.725rem", color: "#64748b" }}>Assigned & dispatched</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #16a34a", padding: "14px 16px" }}>
          <span style={{ fontSize: "0.725rem", fontWeight: "700", color: "#16a34a", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Delivered
          </span>
          <div style={{ fontSize: "1.75rem", fontWeight: "800", color: "#16a34a", marginTop: "2px" }}>
            {data?.delivered ?? data?.completed_today ?? 0}
          </div>
          <span style={{ fontSize: "0.725rem", color: "#64748b" }}>Completed deliveries</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #e11d48", padding: "14px 16px" }}>
          <span style={{ fontSize: "0.725rem", fontWeight: "700", color: "#e11d48", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Failed / Unreachable
          </span>
          <div style={{ fontSize: "1.75rem", fontWeight: "800", color: "#e11d48", marginTop: "2px" }}>
            {data?.failed_unreachable ?? 0}
          </div>
          <span style={{ fontSize: "0.725rem", color: "#64748b" }}>Exceptions for review</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #dc2626", padding: "14px 16px" }}>
          <span style={{ fontSize: "0.725rem", fontWeight: "700", color: "#dc2626", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            High Risk
          </span>
          <div style={{ fontSize: "1.75rem", fontWeight: "800", color: "#dc2626", marginTop: "2px" }}>
            {data?.high_risk ?? 0}
          </div>
          <span style={{ fontSize: "0.725rem", color: "#64748b" }}>ML risk probability &ge; 70%</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #059669", padding: "14px 16px" }}>
          <span style={{ fontSize: "0.725rem", fontWeight: "700", color: "#059669", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Available Riders
          </span>
          <div style={{ fontSize: "1.75rem", fontWeight: "800", color: "#059669", marginTop: "2px" }}>
            {data?.available_riders ?? 0}
            <span style={{ fontSize: "0.95rem", color: "#64748b", fontWeight: "500" }}> / {data?.total_riders ?? riders.length}</span>
          </div>
          <span style={{ fontSize: "0.725rem", color: "#64748b" }}>With remaining capacity</span>
        </div>
      </div>

      {/* Main Section: Paginated Delivery Operations */}
      <div className="card-modern" style={{ padding: "20px", marginBottom: "24px" }}>
        {/* Title and Filter Toolbar */}
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
              Showing {filteredOperations.length === 0 ? 0 : startIndex + 1}–{Math.min(startIndex + pageSize, totalRecords)} of {totalRecords} matching deliveries
            </span>
          </div>

          {/* Search and Filters */}
          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
            <input
              type="text"
              className="form-control-modern"
              placeholder="Search Order #, Phone, Area, Rider..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              style={{ minWidth: "220px", fontSize: "0.825rem", padding: "6px 12px" }}
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
              <option value="high_risk">High Risk</option>
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

            {riders.length > 0 && (
              <select
                className="form-control-modern"
                value={riderFilter}
                onChange={(e) => setRiderFilter(e.target.value)}
                style={{ width: "auto", fontSize: "0.825rem", padding: "6px 12px" }}
              >
                <option value="all">All Riders</option>
                <option value="unassigned">No Rider Assigned</option>
                {riders.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name} ({r.area})
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
        </div>

        {/* Table Content */}
        {loading ? (
          <p style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
            Loading operations queue...
          </p>
        ) : paginatedOperations.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
            <p>No delivery operations matching the selected filters.</p>
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
                  <th style={{ padding: "8px 10px" }}>Delivery Area</th>
                  <th style={{ padding: "8px 10px" }}>ML Risk</th>
                  <th style={{ padding: "8px 10px" }}>Failure Prob</th>
                  <th style={{ padding: "8px 10px" }}>Status</th>
                  <th style={{ padding: "8px 10px" }}>Assigned Rider</th>
                  <th style={{ padding: "8px 10px", textAlign: "right" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {paginatedOperations.map((op) => {
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
                      <td style={{ padding: "10px" }}>
                        <div style={{ fontWeight: "700", color: "#0f172a" }}>
                          Order #{op.order_id}
                        </div>
                        <span style={{ fontSize: "0.725rem", color: "#64748b" }}>
                          {op.item_name} {op.quantity > 1 ? `(Qty: ${op.quantity})` : ""} • Rs. {Number(op.total_price || 0).toLocaleString()}
                        </span>
                      </td>

                      {/* Customer Column */}
                      <td style={{ padding: "10px", color: "#334155", fontWeight: "500" }}>
                        {op.customer_phone}
                        <div style={{ fontSize: "0.725rem", color: "#64748b" }}>
                          {op.payment_method?.toUpperCase() || (op.is_cod ? "COD" : "PREPAID")}
                        </div>
                      </td>

                      {/* Delivery Area Column */}
                      <td style={{ padding: "10px" }}>
                        <div style={{ fontWeight: "600", color: "#0f172a" }}>{op.area}</div>
                        <span style={{ fontSize: "0.725rem", color: "#64748b", display: "block", maxWidth: "180px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {op.address}
                        </span>
                      </td>

                      {/* Risk Badge Column */}
                      <td style={{ padding: "10px" }}>
                        <RiskBadge risk={op.risk} size="small" />
                      </td>

                      {/* Failure Probability Column */}
                      <td style={{ padding: "10px", fontWeight: "700", color: "#0f172a" }}>
                        {probFormatted}
                      </td>

                      {/* Delivery Status Column */}
                      <td style={{ padding: "10px" }}>
                        <span className={`badge-modern badge-status ${op.status === "delivered" ? "success" : op.status === "unassigned" ? "neutral" : op.status === "failed" || op.status === "unreachable" ? "danger" : "active"}`}>
                          {String(op.status).replace(/_/g, " ")}
                        </span>
                      </td>

                      {/* Rider Column */}
                      <td style={{ padding: "10px" }}>
                        {op.rider ? (
                          <div>
                            <div style={{ fontWeight: "600", color: "#0f172a" }}>
                              {op.rider}
                            </div>
                            {op.rider_load !== undefined && op.rider_load !== null && (
                              <span style={{ fontSize: "0.725rem", color: "#64748b" }}>
                                Load: {op.rider_load} / {op.rider_capacity || 20}
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

                      {/* Action Column */}
                      <td style={{ padding: "10px", textAlign: "right" }}>
                        <div style={{ display: "flex", justifyContent: "flex-end", gap: "6px" }}>
                          {isUnassigned && (
                            <button
                              type="button"
                              onClick={() => navigate(`/admin/dispatch?deliveryId=${op.delivery_id}`)}
                              className="btn-modern btn-modern-primary btn-modern-sm"
                              style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                            >
                              Dispatch
                            </button>
                          )}
                          <Link
                            to={`/admin/deliveries/${op.delivery_id}`}
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

        {/* Pagination Controls */}
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

      {/* Section 3: Rider Fleet Status Table */}
      {riders.length > 0 && (
        <div className="card-modern" style={{ padding: "20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
            <div>
              <h2 style={{ fontSize: "1.15rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                Rider Fleet Status
              </h2>
              <span style={{ fontSize: "0.8rem", color: "#64748b" }}>
                Fleet capacity, real-time workload, and automatic assignment availability
              </span>
            </div>

            <Link to="/admin/riders" style={{ fontSize: "0.825rem", color: "#2563eb", fontWeight: "600" }}>
              Manage Fleet →
            </Link>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.825rem" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e2e8f0", color: "#64748b", fontSize: "0.725rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  <th style={{ padding: "8px 10px" }}>Rider</th>
                  <th style={{ padding: "8px 10px" }}>Area Zone</th>
                  <th style={{ padding: "8px 10px" }}>Phone</th>
                  <th style={{ padding: "8px 10px" }}>Current Workload</th>
                  <th style={{ padding: "8px 10px" }}>Remaining Capacity</th>
                  <th style={{ padding: "8px 10px" }}>Availability</th>
                  <th style={{ padding: "8px 10px", textAlign: "right" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {riders.map((r) => {
                  const isAvail = r.is_available ?? (r.is_active && r.current_order_count < r.max_orders_per_day);
                  const atCapacity = r.current_order_count >= r.max_orders_per_day;

                  return (
                    <tr key={r.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "8px 10px", fontWeight: "600", color: "#0f172a" }}>
                        {r.name}
                      </td>
                      <td style={{ padding: "8px 10px", color: "#334155" }}>
                        {r.area || "General"}
                      </td>
                      <td style={{ padding: "8px 10px", color: "#64748b" }}>
                        {r.phone}
                      </td>
                      <td style={{ padding: "8px 10px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <div style={{ width: "80px", height: "6px", backgroundColor: "#e2e8f0", borderRadius: "3px", overflow: "hidden" }}>
                            <div
                              style={{
                                width: `${Math.min(100, ((r.current_order_count || 0) / (r.max_orders_per_day || 20)) * 100)}%`,
                                height: "100%",
                                backgroundColor: atCapacity ? "#dc2626" : ((r.current_order_count || 0) / (r.max_orders_per_day || 20)) > 0.75 ? "#d97706" : "#2563eb",
                              }}
                            />
                          </div>
                          <span style={{ fontWeight: "600", color: "#0f172a" }}>
                            {r.current_order_count || 0} / {r.max_orders_per_day || 20}
                          </span>
                        </div>
                      </td>
                      <td style={{ padding: "8px 10px", fontWeight: "600", color: r.capacity_remaining > 0 ? "#16a34a" : "#dc2626" }}>
                        {r.capacity_remaining ?? Math.max(0, (r.max_orders_per_day || 20) - (r.current_order_count || 0))} slots
                      </td>
                      <td style={{ padding: "8px 10px" }}>
                        <span
                          className={`badge-modern ${
                            !r.is_active
                              ? "badge-status neutral"
                              : atCapacity
                              ? "badge-status danger"
                              : "badge-status success"
                          }`}
                        >
                          {!r.is_active ? "Inactive" : atCapacity ? "Full Capacity" : "Available"}
                        </span>
                      </td>
                      <td style={{ padding: "8px 10px", textAlign: "right" }}>
                        <Link
                          to={`/admin/riders/${r.id}`}
                          className="btn-modern btn-modern-secondary btn-modern-sm"
                          style={{ padding: "3px 8px", fontSize: "0.725rem" }}
                        >
                          Performance
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;
