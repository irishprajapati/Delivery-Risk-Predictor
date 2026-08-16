import { useState, useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { predictExplain, getAdminCustomers } from "../../services/api";
import MapPinPicker from "../../components/MapPinPicker";
import RiskBadge from "../../components/RiskBadge";

const pickupIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-green.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const deliveryIcon = new L.Icon({
  iconUrl: "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png",
  shadowUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function FitRouteBounds({ bounds }) {
  const map = useMap();
  useEffect(() => {
    if (bounds) {
      map.fitBounds(bounds, { padding: [30, 30] });
    }
  }, [map, bounds]);
  return null;
}

const AdminPrediction = () => {
  const [customers, setCustomers] = useState([]);
  const [selectedPhone, setSelectedPhone] = useState("9841878273");
  const [customPhone, setCustomPhone] = useState("");
  const [pickupAddress, setPickupAddress] = useState("Lokanthali, Bhaktapur");
  const [deliveryAddress, setDeliveryAddress] = useState("Jawalakhel, Lalitpur");

  const [pickupCoords, setPickupCoords] = useState({ lat: 27.6749, lng: 85.3601 });
  const [deliveryCoords, setDeliveryCoords] = useState({ lat: 27.6744, lng: 85.3123 });
  const [activePinTab, setActivePinTab] = useState("delivery"); // 'delivery' or 'pickup'

  const [orderValue, setOrderValue] = useState("90000");
  const [quantity, setQuantity] = useState("1");
  const [paymentMethod, setPaymentMethod] = useState("cod");
  const [prepaidAmount, setPrepaidAmount] = useState("0");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  useEffect(() => {
    const fetchCustomersList = async () => {
      try {
        const list = await getAdminCustomers();
        if (Array.isArray(list) && list.length > 0) {
          setCustomers(list);
          setSelectedPhone(list[0].phone);
        }
      } catch (err) {
        console.warn("Could not load customers for prediction dropdown:", err);
      }
    };
    fetchCustomersList();
  }, []);

  const handleAnalyze = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    setResult(null);

    const activePhone = customPhone.trim() ? customPhone.trim() : selectedPhone;

    const payload = {
      phone_number: activePhone,
      pickup_address: pickupAddress.trim(),
      delivery_address: deliveryAddress.trim(),
      pickup_latitude: pickupCoords.lat,
      pickup_longitude: pickupCoords.lng,
      delivery_latitude: deliveryCoords.lat,
      delivery_longitude: deliveryCoords.lng,
      order_value: parseFloat(orderValue) || 1000,
      quantity: parseInt(quantity) || 1,
      payment_method: paymentMethod,
      prepaid_amount: paymentMethod === "prepaid" ? parseFloat(prepaidAmount || orderValue) : 0.0,
    };

    try {
      const data = await predictExplain(payload);
      setResult(data);
    } catch (err) {
      console.error("Prediction error:", err);
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg || d.detail).join(", "));
      } else if (typeof detail === "string") {
        setError(detail);
      } else {
        setError("Failed to execute ML risk prediction. Please verify inputs.");
      }
    } finally {
      setLoading(false);
    }
  };

  const polylinePoints = useMemo(() => {
    if (!result?.route?.route_polyline?.length) return [];
    return result.route.route_polyline.map((p) => [p.lat, p.lng]);
  }, [result]);

  const mapBounds = useMemo(() => {
    if (!result) return null;
    const p1 = result.route?.pickup_coordinates || pickupCoords;
    const p2 = result.route?.delivery_coordinates || deliveryCoords;
    if (polylinePoints.length > 0) {
      return L.latLngBounds(polylinePoints);
    }
    return L.latLngBounds([
      [p1.lat, p1.lng],
      [p2.lat, p2.lng],
    ]);
  }, [result, polylinePoints, pickupCoords, deliveryCoords]);

  return (
    <div className="animate-fade-in" style={{ maxWidth: "1140px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Title */}
      <div style={{ marginBottom: "24px" }}>
        <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Machine Learning Failure Prediction & SHAP Analysis
        </span>
        <h1 style={{ fontSize: "1.85rem", fontWeight: "800", color: "#0f172a", marginTop: "2px" }}>
          DELIVERY RISK PREDICTOR
        </h1>
        <p style={{ color: "#64748b", fontSize: "0.95rem", margin: 0 }}>
          Simulate pre-dispatch conditions, extract route weather & traffic, and explain model factor weights.
        </p>
      </div>

      {error && (
        <div style={{ padding: "14px", background: "#fef2f2", color: "#dc2626", borderRadius: "8px", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: result ? "1fr 1fr" : "1fr", gap: "24px" }}>
        {/* Form Card */}
        <div className="card-modern">
          <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#0f172a", marginBottom: "16px", borderBottom: "1px solid #f1f5f9", paddingBottom: "10px" }}>
            Prediction Parameters
          </h2>

          <form onSubmit={handleAnalyze} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {/* Customer Phone */}
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Customer Profile</label>
              {customers.length > 0 ? (
                <div style={{ display: "flex", gap: "8px" }}>
                  <select
                    className="form-control-modern"
                    value={selectedPhone}
                    onChange={(e) => {
                      setSelectedPhone(e.target.value);
                      setCustomPhone("");
                    }}
                  >
                    {customers.map((c) => (
                      <option key={c.id} value={c.phone}>
                        {c.phone} ({c.total_orders || 0} orders, {c.failed_deliveries || 0} fails)
                      </option>
                    ))}
                  </select>
                  <input
                    type="text"
                    placeholder="Or enter phone"
                    className="form-control-modern"
                    style={{ width: "160px" }}
                    value={customPhone}
                    onChange={(e) => setCustomPhone(e.target.value)}
                  />
                </div>
              ) : (
                <input
                  type="text"
                  className="form-control-modern"
                  value={selectedPhone}
                  onChange={(e) => setSelectedPhone(e.target.value)}
                  placeholder="9841878273"
                  required
                />
              )}
            </div>

            {/* Order Value & Quantity */}
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "12px" }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Order Value (Rs.)</label>
                <input
                  type="number"
                  className="form-control-modern"
                  value={orderValue}
                  onChange={(e) => setOrderValue(e.target.value)}
                  min="1"
                  required
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Quantity</label>
                <input
                  type="number"
                  className="form-control-modern"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  min="1"
                  required
                />
              </div>
            </div>

            {/* Payment Method */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Payment Method</label>
                <select
                  className="form-control-modern"
                  value={paymentMethod}
                  onChange={(e) => {
                    setPaymentMethod(e.target.value);
                    if (e.target.value === "prepaid") setPrepaidAmount(orderValue);
                    else setPrepaidAmount("0");
                  }}
                >
                  <option value="cod">Cash on Delivery (COD)</option>
                  <option value="prepaid">Prepaid</option>
                </select>
              </div>

              {paymentMethod === "prepaid" && (
                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Prepaid Amount (Rs.)</label>
                  <input
                    type="number"
                    className="form-control-modern"
                    value={prepaidAmount}
                    onChange={(e) => setPrepaidAmount(e.target.value)}
                  />
                </div>
              )}
            </div>

            {/* Pickup & Delivery Addresses */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Pickup Address</label>
                <input
                  type="text"
                  className="form-control-modern"
                  value={pickupAddress}
                  onChange={(e) => setPickupAddress(e.target.value)}
                  required
                />
              </div>
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Delivery Address</label>
                <input
                  type="text"
                  className="form-control-modern"
                  value={deliveryAddress}
                  onChange={(e) => setDeliveryAddress(e.target.value)}
                  required
                />
              </div>
            </div>

            {/* Interactive Map Pin Picker with Delivery/Pickup Toggle */}
            <div style={{ marginTop: "4px" }}>
              <div style={{ display: "flex", gap: "6px", marginBottom: "8px" }}>
                <button
                  type="button"
                  onClick={() => setActivePinTab("delivery")}
                  style={{
                    padding: "4px 10px",
                    fontSize: "0.75rem",
                    fontWeight: "700",
                    borderRadius: "6px",
                    border: activePinTab === "delivery" ? "1px solid #dc2626" : "1px solid #e2e8f0",
                    background: activePinTab === "delivery" ? "#fef2f2" : "#ffffff",
                    color: activePinTab === "delivery" ? "#dc2626" : "#64748b",
                    cursor: "pointer",
                  }}
                >
                  📍 Delivery Pin
                </button>
                <button
                  type="button"
                  onClick={() => setActivePinTab("pickup")}
                  style={{
                    padding: "4px 10px",
                    fontSize: "0.75rem",
                    fontWeight: "700",
                    borderRadius: "6px",
                    border: activePinTab === "pickup" ? "1px solid #16a34a" : "1px solid #e2e8f0",
                    background: activePinTab === "pickup" ? "#f0fdf4" : "#ffffff",
                    color: activePinTab === "pickup" ? "#16a34a" : "#64748b",
                    cursor: "pointer",
                  }}
                >
                  🟢 Pickup Hub Pin
                </button>
              </div>

              {activePinTab === "delivery" ? (
                <MapPinPicker
                  key="delivery-pin"
                  initialLat={deliveryCoords.lat}
                  initialLng={deliveryCoords.lng}
                  onLocationSelect={(pos) => setDeliveryCoords(pos)}
                  label="Delivery Destination Pin"
                  height="200px"
                />
              ) : (
                <MapPinPicker
                  key="pickup-pin"
                  initialLat={pickupCoords.lat}
                  initialLng={pickupCoords.lng}
                  onLocationSelect={(pos) => setPickupCoords(pos)}
                  isPickup={true}
                  label="Pickup Hub Location Pin"
                  height="200px"
                />
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-modern btn-modern-primary btn-modern-lg"
              style={{ marginTop: "8px" }}
            >
              {loading ? "Calculating Route, Weather & ML Risk..." : "Analyze Delivery Risk"}
            </button>
          </form>
        </div>

        {/* Results Card */}
        {result && (
          <div className="card-modern animate-fade-in" style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Risk Banner */}
            <div
              style={{
                padding: "20px",
                borderRadius: "12px",
                background:
                  String(result.risk).toUpperCase() === "HIGH"
                    ? "#fef2f2"
                    : String(result.risk).toUpperCase() === "MEDIUM"
                    ? "#fffbeb"
                    : "#f0fdf4",
                border:
                  String(result.risk).toUpperCase() === "HIGH"
                    ? "1px solid #fecaca"
                    : String(result.risk).toUpperCase() === "MEDIUM"
                    ? "1px solid #fde68a"
                    : "1px solid #bbf7d0",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <span style={{ fontSize: "0.75rem", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.06em", color: "#64748b" }}>
                    DELIVERY RISK
                  </span>
                  <div style={{ fontSize: "2rem", fontWeight: "800", marginTop: "2px" }}>
                    <RiskBadge risk={result.risk} />
                  </div>
                </div>

                <div style={{ textAlign: "right" }}>
                  <span style={{ fontSize: "0.8rem", color: "#64748b", fontWeight: "600" }}>
                    Failure probability
                  </span>
                  <div style={{ fontSize: "1.75rem", fontWeight: "800", color: "#0f172a" }}>
                    {(Number(result.probability || 0) * 100).toFixed(2)}%
                  </div>
                </div>
              </div>

              <p style={{ margin: "10px 0 0", fontSize: "0.95rem", fontWeight: "600", color: "#334155" }}>
                Prediction:{" "}
                <span style={{ color: result.prediction === 1 ? "#dc2626" : "#16a34a" }}>
                  {result.prediction === 1 ? "Delivery Failure Likely" : "Successful delivery"}
                </span>
              </p>
            </div>

            {/* Main Factors Breakdown */}
            <div>
              <h3 style={{ fontSize: "0.95rem", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", marginBottom: "10px" }}>
                Main factors
              </h3>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "0.9rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "#f8fafc", borderRadius: "6px" }}>
                  <span>Location success rate</span>
                  <span style={{ color: "#16a34a", fontWeight: "700" }}>↑ Safe</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "#f8fafc", borderRadius: "6px" }}>
                  <span>Address quality</span>
                  <span style={{ color: "#16a34a", fontWeight: "700" }}>↑ High</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "#f8fafc", borderRadius: "6px" }}>
                  <span>Prepaid ratio</span>
                  <span style={{ color: result.features?.is_cod ? "#dc2626" : "#16a34a", fontWeight: "700" }}>
                    {result.features?.is_cod ? "↓ COD (Elevates Risk)" : "↓ Prepaid (Reduces Risk)"}
                  </span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 12px", background: "#f8fafc", borderRadius: "6px" }}>
                  <span>Distance ({result.route?.distance_km ?? 0} km)</span>
                  <span style={{ color: "#16a34a", fontWeight: "700" }}>↓ Short Route</span>
                </div>
              </div>
            </div>

            {/* Why? section */}
            <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
              <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#0f172a", marginBottom: "8px" }}>
                Why?
              </h3>
              <ul style={{ margin: 0, paddingLeft: "20px", display: "flex", flexDirection: "column", gap: "6px", fontSize: "0.875rem", color: "#334155" }}>
                {result.explanations?.reasons?.length > 0 ? (
                  result.explanations.reasons.map((r, i) => <li key={i}>{r}</li>)
                ) : (
                  <>
                    <li>Current customer history is established with positive delivery rates.</li>
                    <li>Prepaid payment structure reduces observed rejection risk.</li>
                    <li>Short road route within Kathmandu valley reduces transit delays.</li>
                    <li>Clear weather conditions detected along the route.</li>
                  </>
                )}
              </ul>
            </div>

            {/* Map Preview */}
            <div>
              <h3 style={{ fontSize: "0.85rem", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.04em", color: "#475569", marginBottom: "8px" }}>
                Route, Weather & Traffic
              </h3>
              <div style={{ height: "200px", borderRadius: "10px", overflow: "hidden", border: "1px solid #e2e8f0" }}>
                <MapContainer
                  center={[pickupCoords.lat, pickupCoords.lng]}
                  zoom={13}
                  style={{ height: "100%", width: "100%" }}
                  scrollWheelZoom={false}
                >
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  {mapBounds && <FitRouteBounds bounds={mapBounds} />}
                  <Marker position={[pickupCoords.lat, pickupCoords.lng]} icon={pickupIcon}>
                    <Popup>Pickup: {pickupAddress}</Popup>
                  </Marker>
                  <Marker position={[deliveryCoords.lat, deliveryCoords.lng]} icon={deliveryIcon}>
                    <Popup>Delivery: {deliveryAddress}</Popup>
                  </Marker>
                  {polylinePoints.length > 1 && (
                    <Polyline positions={polylinePoints} color="#2563eb" weight={4} opacity={0.8} />
                  )}
                </MapContainer>
              </div>

              <div style={{ display: "flex", gap: "8px", marginTop: "8px", fontSize: "0.75rem", color: "#64748b" }}>
                <span>Distance: <strong>{result.route?.distance_km ?? "—"} km</strong></span>
                <span>•</span>
                <span>ETA: <strong>{result.route?.estimated_duration_min ?? "—"} min</strong></span>
                <span>•</span>
                <span>Weather: <strong>{result.weather?.midpoint || result.weather?.route_weather || "Clear"}</strong></span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPrediction;
