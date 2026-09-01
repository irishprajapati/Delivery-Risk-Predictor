import { useEffect, useState, useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  getRiderProfile,
  getRiderDeliveries,
  riderPickupDelivery,
  riderStartDelivery,
  riderCompleteDelivery,
  riderFailDelivery,
  getFailureReasons,
  getErrorMessage,
} from "../../services/api";
import RiskBadge from "../../components/RiskBadge";

const RiderDashboard = () => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [deliveries, setDeliveries] = useState([]);
  const [failureReasons, setFailureReasons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Filters & Pagination
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // Failure modal state
  const [failModalDelivery, setFailModalDelivery] = useState(null);
  const [selectedReasonCode, setSelectedReasonCode] = useState("CUSTOMER_UNAVAILABLE");
  const [failNotes, setFailNotes] = useState("");

  const fetchData = async () => {
    try {
      setLoading(true);
      setError("");
      const [profData, delData, reasonsData] = await Promise.all([
        getRiderProfile(),
        getRiderDeliveries({ limit: 50 }),
        getFailureReasons().catch(() => []),
      ]);

      setProfile(profData);
      setDeliveries(delData.items || []);
      if (reasonsData && reasonsData.length > 0) {
        setFailureReasons(reasonsData);
      }
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load rider dashboard. Please check your connection."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Quick Action Handlers
  const handlePickup = async (deliveryId) => {
    try {
      setActionLoading(true);
      setError("");
      setSuccessMsg("");
      await riderPickupDelivery(deliveryId);
      setSuccessMsg(`Order #${deliveryId} marked as picked up from hub.`);
      await fetchData();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to pick up package"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleStart = async (deliveryId) => {
    try {
      setActionLoading(true);
      setError("");
      setSuccessMsg("");
      await riderStartDelivery(deliveryId);
      setSuccessMsg(`Order #${deliveryId} is now out for delivery.`);
      await fetchData();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to start delivery"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleComplete = async (deliveryId) => {
    try {
      setActionLoading(true);
      setError("");
      setSuccessMsg("");
      await riderCompleteDelivery(deliveryId);
      setSuccessMsg(`Order #${deliveryId} delivered successfully!`);
      await fetchData();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to complete delivery"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleOpenFailModal = (del) => {
    setFailModalDelivery(del);
    setSelectedReasonCode("CUSTOMER_UNAVAILABLE");
    setFailNotes("");
  };

  const handleCloseFailModal = () => {
    setFailModalDelivery(null);
    setSelectedReasonCode("CUSTOMER_UNAVAILABLE");
    setFailNotes("");
  };

  const handleFailSubmit = async (e) => {
    e.preventDefault();
    if (!failModalDelivery) return;

    try {
      setActionLoading(true);
      setError("");
      setSuccessMsg("");
      await riderFailDelivery(failModalDelivery.delivery_id, selectedReasonCode, failNotes);
      setSuccessMsg(`Delivery issue reported for Order #${failModalDelivery.order_id}.`);
      handleCloseFailModal();
      await fetchData();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to record delivery issue"));
    } finally {
      setActionLoading(false);
    }
  };

  // KPIs
  const assignedCount = deliveries.filter((d) => d.status === "assigned").length;
  const inProgressCount = deliveries.filter((d) => ["picked_up", "out_for_delivery"].includes(d.status)).length;
  const completedCount = deliveries.filter((d) => d.status === "delivered").length;
  const failedCount = deliveries.filter((d) => ["failed", "unreachable"].includes(d.status)).length;

  // Filtered Deliveries
  const filteredDeliveries = useMemo(() => {
    return deliveries.filter((d) => {
      const q = search.trim().toLowerCase();
      const matchesSearch =
        !q ||
        String(d.order_id).toLowerCase().includes(q) ||
        String(d.customer_phone || "").toLowerCase().includes(q) ||
        String(d.area || "").toLowerCase().includes(q) ||
        String(d.address || "").toLowerCase().includes(q) ||
        String(d.item_name || "").toLowerCase().includes(q);

      const status = String(d.status || "").toLowerCase();
      let matchesStatus = true;
      if (statusFilter === "assigned") {
        matchesStatus = status === "assigned";
      } else if (statusFilter === "in_progress") {
        matchesStatus = ["picked_up", "out_for_delivery"].includes(status);
      } else if (statusFilter === "picked_up") {
        matchesStatus = status === "picked_up";
      } else if (statusFilter === "out_for_delivery") {
        matchesStatus = status === "out_for_delivery";
      } else if (statusFilter === "delivered") {
        matchesStatus = status === "delivered";
      } else if (statusFilter === "failed") {
        matchesStatus = ["failed", "unreachable"].includes(status);
      }

      return matchesSearch && matchesStatus;
    });
  }, [deliveries, search, statusFilter]);

  // Pagination
  const totalRecords = filteredDeliveries.length;
  const totalPages = Math.max(1, Math.ceil(totalRecords / pageSize));
  const currentPage = Math.min(page, totalPages);
  const startIndex = (currentPage - 1) * pageSize;
  const paginatedDeliveries = filteredDeliveries.slice(startIndex, startIndex + pageSize);

  const selectedReasonObj = failureReasons.find((r) => r.code === selectedReasonCode);
  const isNotesRequired = selectedReasonObj?.requires_notes || selectedReasonCode === "OTHER";

  return (
    <div className="animate-fade-in" style={{ maxWidth: "1100px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h1 style={{ fontSize: "1.65rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
              Rider Operations
            </h1>
            <span className={`badge-modern ${profile?.is_active ? "badge-status success" : "badge-status danger"}`}>
              {profile?.is_active ? "● Online / Active" : "Offline"}
            </span>
          </div>
          <p style={{ fontSize: "0.875rem", color: "#64748b", margin: "4px 0 0" }}>
            Welcome, <strong>{profile?.name || "Rider"}</strong> • Primary Zone: <strong>{profile?.area || "Kathmandu Valley"}</strong>
          </p>
        </div>

        <button
          type="button"
          onClick={fetchData}
          disabled={loading || actionLoading}
          className="btn-modern btn-modern-secondary btn-modern-sm"
        >
          ↻ Refresh Deliveries
        </button>
      </div>

      {/* Notifications */}
      {error && (
        <div style={{ padding: "12px 16px", background: "#fef2f2", color: "#dc2626", borderRadius: "8px", border: "1px solid #fecaca", marginBottom: "18px", fontSize: "0.875rem" }}>
          ✕ {error}
        </div>
      )}

      {successMsg && (
        <div style={{ padding: "12px 16px", background: "#f0fdf4", color: "#16a34a", borderRadius: "8px", border: "1px solid #bbf7d0", marginBottom: "18px", fontWeight: "600", fontSize: "0.875rem" }}>
          {successMsg}
        </div>
      )}

      {/* Operational KPI Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "14px",
          marginBottom: "24px",
        }}
      >
        <div className="card-modern" style={{ borderLeft: "4px solid #d97706", padding: "16px 18px" }}>
          <span style={{ fontSize: "0.725rem", fontWeight: "700", color: "#d97706", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Assigned (To Pick Up)
          </span>
          <div style={{ fontSize: "1.85rem", fontWeight: "800", color: "#0f172a", marginTop: "2px" }}>
            {assignedCount}
          </div>
          <span style={{ fontSize: "0.725rem", color: "#64748b" }}>Ready for hub pickup</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #0284c7", padding: "16px 18px" }}>
          <span style={{ fontSize: "0.725rem", fontWeight: "700", color: "#0284c7", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            In Progress
          </span>
          <div style={{ fontSize: "1.85rem", fontWeight: "800", color: "#0284c7", marginTop: "2px" }}>
            {inProgressCount}
          </div>
          <span style={{ fontSize: "0.725rem", color: "#64748b" }}>Picked up & Out for delivery</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #16a34a", padding: "16px 18px" }}>
          <span style={{ fontSize: "0.725rem", fontWeight: "700", color: "#16a34a", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Completed Today
          </span>
          <div style={{ fontSize: "1.85rem", fontWeight: "800", color: "#16a34a", marginTop: "2px" }}>
            {completedCount}
          </div>
          <span style={{ fontSize: "0.725rem", color: "#64748b" }}>Successfully delivered</span>
        </div>

        <div className="card-modern" style={{ borderLeft: "4px solid #2563eb", padding: "16px 18px" }}>
          <span style={{ fontSize: "0.725rem", fontWeight: "700", color: "#2563eb", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Current Workload
          </span>
          <div style={{ fontSize: "1.85rem", fontWeight: "800", color: "#0f172a", marginTop: "2px" }}>
            {profile?.current_order_count || 0}
            <span style={{ fontSize: "0.95rem", color: "#64748b", fontWeight: "500" }}> / {profile?.max_orders_per_day || 20}</span>
          </div>
          <div style={{ width: "100%", height: "5px", backgroundColor: "#e2e8f0", borderRadius: "3px", marginTop: "6px", overflow: "hidden" }}>
            <div
              style={{
                width: `${Math.min(100, (((profile?.current_order_count || 0) / (profile?.max_orders_per_day || 20)) * 100))}%`,
                height: "100%",
                backgroundColor: (profile?.current_order_count || 0) >= (profile?.max_orders_per_day || 20) ? "#dc2626" : "#2563eb",
              }}
            />
          </div>
        </div>
      </div>

      {/* Deliveries List Card */}
      <div className="card-modern" style={{ padding: "20px" }}>
        {/* Controls Toolbar */}
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
            <h2 style={{ fontSize: "1.15rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
              My Assigned Deliveries
            </h2>
            <span style={{ fontSize: "0.8rem", color: "#64748b" }}>
              Showing {filteredDeliveries.length === 0 ? 0 : startIndex + 1}–{Math.min(startIndex + pageSize, totalRecords)} of {totalRecords} assigned packages
            </span>
          </div>

          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
            <input
              type="text"
              className="form-control-modern"
              placeholder="Search Order #, Phone, Area, Item..."
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
              <option value="all">All Deliveries</option>
              <option value="assigned">Assigned (To Pick Up)</option>
              <option value="in_progress">In Progress (Active)</option>
              <option value="picked_up">Picked Up</option>
              <option value="out_for_delivery">Out for Delivery</option>
              <option value="delivered">Delivered</option>
              <option value="failed">Failed / Unreachable</option>
            </select>
          </div>
        </div>

        {/* Deliveries List */}
        {loading ? (
          <p style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
            Loading your assigned deliveries...
          </p>
        ) : paginatedDeliveries.length === 0 ? (
          <div style={{ textAlign: "center", padding: "48px 20px", color: "#64748b" }}>
            <div style={{ fontSize: "0.95rem", fontWeight: "600", color: "#64748b", marginBottom: "8px" }}>No active deliveries</div>
            <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#0f172a", margin: "0 0 4px" }}>
              No deliveries found
            </h3>
            <p style={{ fontSize: "0.85rem", margin: 0 }}>
              {statusFilter !== "all" || search
                ? "No packages match your search filter."
                : "You currently have no active deliveries assigned."}
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {paginatedDeliveries.map((d) => {
              const probFormatted = d.probability != null ? `${(Number(d.probability) * 100).toFixed(1)}%` : null;
              const isAssigned = d.status === "assigned";
              const isPickedUp = d.status === "picked_up";
              const isOutForDelivery = d.status === "out_for_delivery";
              const isDelivered = d.status === "delivered";
              const isFailed = d.status === "failed" || d.status === "unreachable";

              return (
                <div
                  key={d.delivery_id}
                  className="card-modern"
                  style={{
                    padding: "16px",
                    border: isOutForDelivery ? "1.5px solid #0284c7" : "1px solid #e2e8f0",
                    backgroundColor: isOutForDelivery ? "#f8fafc" : "#ffffff",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "16px",
                  }}
                >
                  {/* Left: Info */}
                  <div style={{ flex: "1 1 320px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "6px" }}>
                      <span style={{ fontWeight: "800", color: "#0f172a", fontSize: "1.05rem" }}>
                        Order #{d.order_id}
                      </span>
                      <span className={`badge-modern badge-status ${isDelivered ? "success" : isAssigned ? "neutral" : isFailed ? "danger" : "active"}`}>
                        {String(d.status).replace(/_/g, " ")}
                      </span>
                      <RiskBadge risk={d.risk} size="small" />
                      {probFormatted && (
                        <span style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: "600" }}>
                          Fail Risk: {probFormatted}
                        </span>
                      )}
                    </div>

                    <div style={{ fontSize: "0.875rem", color: "#334155", fontWeight: "600", marginBottom: "4px" }}>
                      {d.item_name} {d.quantity > 1 ? `× ${d.quantity}` : ""} • Rs. {Number(d.total_price || 0).toLocaleString()} ({d.payment_method?.toUpperCase() || (d.is_cod ? "COD" : "PREPAID")})
                    </div>

                    <div style={{ fontSize: "0.825rem", color: "#475569" }}>
                      <strong>{d.area}</strong> • {d.address}
                    </div>

                    <div style={{ fontSize: "0.8rem", color: "#64748b", marginTop: "4px" }}>
                      Customer: <strong>{d.customer_phone}</strong>
                      {d.failure_reason && (
                        <span style={{ color: "#dc2626", marginLeft: "12px", fontWeight: "600" }}>
                          ✕ Reason: {d.failure_reason}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Right: Operational Actions */}
                  <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}>
                    {isAssigned && (
                      <button
                        type="button"
                        onClick={() => handlePickup(d.delivery_id)}
                        disabled={actionLoading}
                        className="btn-modern btn-modern-primary btn-modern-sm"
                        style={{ padding: "6px 14px", fontSize: "0.825rem" }}
                      >
                        Pick Up Package
                      </button>
                    )}

                    {isPickedUp && (
                      <button
                        type="button"
                        onClick={() => handleStart(d.delivery_id)}
                        disabled={actionLoading}
                        className="btn-modern btn-modern-primary btn-modern-sm"
                        style={{ padding: "6px 14px", fontSize: "0.825rem", backgroundColor: "#0284c7" }}
                      >
                        Start Transit
                      </button>
                    )}

                    {isOutForDelivery && (
                      <>
                        <button
                          type="button"
                          onClick={() => handleComplete(d.delivery_id)}
                          disabled={actionLoading}
                          className="btn-modern btn-modern-sm"
                          style={{ padding: "6px 14px", fontSize: "0.825rem", backgroundColor: "#16a34a", color: "#ffffff", border: "none" }}
                        >
                          Mark Delivered
                        </button>

                        <button
                          type="button"
                          onClick={() => handleOpenFailModal(d)}
                          disabled={actionLoading}
                          className="btn-modern btn-modern-sm"
                          style={{ padding: "6px 12px", fontSize: "0.825rem", backgroundColor: "#fef2f2", color: "#dc2626", border: "1px solid #fecaca" }}
                        >
                          Report Issue
                        </button>
                      </>
                    )}

                    {(isPickedUp || isOutForDelivery) && (
                      <a
                        href={`https://www.google.com/maps/dir/?api=1&destination=${d.latitude || 27.6744},${d.longitude || 85.3123}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-modern btn-modern-secondary btn-modern-sm"
                        style={{ padding: "6px 10px", fontSize: "0.8rem", textDecoration: "none" }}
                      >
                        Nav
                      </a>
                    )}

                    <Link
                      to={`/rider/deliveries/${d.delivery_id}`}
                      className="btn-modern btn-modern-secondary btn-modern-sm"
                      style={{ padding: "6px 12px", fontSize: "0.825rem" }}
                    >
                      View Details
                    </Link>
                  </div>
                </div>
              );
            })}
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
              marginTop: "18px",
              paddingTop: "14px",
              borderTop: "1px solid #f1f5f9",
            }}
          >
            <div style={{ fontSize: "0.825rem", color: "#64748b" }}>
              Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong> ({totalRecords} deliveries)
            </div>

            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(p - 1, 1))}
                disabled={currentPage <= 1}
                className="btn-modern btn-modern-secondary btn-modern-sm"
                style={{ padding: "4px 10px", fontSize: "0.8rem" }}
              >
                ← Previous
              </button>
              <span style={{ fontSize: "0.825rem", fontWeight: "600", padding: "0 6px" }}>
                {currentPage}
              </span>
              <button
                type="button"
                onClick={() => setPage((p) => Math.min(p + 1, totalPages))}
                disabled={currentPage >= totalPages}
                className="btn-modern btn-modern-secondary btn-modern-sm"
                style={{ padding: "4px 10px", fontSize: "0.8rem" }}
              >
                Next →
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Failure Reporting Modal */}
      {failModalDelivery && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            className="card-modern animate-fade-in"
            style={{
              width: "100%",
              maxWidth: "480px",
              background: "#ffffff",
              padding: "24px",
              borderRadius: "12px",
              boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1)",
            }}
          >
            <h3 style={{ fontSize: "1.2rem", fontWeight: "700", color: "#0f172a", margin: "0 0 6px" }}>
              Report Delivery Issue
            </h3>
            <p style={{ fontSize: "0.85rem", color: "#64748b", margin: "0 0 16px" }}>
              Order #{failModalDelivery.order_id} ({failModalDelivery.item_name}) • {failModalDelivery.customer_phone}
            </p>

            <form onSubmit={handleFailSubmit}>
              <div style={{ marginBottom: "14px" }}>
                <label style={{ display: "block", fontSize: "0.825rem", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  Failure Reason Category *
                </label>
                <select
                  className="form-control-modern"
                  value={selectedReasonCode}
                  onChange={(e) => setSelectedReasonCode(e.target.value)}
                  style={{ width: "100%", fontSize: "0.875rem" }}
                  required
                >
                  {failureReasons.length > 0 ? (
                    failureReasons.map((r) => (
                      <option key={r.code} value={r.code}>
                        {r.label} {r.unreachable ? "(Unreachable)" : "(Failed)"}
                      </option>
                    ))
                  ) : (
                    <>
                      <option value="CUSTOMER_UNAVAILABLE">Customer Unavailable (Unreachable)</option>
                      <option value="PHONE_UNREACHABLE">Phone Unreachable / Switched Off</option>
                      <option value="CUSTOMER_REQUESTED_RESCHEDULE">Customer Requested Reschedule</option>
                      <option value="CUSTOMER_REFUSED">Customer Refused Delivery</option>
                      <option value="WRONG_ADDRESS">Wrong Address / Incomplete</option>
                      <option value="ADDRESS_NOT_FOUND">Address Not Found</option>
                      <option value="ROAD_INACCESSIBLE">Road Inaccessible / Blocked</option>
                      <option value="VEHICLE_OR_BIKE_ISSUE">Vehicle Breakdown / Issue</option>
                      <option value="WEATHER_OR_ROAD_CONDITION">Severe Weather / Hazard</option>
                      <option value="PACKAGE_DAMAGED">Package Damaged</option>
                      <option value="PAYMENT_ISSUE">Payment Issue</option>
                      <option value="OTHER">Other Reason</option>
                    </>
                  )}
                </select>
              </div>

              <div style={{ marginBottom: "18px" }}>
                <label style={{ display: "block", fontSize: "0.825rem", fontWeight: "600", color: "#334155", marginBottom: "4px" }}>
                  Operational Notes {isNotesRequired ? "(Required *)" : "(Optional)"}
                </label>
                <textarea
                  className="form-control-modern"
                  rows={3}
                  placeholder="Explain what occurred (e.g., Called 3 times, phone switched off at gate)..."
                  value={failNotes}
                  onChange={(e) => setFailNotes(e.target.value)}
                  style={{ width: "100%", fontSize: "0.85rem", resize: "vertical" }}
                  required={isNotesRequired}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  onClick={handleCloseFailModal}
                  disabled={actionLoading}
                  className="btn-modern btn-modern-secondary btn-modern-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  className="btn-modern btn-modern-sm"
                  style={{ backgroundColor: "#dc2626", color: "#ffffff", border: "none", padding: "6px 16px" }}
                >
                  {actionLoading ? "Submitting..." : "Confirm & Submit Issue"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default RiderDashboard;
