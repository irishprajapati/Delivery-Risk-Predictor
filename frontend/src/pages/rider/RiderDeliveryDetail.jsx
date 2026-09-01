import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import {
  getRiderDelivery,
  riderPickupDelivery,
  riderStartDelivery,
  riderCompleteDelivery,
  riderFailDelivery,
  getFailureReasons,
  getErrorMessage,
} from "../../services/api";
import RiskBadge from "../../components/RiskBadge";

const RiderDeliveryDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [delivery, setDelivery] = useState(null);
  const [failureReasons, setFailureReasons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Failure modal state
  const [showFailModal, setShowFailModal] = useState(false);
  const [selectedReasonCode, setSelectedReasonCode] = useState("CUSTOMER_UNAVAILABLE");
  const [failNotes, setFailNotes] = useState("");

  const fetchDelivery = async () => {
    try {
      setLoading(true);
      setError("");
      const [delData, reasonsData] = await Promise.all([
        getRiderDelivery(id),
        getFailureReasons().catch(() => []),
      ]);

      setDelivery(delData);
      if (reasonsData && reasonsData.length > 0) {
        setFailureReasons(reasonsData);
      }
    } catch (err) {
      setError(getErrorMessage(err, "Could not load delivery details or you are not authorized."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDelivery();
  }, [id]);

  const handlePickup = async () => {
    try {
      setActionLoading(true);
      setError("");
      setSuccessMsg("");
      await riderPickupDelivery(id);
      setSuccessMsg("Package picked up from hub successfully.");
      await fetchDelivery();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to pick up package"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleStart = async () => {
    try {
      setActionLoading(true);
      setError("");
      setSuccessMsg("");
      await riderStartDelivery(id);
      setSuccessMsg("Delivery is now out for delivery.");
      await fetchDelivery();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to start delivery"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleComplete = async () => {
    try {
      setActionLoading(true);
      setError("");
      setSuccessMsg("");
      await riderCompleteDelivery(id);
      setSuccessMsg("Delivery completed successfully!");
      await fetchDelivery();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to complete delivery"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleFailSubmit = async (e) => {
    e.preventDefault();
    try {
      setActionLoading(true);
      setError("");
      setSuccessMsg("");
      await riderFailDelivery(id, selectedReasonCode, failNotes);
      setSuccessMsg("Delivery issue recorded.");
      setShowFailModal(false);
      await fetchDelivery();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to record delivery issue"));
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card-modern" style={{ textAlign: "center", padding: "48px 20px" }}>
        <p style={{ color: "#64748b" }}>Loading package and delivery details...</p>
      </div>
    );
  }

  if (error && !delivery) {
    return (
      <div className="card-modern" style={{ borderColor: "#fecaca", backgroundColor: "#fef2f2", padding: "24px" }}>
        <p style={{ color: "#dc2626", marginBottom: "14px" }}>✕ {error}</p>
        <Link to="/rider/dashboard" className="btn-modern btn-modern-secondary">
          ← Back to Rider Dashboard
        </Link>
      </div>
    );
  }

  const order = delivery?.order || {};
  const customer = delivery?.customer || {};
  const location = delivery?.location || {};
  const risk = delivery?.risk || {};
  const currentStatus = String(delivery?.status || "unassigned").toLowerCase();

  const isAssigned = currentStatus === "assigned";
  const isPickedUp = currentStatus === "picked_up";
  const isOutForDelivery = currentStatus === "out_for_delivery";
  const isDelivered = currentStatus === "delivered";
  const isFailed = currentStatus === "failed" || currentStatus === "unreachable";

  const probFormatted = risk.probability != null ? `${(Number(risk.probability) * 100).toFixed(1)}%` : "—";
  const selectedReasonObj = failureReasons.find((r) => r.code === selectedReasonCode);
  const isNotesRequired = selectedReasonObj?.requires_notes || selectedReasonCode === "OTHER";

  return (
    <div className="animate-fade-in" style={{ maxWidth: "900px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Top Navigation */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
        <Link to="/rider/dashboard" style={{ fontSize: "0.85rem", color: "#2563eb", fontWeight: "600" }}>
          ← Back to My Deliveries
        </Link>
        <button
          type="button"
          onClick={fetchDelivery}
          disabled={loading || actionLoading}
          className="btn-modern btn-modern-secondary btn-modern-sm"
        >
          ↻ Refresh
        </button>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "#fef2f2", color: "#dc2626", borderRadius: "8px", border: "1px solid #fecaca", marginBottom: "16px", fontSize: "0.875rem" }}>
          ✕ {error}
        </div>
      )}

      {successMsg && (
        <div style={{ padding: "12px 16px", background: "#f0fdf4", color: "#16a34a", borderRadius: "8px", border: "1px solid #bbf7d0", marginBottom: "16px", fontWeight: "600", fontSize: "0.875rem" }}>
          {successMsg}
        </div>
      )}

      {/* Main Order Card */}
      <div className="card-modern" style={{ padding: "24px", marginBottom: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", borderBottom: "1px solid #f1f5f9", paddingBottom: "16px", marginBottom: "16px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h1 style={{ fontSize: "1.45rem", fontWeight: "800", color: "#0f172a", margin: 0 }}>
                Order #{order.id}
              </h1>
              <span className={`badge-modern badge-status ${isDelivered ? "success" : isAssigned ? "neutral" : isFailed ? "danger" : "active"}`}>
                {currentStatus.replace(/_/g, " ")}
              </span>
            </div>
            <span style={{ color: "#64748b", fontSize: "0.825rem" }}>
              Delivery #{delivery.delivery_id} • Assigned: {delivery.assigned_at ? new Date(delivery.assigned_at).toLocaleString() : "Recently"}
            </span>
          </div>

          <div style={{ textAlign: "right" }}>
            <RiskBadge risk={risk.level} />
            {probFormatted !== "—" && (
              <div style={{ fontSize: "0.775rem", color: "#64748b", fontWeight: "600", marginTop: "2px" }}>
                Failure Prob: {probFormatted}
              </div>
            )}
          </div>
        </div>

        {/* 2-Column Info Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "16px", marginBottom: "20px" }}>
          {/* Order Details */}
          <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.725rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
              Package Details
            </span>
            <div style={{ fontSize: "1rem", fontWeight: "700", color: "#0f172a", marginTop: "4px" }}>
              {order.item_name} (Qty: {order.quantity})
            </div>
            <div style={{ fontSize: "0.875rem", color: "#334155", marginTop: "4px" }}>
              Total Value: <strong>Rs. {Number(order.total_price || 0).toLocaleString()}</strong>
            </div>
            <div style={{ fontSize: "0.875rem", color: "#334155", marginTop: "2px" }}>
              Payment: <strong style={{ color: order.is_cod ? "#b45309" : "#15803d" }}>
                {order.is_cod ? "Cash on Delivery (Collect Cash)" : `Prepaid (${order.payment_method?.toUpperCase()})`}
              </strong>
            </div>
          </div>

          {/* Customer & Location Details */}
          <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.725rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
              Customer & Destination
            </span>
            <div style={{ fontSize: "1rem", fontWeight: "700", color: "#0f172a", marginTop: "4px" }}>
              <a href={`tel:${customer.phone}`} style={{ color: "#2563eb", textDecoration: "none" }}>{customer.phone}</a>
            </div>
            <div style={{ fontSize: "0.875rem", color: "#334155", marginTop: "4px" }}>
              <strong>{location.area}</strong> • {location.address}
            </div>
            <div style={{ marginTop: "10px" }}>
              <a
                href={`https://www.google.com/maps/dir/?api=1&destination=${location.latitude},${location.longitude}`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-modern btn-modern-primary btn-modern-sm"
                style={{ textDecoration: "none", display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "0.8rem", padding: "5px 12px" }}
              >
                Open Maps Navigation
              </a>
            </div>
          </div>
        </div>

        {/* Failure banner if failed */}
        {delivery.failure_reason && (
          <div style={{ padding: "14px 18px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "8px", marginBottom: "20px" }}>
            <div style={{ fontWeight: "700", color: "#dc2626", fontSize: "0.9rem" }}>
              ✕ Delivery Failure Reason:
            </div>
            <p style={{ fontSize: "0.85rem", color: "#991b1b", margin: "4px 0 0" }}>
              {delivery.failure_reason}
            </p>
          </div>
        )}

        {/* Lifecycle Action Panel */}
        <div
          style={{
            padding: "20px",
            background: "#eff6ff",
            border: "1.5px solid #bfdbfe",
            borderRadius: "10px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "14px",
          }}
        >
          <div>
            <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#1e3a8a", margin: "0 0 2px" }}>
              Delivery Action Panel
            </h3>
            <span style={{ fontSize: "0.825rem", color: "#3b82f6" }}>
              {isAssigned && "Package is ready for pickup at Balkumari Hub."}
              {isPickedUp && "Package is in your possession. Ready to start journey."}
              {isOutForDelivery && "Transit in progress. Complete upon customer handover."}
              {isDelivered && "This delivery is completed."}
              {isFailed && "✕ This delivery was reported with an issue."}
            </span>
          </div>

          <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
            {isAssigned && (
              <button
                type="button"
                onClick={handlePickup}
                disabled={actionLoading}
                className="btn-modern btn-modern-primary"
                style={{ padding: "8px 18px", fontSize: "0.9rem" }}
              >
                Pick Up Package from Hub
              </button>
            )}

            {isPickedUp && (
              <button
                type="button"
                onClick={handleStart}
                disabled={actionLoading}
                className="btn-modern btn-modern-primary"
                style={{ padding: "8px 18px", fontSize: "0.9rem", backgroundColor: "#0284c7" }}
              >
                Start Transit (Out for Delivery)
              </button>
            )}

            {isOutForDelivery && (
              <>
                <button
                  type="button"
                  onClick={handleComplete}
                  disabled={actionLoading}
                  className="btn-modern"
                  style={{ padding: "8px 18px", fontSize: "0.9rem", backgroundColor: "#16a34a", color: "#ffffff", border: "none", borderRadius: "6px", fontWeight: "700" }}
                >
                  Mark Delivered
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setSelectedReasonCode("CUSTOMER_UNAVAILABLE");
                    setFailNotes("");
                    setShowFailModal(true);
                  }}
                  disabled={actionLoading}
                  className="btn-modern btn-modern-secondary"
                  style={{ padding: "8px 16px", fontSize: "0.9rem", color: "#dc2626", borderColor: "#fecaca" }}
                >
                  Report Issue
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* ML Failure Prediction Insights */}
      {risk.reasons && risk.reasons.length > 0 && (
        <div className="card-modern" style={{ padding: "20px", marginBottom: "20px" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: "700", color: "#0f172a", margin: "0 0 12px" }}>
            Delivery Intelligence & Operational Risk Factors
          </h3>
          <ul style={{ margin: 0, paddingLeft: "20px", fontSize: "0.85rem", color: "#475569" }}>
            {risk.reasons.map((r, i) => (
              <li key={i} style={{ marginBottom: "6px" }}>{r}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Failure Modal */}
      {showFailModal && (
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
              Order #{order.id} ({order.item_name}) • {customer.phone}
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
                  placeholder="Explain what occurred..."
                  value={failNotes}
                  onChange={(e) => setFailNotes(e.target.value)}
                  style={{ width: "100%", fontSize: "0.85rem", resize: "vertical" }}
                  required={isNotesRequired}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowFailModal(false)}
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

export default RiderDeliveryDetail;
