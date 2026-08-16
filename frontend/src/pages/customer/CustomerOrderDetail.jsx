import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { getCustomerOrder } from "../../services/api";
import StatusTimeline from "../../components/StatusTimeline";

const markerIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const getDeliveryStatusMessage = (status, riderName) => {
  const s = String(status || "").toLowerCase();
  switch (s) {
    case "placed":
    case "unassigned":
      return "Waiting for rider assignment. Our dispatch system is finding the best eligible rider for your area.";
    case "assigned":
      return riderName
        ? `Rider ${riderName} has been assigned to your order.`
        : "A rider has been assigned and is heading to the pickup hub.";
    case "picked_up":
    case "started":
      return riderName
        ? `Rider ${riderName} has picked up your package from the hub.`
        : "Package has been picked up from the hub.";
    case "out_for_delivery":
      return riderName
        ? `Rider ${riderName} is on the way to your delivery address!`
        : "Package is currently out for delivery.";
    case "delivered":
      return "Package has been successfully delivered! Thank you for ordering.";
    case "failed":
    case "unreachable":
      return "Delivery attempt could not be completed. Operations will reassign shortly.";
    case "cancelled":
      return "This order has been cancelled.";
    default:
      return "Order is being processed.";
  }
};

const CustomerOrderDetail = () => {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchOrder = async () => {
    try {
      setLoading(true);
      const data = await getCustomerOrder(id);
      setOrder(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Could not load order details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrder();
  }, [id]);

  if (loading) {
    return (
      <div className="card-modern" style={{ textAlign: "center", padding: "48px 24px" }}>
        <p style={{ color: "#64748b" }}>Loading order details...</p>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="card-modern" style={{ borderColor: "#fecaca", backgroundColor: "#fef2f2" }}>
        <p style={{ color: "#dc2626", marginBottom: "12px" }}>{error || "Order not found"}</p>
        <Link to="/customer/dashboard" className="btn-modern btn-modern-secondary">
          ← Back to Dashboard
        </Link>
      </div>
    );
  }

  const effectiveStatus = order.delivery_status || order.order_status || "placed";
  const formattedPrice = `Rs. ${Number(order.total_price || 0).toLocaleString()}`;
  const statusMessage = getDeliveryStatusMessage(effectiveStatus, order.rider_name);
  const hasCoordinates = order.latitude && order.longitude;

  return (
    <div className="animate-fade-in" style={{ maxWidth: "800px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Navigation */}
      <div style={{ marginBottom: "20px" }}>
        <Link to="/customer/dashboard" style={{ fontSize: "0.85rem", color: "#2563eb", fontWeight: "600", textDecoration: "none" }}>
          ← Back to My Orders
        </Link>
      </div>

      {/* Main Order Card */}
      <div className="card-modern">
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
            paddingBottom: "18px",
            borderBottom: "1px solid #e2e8f0",
          }}
        >
          <div>
            <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              Order Confirmation
            </span>
            <h1 style={{ fontSize: "1.75rem", fontWeight: "800", color: "#0f172a", margin: "2px 0 0" }}>
              Order #{order.id}
            </h1>
          </div>

          <button
            type="button"
            onClick={fetchOrder}
            className="btn-modern btn-modern-secondary btn-modern-sm"
          >
            ↻ Refresh Status
          </button>
        </div>

        {/* Status Lifecycle Stepper */}
        <div style={{ margin: "24px 0 16px" }}>
          <StatusTimeline status={effectiveStatus} />
        </div>

        {/* Status explanation alert */}
        <div
          style={{
            padding: "14px 18px",
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
            borderRadius: "10px",
            color: "#1e40af",
            fontSize: "0.95rem",
            lineHeight: "1.45",
            marginBottom: "24px",
            display: "flex",
            gap: "10px",
            alignItems: "flex-start",
          }}
        >
          <span style={{ fontSize: "1.2rem" }}>ℹ️</span>
          <div>
            <strong style={{ display: "block", marginBottom: "2px" }}>Delivery Status</strong>
            {statusMessage}
          </div>
        </div>

        {/* Order Details Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginBottom: "24px" }}>
          <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              Delivery Address
            </span>
            <p style={{ fontSize: "1rem", fontWeight: "600", color: "#0f172a", margin: "6px 0 0" }}>
              {order.address}
            </p>
          </div>

          <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              Order Value
            </span>
            <p style={{ fontSize: "1.2rem", fontWeight: "800", color: "#0f172a", margin: "4px 0 0" }}>
              {formattedPrice}
            </p>
            <span style={{ fontSize: "0.8rem", color: "#64748b" }}>
              Item: {order.item_name} {order.quantity > 1 ? `(Qty: ${order.quantity})` : ""}
            </span>
          </div>

          <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              Payment Method
            </span>
            <p style={{ fontSize: "1rem", fontWeight: "600", color: "#0f172a", margin: "6px 0 0" }}>
              {order.is_cod ? "Cash on Delivery" : "Prepaid"}
            </p>
          </div>

          <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
              Assigned Rider
            </span>
            <p style={{ fontSize: "1rem", fontWeight: "600", color: "#0f172a", margin: "6px 0 0" }}>
              {order.rider_name ? `🚴 ${order.rider_name}` : "Pending Assignment"}
            </p>
          </div>
        </div>

        {/* Map Preview if coordinates present */}
        {hasCoordinates && (
          <div>
            <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: "8px" }}>
              Delivery Pin Location
            </span>
            <div style={{ height: "240px", borderRadius: "10px", overflow: "hidden", border: "1px solid #cbd5e1" }}>
              <MapContainer
                center={[order.latitude, order.longitude]}
                zoom={14}
                style={{ height: "100%", width: "100%" }}
                scrollWheelZoom={false}
              >
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <Marker position={[order.latitude, order.longitude]} icon={markerIcon}>
                  <Popup>
                    <strong>Delivery Location</strong>
                    <br />
                    {order.address}
                  </Popup>
                </Marker>
              </MapContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CustomerOrderDetail;
