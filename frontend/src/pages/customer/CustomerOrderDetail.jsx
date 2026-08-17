import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { getCustomerOrder, getErrorMessage } from "../../services/api";
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
        ? `Rider ${riderName} is currently out for delivery to your location.`
        : "Package is currently out for delivery.";
    case "delivered":
      return "Package has been successfully delivered.";
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
      setError("");
      const data = await getCustomerOrder(id);
      setOrder(data);
    } catch (err) {
      setError(getErrorMessage(err, "Could not load order details."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrder();
  }, [id]);

  if (loading) {
    return (
      <div className="card-modern" style={{ textAlign: "center", padding: "48px 24px", maxWidth: "800px", margin: "0 auto" }}>
        <p style={{ color: "#64748b" }}>Loading order details...</p>
      </div>
    );
  }

  if (error || !order) {
    return (
      <div className="card-modern" style={{ maxWidth: "800px", margin: "0 auto", borderColor: "#fecaca", backgroundColor: "#fef2f2" }}>
        <p style={{ color: "#dc2626", marginBottom: "12px" }}>{error || "Order not found"}</p>
        <Link to="/customer/dashboard" className="btn-modern btn-modern-secondary btn-modern-sm">
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
      <div style={{ marginBottom: "16px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Link to="/customer/dashboard" style={{ fontSize: "0.85rem", color: "#2563eb", fontWeight: "600", textDecoration: "none" }}>
          ← Back to My Orders
        </Link>
        <button
          type="button"
          onClick={fetchOrder}
          className="btn-modern btn-modern-secondary btn-modern-sm"
        >
          ↻ Refresh Status
        </button>
      </div>

      {/* Main Order Card */}
      <div className="card-modern" style={{ display: "flex", flexDirection: "column", gap: "20px", padding: "24px" }}>
        {/* Order Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            flexWrap: "wrap",
            gap: "12px",
            borderBottom: "1px solid #f1f5f9",
            paddingBottom: "16px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h1 style={{ fontSize: "1.5rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                Order #{order.order_id || id}
              </h1>
              <span className="badge-modern badge-status active">
                {String(effectiveStatus).replace(/_/g, " ")}
              </span>
            </div>
            <span style={{ color: "#64748b", fontSize: "0.85rem" }}>
              Placed: {order.created_at ? new Date(order.created_at).toLocaleString() : "Recently"}
            </span>
          </div>

          <div style={{ textAlign: "right" }}>
            <span style={{ fontSize: "1.4rem", fontWeight: "800", color: "#0f172a" }}>
              {formattedPrice}
            </span>
            <span style={{ display: "block", fontSize: "0.8rem", color: "#64748b" }}>
              {order.is_cod ? "Cash on Delivery" : `Prepaid (Rs. ${Number(order.prepaid_amount || 0).toLocaleString()})`}
            </span>
          </div>
        </div>

        {/* Live Status Message Box */}
        <div
          style={{
            padding: "14px 16px",
            backgroundColor: "#f8fafc",
            border: "1px solid #e2e8f0",
            borderRadius: "8px",
            fontSize: "0.9rem",
            color: "#334155",
          }}
        >
          <strong style={{ color: "#0f172a", display: "block", marginBottom: "3px" }}>
            Delivery Update:
          </strong>
          {statusMessage}
        </div>

        {/* 5-Step Visual Lifecycle Timeline */}
        <div>
          <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: "8px" }}>
            Order Progress
          </span>
          <StatusTimeline status={effectiveStatus} />
        </div>

        {/* Order & Rider Details Grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
          <div style={{ padding: "14px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
              Ordered Items
            </span>
            <div style={{ fontSize: "1rem", fontWeight: "700", color: "#0f172a", marginTop: "4px" }}>
              {order.item_name || "Item"}
            </div>
            <div style={{ fontSize: "0.85rem", color: "#64748b" }}>
              Quantity: {order.quantity || 1}
            </div>
          </div>

          <div style={{ padding: "14px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
              Delivery Destination
            </span>
            <div style={{ fontSize: "0.95rem", fontWeight: "600", color: "#0f172a", marginTop: "4px" }}>
              {order.address || "Address"}
            </div>
            <div style={{ fontSize: "0.85rem", color: "#64748b" }}>
              Area: {order.area || "Kathmandu"}
            </div>
          </div>
        </div>

        {/* Destination Map */}
        {hasCoordinates && (
          <div>
            <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em", display: "block", marginBottom: "8px" }}>
              Delivery Map Pin
            </span>
            <div style={{ height: "220px", borderRadius: "8px", overflow: "hidden", border: "1px solid #cbd5e1" }}>
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
                    <strong>{order.address}</strong>
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
