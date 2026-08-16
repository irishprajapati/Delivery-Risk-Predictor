import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { getItems, placeOrder } from "../../services/api";
import MapPinPicker from "../../components/MapPinPicker";

const DEFAULT_ITEMS = [
  { id: 1, name: "Laptop", price: 90000, category: "computers" },
  { id: 2, name: "Smartphone", price: 45000, category: "mobile_phones" },
  { id: 3, name: "Smart Watch", price: 15000, category: "watches" },
  { id: 4, name: "Headphones", price: 8500, category: "gaming_consoles" },
  { id: 5, name: "Gaming Console", price: 65000, category: "gaming_consoles" },
];

const PlaceOrder = () => {
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [selectedItemId, setSelectedItemId] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [paymentMethod, setPaymentMethod] = useState("cod"); // 'cod' or 'prepaid'
  const [prepaidAmount, setPrepaidAmount] = useState(0);
  const [address, setAddress] = useState("Jawalakhel, Lalitpur");
  const [coordinates, setCoordinates] = useState({ lat: 27.6744, lng: 85.3123 });

  const [loading, setLoading] = useState(false);
  const [itemsLoading, setItemsLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchAvailableItems = async () => {
      try {
        setItemsLoading(true);
        const data = await getItems();
        if (Array.isArray(data) && data.length > 0) {
          setItems(data);
          setSelectedItemId(String(data[0].id));
        } else {
          setItems(DEFAULT_ITEMS);
          setSelectedItemId(String(DEFAULT_ITEMS[0].id));
        }
      } catch (err) {
        console.warn("Could not load items from API, using fallback defaults:", err);
        setItems(DEFAULT_ITEMS);
        setSelectedItemId(String(DEFAULT_ITEMS[0].id));
      } finally {
        setItemsLoading(false);
      }
    };

    fetchAvailableItems();
  }, []);

  const selectedItem = items.find((i) => String(i.id) === String(selectedItemId)) || items[0] || DEFAULT_ITEMS[0];
  const unitPrice = selectedItem ? Number(selectedItem.price || 0) : 0;
  const totalPrice = unitPrice * Math.max(1, Number(quantity || 1));

  const handlePaymentChange = (method) => {
    setPaymentMethod(method);
    if (method === "prepaid") {
      setPrepaidAmount(totalPrice);
    } else {
      setPrepaidAmount(0);
    }
  };

  const handleLocationSelect = (pos) => {
    setCoordinates(pos);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!selectedItem) {
      setError("Please select an item to order.");
      return;
    }

    if (!address.trim()) {
      setError("Please provide a delivery address.");
      return;
    }

    setLoading(true);

    const payload = {
      item_id: Number(selectedItem.id),
      quantity: Math.max(1, Number(quantity)),
      payment_method: paymentMethod,
      prepaid_amount: paymentMethod === "prepaid" ? Number(prepaidAmount || totalPrice) : 0.0,
      address: address.trim(),
      latitude: coordinates.lat,
      longitude: coordinates.lng,
    };

    try {
      const res = await placeOrder(payload);
      if (res && (res.order_id || res.id)) {
        const orderId = res.order_id || res.id;
        navigate(`/customer/orders/${orderId}`);
      } else {
        navigate("/customer/dashboard");
      }
    } catch (err) {
      console.error("Order error:", err);
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail.map((d) => d.msg || d.detail).join(", "));
      } else if (typeof detail === "string") {
        setError(detail);
      } else {
        setError("Failed to place order. Please check all fields and try again.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: "840px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <Link to="/customer/dashboard" style={{ fontSize: "0.85rem", color: "#2563eb", fontWeight: "600", textDecoration: "none" }}>
          ← Back to Dashboard
        </Link>
        <h1 style={{ fontSize: "1.75rem", fontWeight: "800", color: "#0f172a", marginTop: "8px" }}>
          Place New Order
        </h1>
        <p style={{ color: "#64748b", fontSize: "0.95rem", margin: 0 }}>
          Select an item and set your delivery pin on the map.
        </p>
      </div>

      {error && (
        <div
          style={{
            padding: "14px 18px",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "8px",
            color: "#dc2626",
            marginBottom: "20px",
            fontSize: "0.9rem",
            fontWeight: "500",
          }}
        >
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
          {/* Left Column: Inputs */}
          <div className="card-modern" style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
            <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#1e293b", borderBottom: "1px solid #f1f5f9", paddingBottom: "10px" }}>
              Order Information
            </h2>

            {/* Item Selection */}
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Item</label>
              <select
                className="form-control-modern"
                value={selectedItemId}
                onChange={(e) => setSelectedItemId(e.target.value)}
                disabled={itemsLoading}
                style={{ fontSize: "0.95rem", fontWeight: "500" }}
              >
                {items.map((it) => (
                  <option key={it.id} value={it.id}>
                    {it.name} (Rs. {Number(it.price).toLocaleString()})
                  </option>
                ))}
              </select>
            </div>

            {/* Quantity */}
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Quantity</label>
              <input
                type="number"
                min="1"
                max="99"
                className="form-control-modern"
                value={quantity}
                onChange={(e) => {
                  const val = Math.max(1, parseInt(e.target.value) || 1);
                  setQuantity(val);
                  if (paymentMethod === "prepaid") {
                    setPrepaidAmount(unitPrice * val);
                  }
                }}
                required
              />
            </div>

            {/* Payment Method */}
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Payment</label>
              <div style={{ display: "flex", flexDirection: "column", gap: "8px", marginTop: "2px" }}>
                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    padding: "10px 14px",
                    borderRadius: "8px",
                    border: paymentMethod === "cod" ? "2px solid #2563eb" : "1px solid #e2e8f0",
                    backgroundColor: paymentMethod === "cod" ? "#eff6ff" : "#ffffff",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="radio"
                    name="payment_method"
                    value="cod"
                    checked={paymentMethod === "cod"}
                    onChange={() => handlePaymentChange("cod")}
                  />
                  <span style={{ fontSize: "0.925rem", fontWeight: "600", color: "#1e293b" }}>
                    Cash on Delivery
                  </span>
                </label>

                <label
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    padding: "10px 14px",
                    borderRadius: "8px",
                    border: paymentMethod === "prepaid" ? "2px solid #2563eb" : "1px solid #e2e8f0",
                    backgroundColor: paymentMethod === "prepaid" ? "#eff6ff" : "#ffffff",
                    cursor: "pointer",
                  }}
                >
                  <input
                    type="radio"
                    name="payment_method"
                    value="prepaid"
                    checked={paymentMethod === "prepaid"}
                    onChange={() => handlePaymentChange("prepaid")}
                  />
                  <span style={{ fontSize: "0.925rem", fontWeight: "600", color: "#1e293b" }}>
                    Prepaid
                  </span>
                </label>
              </div>
            </div>

            {/* Prepaid Amount Input (if prepaid selected) */}
            {paymentMethod === "prepaid" && (
              <div className="form-group" style={{ margin: 0 }}>
                <label className="form-label">Prepaid Amount (Rs.)</label>
                <input
                  type="number"
                  className="form-control-modern"
                  value={prepaidAmount}
                  onChange={(e) => setPrepaidAmount(Number(e.target.value))}
                  min="1"
                  max={totalPrice}
                  required
                />
              </div>
            )}

            {/* Delivery Address */}
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Delivery Address</label>
              <input
                type="text"
                className="form-control-modern"
                placeholder="e.g. Jawalakhel, Lalitpur"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Right Column: Map & Order Summary */}
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Map Pin Picker Card */}
            <div className="card-modern">
              <MapPinPicker
                initialLat={coordinates.lat}
                initialLng={coordinates.lng}
                onLocationSelect={handleLocationSelect}
                label="Delivery Map Location"
                height="230px"
              />
            </div>

            {/* Order Summary Card */}
            <div
              className="card-modern"
              style={{
                backgroundColor: "#f8fafc",
                borderColor: "#cbd5e1",
              }}
            >
              <h2 style={{ fontSize: "1.05rem", fontWeight: "700", color: "#0f172a", marginBottom: "14px" }}>
                Order Summary
              </h2>

              <div style={{ display: "flex", flexDirection: "column", gap: "10px", fontSize: "0.925rem" }}>
                <div style={{ display: "flex", justifyContent: "space-between", color: "#334155" }}>
                  <span>{selectedItem?.name || "Item"}</span>
                  <span style={{ fontWeight: "600" }}>Rs. {unitPrice.toLocaleString()}</span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", color: "#334155" }}>
                  <span>Quantity</span>
                  <span style={{ fontWeight: "600" }}>{quantity}</span>
                </div>

                <div style={{ display: "flex", justifyContent: "space-between", color: "#334155" }}>
                  <span>Payment</span>
                  <span style={{ fontWeight: "600" }}>{paymentMethod === "cod" ? "COD" : "Prepaid"}</span>
                </div>

                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    paddingTop: "12px",
                    borderTop: "2px solid #e2e8f0",
                    fontSize: "1.15rem",
                    fontWeight: "800",
                    color: "#0f172a",
                  }}
                >
                  <span>Total</span>
                  <span>Rs. {totalPrice.toLocaleString()}</span>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn-modern btn-modern-primary btn-modern-lg"
                style={{ width: "100%", marginTop: "20px" }}
              >
                {loading ? "Placing Order..." : "Place Order"}
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
};

export default PlaceOrder;
