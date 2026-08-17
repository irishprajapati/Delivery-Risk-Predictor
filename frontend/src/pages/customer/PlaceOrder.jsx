import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { getItems, placeOrder, getErrorMessage } from "../../services/api";
import MapPinPicker from "../../components/MapPinPicker";

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
          setItems([]);
          setError("No items are currently available in the catalog.");
        }
      } catch (err) {
        console.error("Could not load items from API:", err);
        setItems([]);
        setError(getErrorMessage(err, "Failed to load product catalog."));
      } finally {
        setItemsLoading(false);
      }
    };

    fetchAvailableItems();
  }, []);

  const selectedItem = items.find((i) => String(i.id) === String(selectedItemId)) || items[0] || null;
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
      console.error("Place order failed:", err);
      setError(getErrorMessage(err, "Failed to place order. Please check your inputs and try again."));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: "860px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Title */}
      <div style={{ marginBottom: "20px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: "1.65rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
            Place New Order
          </h1>
          <p style={{ fontSize: "0.875rem", color: "#64748b", margin: "4px 0 0" }}>
            Select your item, payment type, and delivery location pin on the map
          </p>
        </div>

        <Link to="/customer/dashboard" style={{ fontSize: "0.85rem", color: "#2563eb", fontWeight: "600" }}>
          ← Back to Dashboard
        </Link>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "#fef2f2", color: "#dc2626", borderRadius: "8px", border: "1px solid #fecaca", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} style={{ display: "grid", gridTemplateColumns: "1fr", gap: "20px" }}>
        {/* Step 1: Item & Quantity */}
        <div className="card-modern" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#0f172a", marginBottom: "16px" }}>
            1. Select Item & Quantity
          </h2>

          <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "16px" }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Item</label>
              {itemsLoading ? (
                <div style={{ padding: "10px", color: "#64748b" }}>Loading item inventory...</div>
              ) : items.length === 0 ? (
                <div style={{ padding: "10px", color: "#dc2626" }}>No items currently available in catalog.</div>
              ) : (
                <select
                  className="form-control-modern"
                  value={selectedItemId}
                  onChange={(e) => {
                    setSelectedItemId(e.target.value);
                    const itm = items.find((i) => String(i.id) === e.target.value);
                    if (itm && paymentMethod === "prepaid") {
                      setPrepaidAmount(Number(itm.price || 0) * Math.max(1, Number(quantity)));
                    }
                  }}
                  required
                >
                  {items.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name} — Rs. {Number(item.price).toLocaleString()}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div className="form-group" style={{ margin: 0 }}>
              <label className="form-label">Quantity</label>
              <input
                type="number"
                min="1"
                max="50"
                className="form-control-modern"
                value={quantity}
                onChange={(e) => {
                  const qty = Math.max(1, Number(e.target.value || 1));
                  setQuantity(qty);
                  if (paymentMethod === "prepaid") {
                    setPrepaidAmount(unitPrice * qty);
                  }
                }}
                required
              />
            </div>
          </div>
        </div>

        {/* Step 2: Payment Method */}
        <div className="card-modern" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#0f172a", marginBottom: "16px" }}>
            2. Payment Method
          </h2>

          <div style={{ display: "flex", gap: "20px", marginBottom: "14px" }}>
            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                cursor: "pointer",
                padding: "10px 16px",
                border: paymentMethod === "cod" ? "1px solid #2563eb" : "1px solid #e2e8f0",
                borderRadius: "8px",
                background: paymentMethod === "cod" ? "#eff6ff" : "#ffffff",
                fontWeight: "600",
                fontSize: "0.9rem",
              }}
            >
              <input
                type="radio"
                name="payment_method"
                value="cod"
                checked={paymentMethod === "cod"}
                onChange={() => handlePaymentChange("cod")}
              />
              Cash on Delivery (COD)
            </label>

            <label
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                cursor: "pointer",
                padding: "10px 16px",
                border: paymentMethod === "prepaid" ? "1px solid #2563eb" : "1px solid #e2e8f0",
                borderRadius: "8px",
                background: paymentMethod === "prepaid" ? "#eff6ff" : "#ffffff",
                fontWeight: "600",
                fontSize: "0.9rem",
              }}
            >
              <input
                type="radio"
                name="payment_method"
                value="prepaid"
                checked={paymentMethod === "prepaid"}
                onChange={() => handlePaymentChange("prepaid")}
              />
              Prepaid
            </label>
          </div>

          {paymentMethod === "prepaid" && (
            <div className="form-group" style={{ maxWidth: "280px", margin: 0 }}>
              <label className="form-label">Prepaid Amount (Rs.)</label>
              <input
                type="number"
                min="0"
                max={totalPrice}
                className="form-control-modern"
                value={prepaidAmount}
                onChange={(e) => setPrepaidAmount(Number(e.target.value))}
                required
              />
              <span style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "2px", display: "block" }}>
                Full or partial prepayment
              </span>
            </div>
          )}
        </div>

        {/* Step 3: Location Pin Picker */}
        <div className="card-modern" style={{ padding: "24px" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#0f172a", marginBottom: "14px" }}>
            3. Delivery Address & Map Location Pin
          </h2>

          <div className="form-group" style={{ marginBottom: "16px" }}>
            <label className="form-label">Delivery Address / Landmark</label>
            <input
              type="text"
              className="form-control-modern"
              placeholder="e.g. Jawalakhel, near Zoo gate, Lalitpur"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              required
            />
          </div>

          <MapPinPicker
            initialLat={coordinates.lat}
            initialLng={coordinates.lng}
            onLocationSelect={handleLocationSelect}
            label="Drag the marker or click on map to set your location pin:"
            height="260px"
          />
        </div>

        {/* Order Summary & Submit */}
        <div className="card-modern" style={{ padding: "24px", background: "#f8fafc", border: "1px solid #cbd5e1" }}>
          <h2 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#0f172a", marginBottom: "14px" }}>
            Order Summary
          </h2>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px", fontSize: "0.9rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "#64748b" }}>Selected Item:</span>
              <strong style={{ color: "#0f172a" }}>{selectedItem?.name || "Item"}</strong>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "#64748b" }}>Unit Price:</span>
              <span>Rs. {unitPrice.toLocaleString()}</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "#64748b" }}>Quantity:</span>
              <span>{quantity}</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "#64748b" }}>Payment Mode:</span>
              <span style={{ fontWeight: "600", color: "#0f172a" }}>
                {paymentMethod === "cod" ? "Cash on Delivery" : "Prepaid"}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "#64748b" }}>Delivery Address:</span>
              <span style={{ textAlign: "right", maxWidth: "300px", fontWeight: "500", color: "#0f172a" }}>
                {address || "Not specified"}
              </span>
            </div>

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                borderTop: "2px solid #e2e8f0",
                paddingTop: "12px",
                marginTop: "6px",
                fontSize: "1.15rem",
              }}
            >
              <strong style={{ color: "#0f172a" }}>Total Payable:</strong>
              <strong style={{ color: "#2563eb" }}>Rs. {totalPrice.toLocaleString()}</strong>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || itemsLoading}
            className="btn-modern btn-modern-primary btn-modern-lg"
            style={{ width: "100%", marginTop: "20px", padding: "12px" }}
          >
            {loading ? "Submitting Order..." : `[ Confirm & Place Order — Rs. ${totalPrice.toLocaleString()} ]`}
          </button>
        </div>
      </form>
    </div>
  );
};

export default PlaceOrder;
