import { useState, useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { predictExplain, getAdminCustomers, getErrorMessage } from "../../services/api";
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
      setError(getErrorMessage(err, "Failed to execute ML risk prediction. Please verify inputs."));
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
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "1.65rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
          Delivery Failure Prediction Engine
        </h1>
        <p style={{ color: "#64748b", fontSize: "0.875rem", margin: "3px 0 0" }}>
          Machine learning failure probability calculation, SHAP feature importance analysis, and route factors
        </p>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "#fef2f2", color: "#dc2626", borderRadius: "8px", border: "1px solid #fecaca", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: result ? "1fr 1fr" : "1fr", gap: "20px" }}>
        {/* Form Card */}
        <div className="card-modern" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#0f172a", marginBottom: "16px", borderBottom: "1px solid #f1f5f9", paddingBottom: "10px" }}>
            Input Parameters
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
                    fontWeight: "600",
                    borderRadius: "6px",
                    border: activePinTab === "delivery" ? "1px solid #dc2626" : "1px solid #e2e8f0",
                    background: activePinTab === "delivery" ? "#fef2f2" : "#ffffff",
                    color: activePinTab === "delivery" ? "#dc2626" : "#64748b",
                    cursor: "pointer",
                  }}
                >
                  Delivery Destination Pin
                </button>
                <button
                  type="button"
                  onClick={() => setActivePinTab("pickup")}
                  style={{
                    padding: "4px 10px",
                    fontSize: "0.75rem",
                    fontWeight: "600",
                    borderRadius: "6px",
                    border: activePinTab === "pickup" ? "1px solid #16a34a" : "1px solid #e2e8f0",
                    background: activePinTab === "pickup" ? "#f0fdf4" : "#ffffff",
                    color: activePinTab === "pickup" ? "#16a34a" : "#64748b",
                    cursor: "pointer",
                  }}
                >
                  Pickup Hub Pin
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
              style={{ marginTop: "6px" }}
            >
              {loading ? "Evaluating ML Model..." : "Run Delivery Failure Prediction"}
            </button>
          </form>
        </div>

        {/* Results Panel */}
        {result && (
          <div className="card-modern animate-fade-in" style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "18px" }}>
            {/* Risk Banner */}
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                borderBottom: "1px solid #f1f5f9",
                paddingBottom: "14px",
              }}
            >
              <div>
                <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
                  Delivery Failure Risk
                </span>
                <div style={{ marginTop: "4px" }}>
                  <RiskBadge risk={result.risk} size="large" />
                </div>
              </div>

              <div style={{ textAlign: "right" }}>
                <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
                  Failure Probability
                </span>
                <div style={{ fontSize: "1.75rem", fontWeight: "800", color: "#0f172a" }}>
                  {(result.probability * 100).toFixed(1)}%
                </div>
              </div>
            </div>

            {/* Verdict */}
            <div style={{ padding: "12px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
                Predicted Outcome
              </span>
              <div style={{ fontSize: "1.05rem", fontWeight: "700", color: result.prediction === 1 ? "#dc2626" : "#16a34a", marginTop: "2px" }}>
                {result.prediction === 1 ? "Delivery Failure Likely (P > 0.50)" : "Successful Delivery Expected (P ≤ 0.50)"}
              </div>
            </div>

            {/* Top SHAP Contributors */}
            {(() => {
              const shapFactors = result.explanations?.shap || result.explanation?.factors || result.explanation?.shap || [];
              const reasonsList = result.explanations?.reasons || result.explanation?.reasons || [];

              return (
                <>
                  {shapFactors.length > 0 && (
                    <div>
                      <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", display: "block", marginBottom: "8px" }}>
                        Top SHAP Feature Contributors
                      </span>
                      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                        {shapFactors.map((factor, idx) => {
                          const isRiskIncrease =
                            factor.direction === "increases_failure_risk" ||
                            factor.impact === "increases_risk" ||
                            factor.shap_value > 0;
                          return (
                            <div
                              key={idx}
                              style={{
                                display: "flex",
                                justifyContent: "space-between",
                                alignItems: "center",
                                padding: "8px 12px",
                                borderRadius: "6px",
                                border: "1px solid #e2e8f0",
                                backgroundColor: "#f8fafc",
                                fontSize: "0.85rem",
                              }}
                            >
                              <span style={{ fontWeight: "600", color: "#334155" }}>
                                {String(factor.feature || "").replace(/_/g, " ")}:{" "}
                                {typeof factor.value === "number" ? factor.value.toFixed(2) : factor.value}
                              </span>
                              <span style={{ fontWeight: "700", color: isRiskIncrease ? "#dc2626" : "#16a34a" }}>
                                {isRiskIncrease ? "↑ Increases Failure Risk" : "↓ Reduces Failure Risk"}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Human Readable Explanation Reasons */}
                  {reasonsList.length > 0 && (
                    <div>
                      <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>
                        Explanation Reasons
                      </span>
                      <ul style={{ margin: "0 0 0 18px", fontSize: "0.85rem", color: "#475569", lineHeight: "1.5" }}>
                        {reasonsList.map((r, i) => (
                          <li key={i}>{r}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              );
            })()}

            {/* Route & Polyline Map */}
            {polylinePoints.length > 0 && (
              <div>
                <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", display: "block", marginBottom: "6px" }}>
                  Route & Telemetry Preview ({result.route?.estimated_distance_km || "—"} km, ~{result.route?.estimated_duration_min || "—"} min)
                </span>
                <div style={{ height: "200px", borderRadius: "8px", overflow: "hidden", border: "1px solid #cbd5e1" }}>
                  <MapContainer bounds={mapBounds} style={{ height: "100%", width: "100%" }} scrollWheelZoom={false}>
                    <TileLayer
                      attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                      url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <FitRouteBounds bounds={mapBounds} />
                    <Marker position={[pickupCoords.lat, pickupCoords.lng]} icon={pickupIcon}>
                      <Popup>Pickup Hub</Popup>
                    </Marker>
                    <Marker position={[deliveryCoords.lat, deliveryCoords.lng]} icon={deliveryIcon}>
                      <Popup>Delivery Destination</Popup>
                    </Marker>
                    <Polyline positions={polylinePoints} color="#2563eb" weight={4} opacity={0.8} />
                  </MapContainer>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPrediction;
