import { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  getDeliverySummary,
  startDelivery,
  markOutForDelivery,
  completeDelivery,
  failDelivery,
  reassignDelivery,
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
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Failure modal state
  const [showFailModal, setShowFailModal] = useState(false);
  const [failReason, setFailReason] = useState("Customer unreachable after repeated attempts");

  const fetchDelivery = async () => {
    try {
      setLoading(true);
      const data = await getDeliverySummary(id);
      setDelivery(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not load delivery lifecycle");
    } finally {
      setLoading(false);
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
      setError(err.response?.data?.detail || `Failed to execute ${name}`);
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
      setError(err.response?.data?.detail || "Failed to record failure");
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="card-modern" style={{ textAlign: "center", padding: "48px 24px" }}>
        <p style={{ color: "#64748b" }}>Loading delivery lifecycle...</p>
      </div>
    );
  }

  if (error && !delivery) {
    return (
      <div className="card-modern" style={{ borderColor: "#fecaca", backgroundColor: "#fef2f2" }}>
        <p style={{ color: "#dc2626", marginBottom: "12px" }}>{error}</p>
        <Link to="/admin/dashboard" className="btn-modern btn-modern-secondary">
          ← Back to Operations
        </Link>
      </div>
    );
  }

  const order = delivery?.order || {};
  const rider = delivery?.rider || null;
  const location = delivery?.location || {};
  const currentStatus = String(delivery?.status || "unassigned").toLowerCase();

  const isAssigned = currentStatus === "assigned";
  const isPickedUp = currentStatus === "picked_up" || currentStatus === "started";
  const isOutForDelivery = currentStatus === "out_for_delivery";
  const isDelivered = currentStatus === "delivered";
  const isFailed = currentStatus === "failed" || currentStatus === "unreachable";

  const coordinates = {
    lat: location?.latitude || order?.latitude || 27.6744,
    lng: location?.longitude || order?.longitude || 85.3123,
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: "1000px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Title & Navigation */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <Link to="/admin/dashboard" style={{ fontSize: "0.85rem", color: "#2563eb", fontWeight: "600" }}>
          ← Back to Operations Dashboard
        </Link>
        <button
          type="button"
          onClick={fetchDelivery}
          className="btn-modern btn-modern-secondary btn-modern-sm"
        >
          ↻ Refresh State
        </button>
      </div>

      {error && (
        <div style={{ padding: "14px", background: "#fef2f2", color: "#dc2626", borderRadius: "8px", marginBottom: "16px" }}>
          {error}
        </div>
      )}

      {successMsg && (
        <div style={{ padding: "14px", background: "#f0fdf4", color: "#16a34a", borderRadius: "8px", marginBottom: "16px", fontWeight: "600" }}>
          ✓ {successMsg}
        </div>
      )}

      {/* Main Delivery Card */}
      <div className="card-modern" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {/* Header Bar */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
            borderBottom: "1px solid #e2e8f0",
            paddingBottom: "16px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h1 style={{ fontSize: "1.75rem", fontWeight: "800", color: "#0f172a", margin: 0 }}>
                DELIVERY #{delivery?.delivery_id || id}
              </h1>
              <span className="badge-modern badge-status active">
                {String(delivery?.status || "unassigned").replace(/_/g, " ")}
              </span>
            </div>
            <p style={{ color: "#64748b", margin: "4px 0 0", fontSize: "0.95rem" }}>
              Order #{delivery?.order_id} • Created {delivery?.created_at ? new Date(delivery.created_at).toLocaleString() : "Recently"}
            </p>
          </div>

          <div style={{ display: "flex", gap: "14px", alignItems: "center" }}>
            <div style={{ textAlign: "right" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
                Risk Level
              </span>
              <div>
                <RiskBadge risk={delivery?.risk_level || "MEDIUM"} />
              </div>
            </div>
          </div>
        </div>

        {/* Lifecycle Stepper */}
        <div>
          <h3 style={{ fontSize: "0.9rem", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "#475569", marginBottom: "4px" }}>
            Lifecycle Progression
          </h3>
          <StatusTimeline status={delivery?.status} />
        </div>

        {/* Customer & Location Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
          {/* Customer info */}
          <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <h3 style={{ fontSize: "0.8rem", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "#64748b", marginBottom: "8px" }}>
              Customer Details
            </h3>
            <div style={{ fontSize: "1.1rem", fontWeight: "700", color: "#0f172a", marginBottom: "4px" }}>
              📱 {order?.customer_phone || "9841878273"}
            </div>
            <div style={{ fontSize: "0.85rem", color: "#475569" }}>
              Item: <strong>{order?.item_name || "Laptop"}</strong> (Qty: {order?.quantity || 1})
            </div>
            <div style={{ fontSize: "0.85rem", color: "#475569" }}>
              Value: <strong>Rs. {Number(order?.total_price || 90000).toLocaleString()}</strong> ({order?.is_cod ? "COD" : "Prepaid"})
            </div>
          </div>

          {/* Location info */}
          <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <h3 style={{ fontSize: "0.8rem", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "#64748b", marginBottom: "8px" }}>
              Delivery Destination
            </h3>
            <div style={{ fontSize: "1.05rem", fontWeight: "600", color: "#0f172a", marginBottom: "4px" }}>
              📍 {order?.address || "Jawalakhel, Lalitpur"}
            </div>
            <div style={{ fontSize: "0.85rem", color: "#475569" }}>
              Area: <strong>{order?.area || "Lalitpur"}</strong>
            </div>
            {delivery?.distance_km && (
              <div style={{ fontSize: "0.85rem", color: "#475569" }}>
                Distance: <strong>{delivery.distance_km} km</strong> (~{Math.round(delivery.estimated_duration || 15)} min)
              </div>
            )}
          </div>
        </div>

        {/* Assigned Rider Information Card */}
        <div style={{ padding: "20px", background: "#f8fafc", borderRadius: "12px", border: "1px solid #e2e8f0" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
            <div>
              <h3 style={{ fontSize: "0.85rem", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "#64748b", margin: 0 }}>
                Rider Information
              </h3>
              <div style={{ fontSize: "1.25rem", fontWeight: "800", color: "#0f172a", marginTop: "2px" }}>
                {rider ? `🚴 ${rider.name}` : "No Rider Assigned"}
              </div>
            </div>

            {rider ? (
              <Link to={`/admin/riders/${rider.id}`} style={{ fontSize: "0.85rem", color: "#2563eb", fontWeight: "600" }}>
                View Rider Profile →
              </Link>
            ) : (
              <button
                type="button"
                onClick={() => navigate(`/admin/dispatch?deliveryId=${delivery?.delivery_id || id}`)}
                className="btn-modern btn-modern-primary btn-modern-sm"
              >
                Dispatch Rider Now →
              </button>
            )}
          </div>

          {rider && (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px", marginTop: "12px" }}>
              <div style={{ background: "#ffffff", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <span style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: "600" }}>Current Load</span>
                <div style={{ fontSize: "1.2rem", fontWeight: "800", color: "#0f172a" }}>
                  {rider.current_order_count ?? 6} / {rider.max_orders_per_day ?? 20}
                </div>
              </div>

              <div style={{ background: "#ffffff", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <span style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: "600" }}>Overall Success</span>
                <div style={{ fontSize: "1.2rem", fontWeight: "800", color: "#16a34a" }}>
                  {(Number(rider.overall_success_rate || 0.905) * 100).toFixed(1)}%
                </div>
              </div>

              <div style={{ background: "#ffffff", padding: "12px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                <span style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: "600" }}>Area Success</span>
                <div style={{ fontSize: "1.2rem", fontWeight: "800", color: "#2563eb" }}>
                  {(Number(rider.area_performance?.success_rate || 0.87) * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Interactive Map Preview */}
        <div>
          <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: "8px" }}>
            Destination Map
          </span>
          <div style={{ height: "220px", borderRadius: "10px", overflow: "hidden", border: "1px solid #cbd5e1" }}>
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
                  <strong>{order?.address || "Delivery Location"}</strong>
                </Popup>
              </Marker>
            </MapContainer>
          </div>
        </div>

        {/* Operational Admin Lifecycle Controls */}
        <div style={{ borderTop: "2px solid #e2e8f0", paddingTop: "20px" }}>
          <h3 style={{ fontSize: "0.95rem", fontWeight: "800", color: "#0f172a", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "12px" }}>
            OPERATIONAL LIFECYCLE CONTROLS
          </h3>

          <div style={{ display: "flex", gap: "10px", flexWrap: "wrap" }}>
            {isAssigned && (
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => handleAction(() => startDelivery(id), "Start Delivery")}
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

            {isDelivered && (
              <div style={{ color: "#16a34a", fontWeight: "700", fontSize: "0.95rem", display: "flex", alignItems: "center", gap: "6px" }}>
                ✓ Terminal State: Delivered successfully
              </div>
            )}
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
          <div className="card-modern" style={{ width: "420px", maxWidth: "90vw" }}>
            <h3 style={{ fontSize: "1.15rem", fontWeight: "800", color: "#dc2626", marginBottom: "12px" }}>
              Record Delivery Failure
            </h3>
            <p style={{ fontSize: "0.875rem", color: "#64748b", marginBottom: "16px" }}>
              Specify the reason this delivery attempt could not be fulfilled:
            </p>

            <div className="form-group">
              <label className="form-label">Failure Reason</label>
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
