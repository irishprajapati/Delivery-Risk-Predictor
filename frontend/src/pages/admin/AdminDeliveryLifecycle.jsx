import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  getDeliverySummary,
  getDeliveryRiderOptions,
  assignDeliveryRider,
  startDelivery,
  markOutForDelivery,
  completeDelivery,
  failDelivery,
  reassignDelivery,
  cancelDelivery,
  getErrorMessage,
} from "../../services/api";
import StatusTimeline from "../../components/StatusTimeline";
import RiskBadge from "../../components/RiskBadge";

const markerIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const AdminDeliveryLifecycle = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [delivery, setDelivery] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Other riders collapsible
  const [showOtherRiders, setShowOtherRiders] = useState(false);

  // Failure modal state
  const [showFailModal, setShowFailModal] = useState(false);
  const [failReason, setFailReason] = useState("Customer unreachable after repeated attempts");

  const fetchDelivery = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getDeliverySummary(id);
      setDelivery(data);

      if (data.status === "unassigned") {
        fetchRiderCandidates();
      }
    } catch (err) {
      setError(getErrorMessage(err, "Could not load delivery details"));
    } finally {
      setLoading(false);
    }
  };

  const fetchRiderCandidates = async () => {
    try {
      setCandidatesLoading(true);
      const res = await getDeliveryRiderOptions(id);
      setCandidates(res.candidates || []);
    } catch (err) {
      console.warn("Could not load rider candidates:", err);
    } finally {
      setCandidatesLoading(false);
    }
  };

  useEffect(() => {
    fetchDelivery();
  }, [id]);

  const handleAction = async (actionFn, name) => {
    try {
      setActionLoading(true);
      setError("");
      setSuccessMsg("");
      await actionFn();
      setSuccessMsg(`Action '${name}' executed successfully!`);
      await fetchDelivery();
    } catch (err) {
      setError(getErrorMessage(err, `Failed to execute ${name}`));
    } finally {
      setActionLoading(false);
    }
  };

  const handleAssignRider = async (riderId = null) => {
    try {
      setActionLoading(true);
      setError("");
      setSuccessMsg("");
      const res = await assignDeliveryRider(id, riderId);
      setSuccessMsg(res.message || "Rider assigned successfully!");
      await fetchDelivery();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to assign rider"));
    } finally {
      setActionLoading(false);
    }
  };

  const handleFailSubmit = async (unreachable = false) => {
    try {
      setActionLoading(true);
      setError("");
      setShowFailModal(false);
      await failDelivery(id, failReason, unreachable);
      setSuccessMsg(`Delivery marked as ${unreachable ? "unreachable" : "failed"}.`);
      await fetchDelivery();
    } catch (err) {
      setError(getErrorMessage(err, "Failed to record failure"));
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card-modern" style={{ textAlign: "center", padding: "48px 24px" }}>
        <p style={{ color: "#64748b" }}>Loading delivery details & ML risk assessment...</p>
      </div>
    );
  }

  if (error && !delivery) {
    return (
      <div className="card-modern" style={{ borderColor: "#fecaca", backgroundColor: "#fef2f2" }}>
        <p style={{ color: "#dc2626", marginBottom: "12px" }}>{error}</p>
        <Link to="/admin/dashboard" className="btn-modern btn-modern-secondary">
          ← Back to Operations Dashboard
        </Link>
      </div>
    );
  }

  const order = delivery?.order || {};
  const rider = delivery?.rider || null;
  const location = delivery?.location || {};
  const prediction = delivery?.prediction || null;
  const currentStatus = String(delivery?.status || "unassigned").toLowerCase();
  const riskLevel = String(delivery?.risk_level || prediction?.risk || order?.risk_level || "LOW").toUpperCase();

  const isAssigned = currentStatus === "assigned";
  const isPickedUp = currentStatus === "picked_up" || currentStatus === "started";
  const isOutForDelivery = currentStatus === "out_for_delivery";
  const isDelivered = currentStatus === "delivered";
  const isFailed = currentStatus === "failed" || currentStatus === "unreachable";
  const isUnassigned = currentStatus === "unassigned";

  const coordinates = {
    lat: location?.latitude || order?.latitude || 27.6744,
    lng: location?.longitude || order?.longitude || 85.3123,
  };

  const failureProb = prediction?.probability != null ? (Number(prediction.probability) * 100).toFixed(1) : "—";
  const predictedClass = prediction?.predicted_class || (prediction?.prediction === 1 ? "Delivery Failure Likely" : "Successful Delivery");
  const reasonsList = prediction?.reasons?.length > 0 ? prediction.reasons : [
    "Location historical reliability within normal thresholds",
    "Customer address resolved successfully",
    "Estimated route distance and traffic within standard parameters",
  ];

  const topRecommendedRider = candidates[0] || null;

  return (
    <div className="animate-fade-in" style={{ maxWidth: "1080px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Navigation */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
        <Link to="/admin/dashboard" style={{ fontSize: "0.85rem", color: "#2563eb", fontWeight: "600" }}>
          ← Back to Operations Dashboard
        </Link>
        <button
          type="button"
          onClick={fetchDelivery}
          className="btn-modern btn-modern-secondary btn-modern-sm"
        >
          ↻ Refresh Delivery
        </button>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "#fef2f2", color: "#dc2626", borderRadius: "8px", border: "1px solid #fecaca", marginBottom: "16px" }}>
          {error}
        </div>
      )}

      {successMsg && (
        <div style={{ padding: "12px 16px", background: "#f0fdf4", color: "#16a34a", borderRadius: "8px", border: "1px solid #bbf7d0", marginBottom: "16px", fontWeight: "600" }}>
          ✓ {successMsg}
        </div>
      )}

      {/* Main Container */}
      <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>

        {/* 1. Order & Header Card */}
        <div className="card-modern" style={{ padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", borderBottom: "1px solid #f1f5f9", paddingBottom: "16px", marginBottom: "16px" }}>
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <h1 style={{ fontSize: "1.5rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                  Order #{order.id || delivery.order_id}
                </h1>
                <span className={`badge-modern badge-status ${isDelivered ? "success" : isUnassigned ? "neutral" : "active"}`}>
                  {currentStatus.replace(/_/g, " ")}
                </span>
              </div>
              <span style={{ color: "#64748b", fontSize: "0.85rem" }}>
                Delivery #{delivery.delivery_id} • Created: {order.created_at ? new Date(order.created_at).toLocaleString() : "Recently"}
              </span>
            </div>

            <div style={{ textAlign: "right" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
                Risk Classification
              </span>
              <div>
                <RiskBadge risk={riskLevel} />
              </div>
            </div>
          </div>

          {/* Grid: Order Info & Customer Details */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "16px" }}>
            <div style={{ padding: "14px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
                Order Information
              </span>
              <div style={{ fontSize: "0.925rem", fontWeight: "600", color: "#0f172a", marginTop: "4px" }}>
                Item: {order.item_name || "Package"} (Qty: {order.quantity || 1})
              </div>
              <div style={{ fontSize: "0.85rem", color: "#475569", marginTop: "2px" }}>
                Total Value: <strong>Rs. {Number(order.total_price || 0).toLocaleString()}</strong>
              </div>
              <div style={{ fontSize: "0.85rem", color: "#475569", marginTop: "2px" }}>
                Payment: <strong>{order.is_cod ? "Cash on Delivery (COD)" : `Prepaid (Rs. ${Number(order.prepaid_amount || 0).toLocaleString()})`}</strong>
              </div>
            </div>

            <div style={{ padding: "14px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
                Customer Information
              </span>
              <div style={{ fontSize: "1.05rem", fontWeight: "700", color: "#0f172a", marginTop: "4px" }}>
                📱 {order.customer_phone || "—"}
              </div>
              <div style={{ fontSize: "0.85rem", color: "#475569", marginTop: "2px" }}>
                Destination Area: <strong>{order.area || "Kathmandu Valley"}</strong>
              </div>
              <div style={{ fontSize: "0.85rem", color: "#475569", marginTop: "2px" }}>
                Address: {order.address || "—"}
              </div>
            </div>
          </div>
        </div>

        {/* 2. ML Risk Assessment Section */}
        <div
          className="card-modern"
          style={{
            padding: "24px",
            borderLeft: riskLevel === "HIGH" ? "5px solid #dc2626" : riskLevel === "MEDIUM" ? "5px solid #d97706" : "5px solid #16a34a",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
            <div>
              <h2 style={{ fontSize: "1.15rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                ML Risk Assessment
              </h2>
              <span style={{ fontSize: "0.825rem", color: "#64748b" }}>
                Evaluated by Machine Learning Delivery Failure Model
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <span style={{ fontSize: "0.85rem", color: "#475569" }}>
                Failure Probability: <strong style={{ color: "#0f172a", fontSize: "1.1rem" }}>{failureProb}%</strong>
              </span>
              <RiskBadge risk={riskLevel} />
            </div>
          </div>

          {/* Operational Policy Callout */}
          <div
            style={{
              padding: "12px 14px",
              borderRadius: "8px",
              marginBottom: "16px",
              fontSize: "0.85rem",
              background: riskLevel === "HIGH" ? "#fef2f2" : riskLevel === "MEDIUM" ? "#fffbeb" : "#f0fdf4",
              border: `1px solid ${riskLevel === "HIGH" ? "#fecaca" : riskLevel === "MEDIUM" ? "#fde68a" : "#bbf7d0"}`,
              color: riskLevel === "HIGH" ? "#991b1b" : riskLevel === "MEDIUM" ? "#92400e" : "#166534",
            }}
          >
            {riskLevel === "HIGH" && (
              <strong>
                HIGH RISK: High delivery failure probability flagged. Review SHAP reasons and assign an experienced area rider. (Order is not rejected; admin review permitted).
              </strong>
            )}
            {riskLevel === "MEDIUM" && (
              <strong>
                MEDIUM RISK: Moderate failure risk detected. Standard dispatch ranking applies with area familiarity weighting.
              </strong>
            )}
            {riskLevel === "LOW" && (
              <strong>
                LOW RISK: Delivery parameters are optimal. Order proceeds normally with recommended rider dispatch.
              </strong>
            )}
          </div>

          {/* Predicted Class & Reasons */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
            <div style={{ padding: "14px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
                Predicted Outcome Class
              </span>
              <div style={{ fontSize: "1.05rem", fontWeight: "700", color: predictedClass.includes("Failure") ? "#dc2626" : "#16a34a", marginTop: "4px" }}>
                {predictedClass}
              </div>
              <span style={{ fontSize: "0.8rem", color: "#64748b" }}>
                Threshold: P(Failure) {">"} 0.50 → Failure Likely
              </span>
            </div>

            <div style={{ padding: "14px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
                Top Contributing Factors (SHAP)
              </span>
              <ul style={{ margin: "6px 0 0 16px", fontSize: "0.85rem", color: "#334155", lineHeight: "1.5" }}>
                {reasonsList.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* 3. Dispatch Section (Rider Assignment) */}
        <div className="card-modern" style={{ padding: "24px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
            <div>
              <h2 style={{ fontSize: "1.15rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                Rider Dispatch & Assignment
              </h2>
              <span style={{ fontSize: "0.825rem", color: "#64748b" }}>
                Multi-Criteria Decision Ranking (Workload, Area Familiarity, Success Rate, Proximity)
              </span>
            </div>

            {rider && (
              <span className="badge-modern badge-status active">
                Assigned: {rider.name}
              </span>
            )}
          </div>

          {/* If already assigned */}
          {rider ? (
            <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                    {rider.name}
                  </h3>
                  <span style={{ fontSize: "0.85rem", color: "#64748b" }}>
                    Primary Zone: {rider.area || "Kathmandu Valley"} • Phone: {rider.phone || "—"}
                  </span>
                </div>

                <div style={{ display: "flex", gap: "16px" }}>
                  <div style={{ textAlign: "right" }}>
                    <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Current Load</span>
                    <div style={{ fontWeight: "700", color: "#0f172a" }}>{rider.current_order_count ?? 0} / {rider.max_orders_per_day ?? 20}</div>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Overall Success</span>
                    <div style={{ fontWeight: "700", color: "#16a34a" }}>{(Number(rider.overall_success_rate || 0.85) * 100).toFixed(1)}%</div>
                  </div>
                </div>
              </div>

              {isAssigned && (
                <div style={{ marginTop: "14px", borderTop: "1px solid #e2e8f0", paddingTop: "12px" }}>
                  <button
                    type="button"
                    disabled={actionLoading}
                    onClick={() => navigate(`/admin/dispatch?deliveryId=${id}`)}
                    className="btn-modern btn-modern-secondary btn-modern-sm"
                  >
                    Reassign to Another Rider
                  </button>
                </div>
              )}
            </div>
          ) : (
            /* Unassigned: Show Recommended Rider */
            <div>
              {candidatesLoading ? (
                <p style={{ color: "#64748b", padding: "16px 0" }}>Evaluating eligible riders...</p>
              ) : topRecommendedRider ? (
                <div>
                  {/* Highlighted Recommended Rider Card */}
                  <div
                    style={{
                      padding: "16px 20px",
                      background: "#eff6ff",
                      borderRadius: "10px",
                      border: "1px solid #bfdbfe",
                      marginBottom: "14px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "10px" }}>
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#1e40af", background: "#dbeafe", padding: "2px 8px", borderRadius: "4px" }}>
                            RECOMMENDED RIDER
                          </span>
                          <h3 style={{ fontSize: "1.15rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                            {topRecommendedRider.rider_name || topRecommendedRider.name || `Rider ${topRecommendedRider.rider_id}`}
                          </h3>
                        </div>
                        <span style={{ fontSize: "0.85rem", color: "#3b82f6", display: "block", marginTop: "4px" }}>
                          Composite Score: <strong>{Number(topRecommendedRider.score || 0.84).toFixed(2)}</strong> • Highest ranking for {riskLevel} risk in {order.area || "this area"}.
                        </span>
                      </div>

                      <button
                        type="button"
                        disabled={actionLoading}
                        onClick={() => handleAssignRider(topRecommendedRider.rider_id || topRecommendedRider.id)}
                        className="btn-modern btn-modern-primary"
                        style={{ padding: "8px 16px" }}
                      >
                        {actionLoading ? "Assigning..." : `Assign Recommended Rider (${topRecommendedRider.rider_name || topRecommendedRider.name || "Rider"})`}
                      </button>
                    </div>

                    {/* Metrics Grid */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: "10px", marginTop: "14px" }}>
                      <div style={{ background: "#ffffff", padding: "8px 12px", borderRadius: "6px", border: "1px solid #bfdbfe" }}>
                        <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Load</span>
                        <div style={{ fontWeight: "700", color: "#0f172a" }}>
                          {topRecommendedRider.details?.workload?.current_orders ?? topRecommendedRider.current_order_count ?? 0} / {topRecommendedRider.details?.workload?.capacity ?? topRecommendedRider.max_orders_per_day ?? 20}
                        </div>
                      </div>

                      <div style={{ background: "#ffffff", padding: "8px 12px", borderRadius: "6px", border: "1px solid #bfdbfe" }}>
                        <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Overall Success</span>
                        <div style={{ fontWeight: "700", color: "#16a34a" }}>
                          {(Number(topRecommendedRider.details?.overall_performance?.success_rate ?? topRecommendedRider.overall_success_rate ?? 0.85) * 100).toFixed(1)}%
                        </div>
                      </div>

                      <div style={{ background: "#ffffff", padding: "8px 12px", borderRadius: "6px", border: "1px solid #bfdbfe" }}>
                        <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Area Match</span>
                        <div style={{ fontWeight: "700", color: (topRecommendedRider.details?.area_match?.matched ?? topRecommendedRider.area_match) ? "#16a34a" : "#64748b" }}>
                          {(topRecommendedRider.details?.area_match?.matched ?? topRecommendedRider.area_match) ? "Yes" : "No"}
                        </div>
                      </div>

                      <div style={{ background: "#ffffff", padding: "8px 12px", borderRadius: "6px", border: "1px solid #bfdbfe" }}>
                        <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Assignment Score</span>
                        <div style={{ fontWeight: "700", color: "#2563eb" }}>{Number(topRecommendedRider.score || 0).toFixed(2)}</div>
                      </div>
                    </div>
                  </div>

                  {/* Secondary Action: View Other Riders Toggle */}
                  <div>
                    <button
                      type="button"
                      onClick={() => setShowOtherRiders(!showOtherRiders)}
                      style={{
                        background: "none",
                        border: "none",
                        color: "#2563eb",
                        fontSize: "0.85rem",
                        fontWeight: "600",
                        cursor: "pointer",
                        padding: 0,
                      }}
                    >
                      {showOtherRiders ? "▲ Hide Other Eligible Riders" : "▼ View Other Eligible Riders (Admin Override)"}
                    </button>

                    {showOtherRiders && (
                      <div style={{ marginTop: "12px", overflowX: "auto" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.85rem" }}>
                          <thead>
                            <tr style={{ borderBottom: "2px solid #e2e8f0", color: "#64748b", fontSize: "0.75rem", textTransform: "uppercase" }}>
                              <th style={{ padding: "8px" }}>Rider</th>
                              <th style={{ padding: "8px" }}>Load</th>
                              <th style={{ padding: "8px" }}>Success Rate</th>
                              <th style={{ padding: "8px" }}>Area Match</th>
                              <th style={{ padding: "8px" }}>Score</th>
                              <th style={{ padding: "8px", textAlign: "right" }}>Override Action</th>
                            </tr>
                          </thead>
                          <tbody>
                            {candidates.map((c, idx) => {
                              const cLoad = `${c.details?.workload?.current_orders ?? c.current_order_count ?? 0}/${c.details?.workload?.capacity ?? c.max_orders_per_day ?? 20}`;
                              const cSuccess = `${(Number(c.details?.overall_performance?.success_rate ?? c.overall_success_rate ?? 0.85) * 100).toFixed(1)}%`;
                              const cMatch = (c.details?.area_match?.matched ?? c.area_match) ? "Yes" : "No";

                              return (
                                <tr key={c.rider_id || c.id || idx} style={{ borderBottom: "1px solid #f1f5f9" }}>
                                  <td style={{ padding: "8px", fontWeight: "600", color: "#0f172a" }}>{c.rider_name || c.name}</td>
                                  <td style={{ padding: "8px" }}>{cLoad}</td>
                                  <td style={{ padding: "8px", color: "#16a34a", fontWeight: "600" }}>{cSuccess}</td>
                                  <td style={{ padding: "8px" }}>{cMatch}</td>
                                  <td style={{ padding: "8px", fontWeight: "700" }}>{Number(c.score || 0).toFixed(2)}</td>
                                  <td style={{ padding: "8px", textAlign: "right" }}>
                                    <button
                                      type="button"
                                      disabled={actionLoading}
                                      onClick={() => handleAssignRider(c.rider_id || c.id)}
                                      className="btn-modern btn-modern-secondary btn-modern-sm"
                                      style={{ padding: "3px 8px", fontSize: "0.75rem" }}
                                    >
                                      Assign
                                    </button>
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
              ) : (
                <p style={{ color: "#64748b", fontSize: "0.875rem" }}>No eligible riders currently active in the fleet.</p>
              )}
            </div>
          )}
        </div>

        {/* 4. Delivery Lifecycle & Controls */}
        <div className="card-modern" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "1.15rem", fontWeight: "700", color: "#0f172a", margin: "0 0 16px 0" }}>
            Delivery Lifecycle Operations
          </h2>

          <StatusTimeline status={delivery?.status} />

          {/* Operational Admin Action Buttons */}
          <div style={{ marginTop: "20px", borderTop: "1px solid #f1f5f9", paddingTop: "16px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", display: "block", marginBottom: "10px" }}>
              Operational Controls
            </span>

            <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
              {isAssigned && (
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={() => handleAction(() => startDelivery(id), "Start Delivery (Picked Up)")}
                  className="btn-modern btn-modern-primary"
                >
                  [ Start Delivery (Picked Up) ]
                </button>
              )}

              {isPickedUp && (
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={() => handleAction(() => markOutForDelivery(id), "Out for Delivery")}
                  className="btn-modern btn-modern-primary"
                >
                  [ Out for Delivery ]
                </button>
              )}

              {isOutForDelivery && (
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={() => handleAction(() => completeDelivery(id, 25), "Mark Delivered")}
                  className="btn-modern btn-modern-success"
                >
                  ✓ [ Mark Delivered ]
                </button>
              )}

              {(isPickedUp || isOutForDelivery) && (
                <>
                  <button
                    type="button"
                    disabled={actionLoading}
                    onClick={() => setShowFailModal(true)}
                    className="btn-modern btn-modern-danger"
                  >
                    ✕ [ Mark Failed ]
                  </button>

                  <button
                    type="button"
                    disabled={actionLoading}
                    onClick={() => handleFailSubmit(true)}
                    className="btn-modern btn-modern-secondary"
                  >
                    [ Mark Unreachable ]
                  </button>
                </>
              )}

              {isFailed && (
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={() => handleAction(() => reassignDelivery(id), "Reassign Delivery")}
                  className="btn-modern btn-modern-primary"
                >
                  ↻ [ Reassign Delivery ]
                </button>
              )}

              {!isDelivered && !isFailed && (
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={() => handleAction(() => cancelDelivery(id), "Cancel Order")}
                  className="btn-modern btn-modern-secondary"
                  style={{ color: "#dc2626" }}
                >
                  [ Cancel Order ]
                </button>
              )}

              {isDelivered && (
                <div style={{ color: "#16a34a", fontWeight: "700", fontSize: "0.95rem" }}>
                  ✓ Delivery Successfully Completed
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 5. Destination Map Panel */}
        <div className="card-modern" style={{ padding: "20px" }}>
          <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: "8px" }}>
            Delivery Location Map
          </span>
          <div style={{ height: "240px", borderRadius: "8px", overflow: "hidden", border: "1px solid #cbd5e1" }}>
            <MapContainer
              center={[coordinates.lat, coordinates.lng]}
              zoom={14}
              style={{ height: "100%", width: "100%" }}
              scrollWheelZoom={false}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              <Marker position={[coordinates.lat, coordinates.lng]} icon={markerIcon}>
                <Popup>
                  <strong>{order?.address || "Delivery Destination"}</strong>
                </Popup>
              </Marker>
            </MapContainer>
          </div>
        </div>

      </div>

      {/* Failure Reason Modal */}
      {showFailModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(15, 23, 42, 0.6)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 9999,
          }}
        >
          <div className="card-modern" style={{ width: "420px", maxWidth: "90vw", padding: "24px" }}>
            <h3 style={{ fontSize: "1.15rem", fontWeight: "700", color: "#dc2626", marginBottom: "10px" }}>
              Record Delivery Failure
            </h3>
            <p style={{ fontSize: "0.85rem", color: "#64748b", marginBottom: "14px" }}>
              Specify the reason why this delivery could not be fulfilled:
            </p>

            <div className="form-group" style={{ margin: 0 }}>
              <textarea
                className="form-control-modern"
                rows={3}
                value={failReason}
                onChange={(e) => setFailReason(e.target.value)}
                required
              />
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "16px" }}>
              <button
                type="button"
                onClick={() => setShowFailModal(false)}
                className="btn-modern btn-modern-secondary btn-modern-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => handleFailSubmit(false)}
                className="btn-modern btn-modern-danger btn-modern-sm"
              >
                Confirm Failure
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDeliveryLifecycle;
