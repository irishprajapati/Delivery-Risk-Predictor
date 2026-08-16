import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getCustomerOrders, getCustomerProfile } from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import StatusTimeline from "../../components/StatusTimeline";

const CustomerDashboard = () => {
  const navigate = useNavigate();
  const { phone } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [customerPhone, setCustomerPhone] = useState(phone || "9841878273");

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        setLoading(true);
        const [ordersData, profileData] = await Promise.allSettled([
          getCustomerOrders(),
          getCustomerProfile(),
        ]);

        if (ordersData.status === "fulfilled") {
          setOrders(ordersData.value);
        } else {
          console.warn("Could not fetch orders:", ordersData.reason);
        }

        if (profileData.status === "fulfilled" && profileData.value.phone) {
          setCustomerPhone(profileData.value.phone);
        }
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    };

    fetchOrders();
  }, []);

  return (
    <div className="animate-fade-in" style={{ maxWidth: "880px", margin: "0 auto", paddingBottom: "40px" }}>
      {/* Top Welcome Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "16px",
          marginBottom: "28px",
          paddingBottom: "20px",
          borderBottom: "1px solid #e2e8f0",
        }}
      >
        <div>
          <span style={{ fontSize: "0.85rem", fontWeight: "600", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            Customer Portal
          </span>
          <h1 style={{ fontSize: "1.75rem", fontWeight: "800", color: "#0f172a", marginTop: "2px" }}>
            Welcome, {customerPhone}
          </h1>
        </div>

        <Link
          to="/customer/order"
          className="btn-modern btn-modern-primary btn-modern-lg"
          style={{ textDecoration: "none" }}
        >
          <span style={{ fontSize: "1.1rem" }}>+</span> Place New Order
        </Link>
      </div>

      {/* Main Content Area */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <h2 style={{ fontSize: "1.25rem", fontWeight: "700", color: "#1e293b" }}>
            Recent Orders
          </h2>
          {orders.length > 0 && (
            <span style={{ fontSize: "0.85rem", color: "#64748b" }}>
              {orders.length} order{orders.length > 1 ? "s" : ""} placed
            </span>
          )}
        </div>

        {loading ? (
          <div className="card-modern" style={{ textAlign: "center", padding: "48px 24px" }}>
            <p style={{ color: "#64748b", fontSize: "0.95rem" }}>Loading your orders...</p>
          </div>
        ) : error ? (
          <div className="card-modern" style={{ borderColor: "#fecaca", backgroundColor: "#fef2f2" }}>
            <p style={{ color: "#dc2626", margin: 0 }}>{error}</p>
          </div>
        ) : orders.length === 0 ? (
          /* Empty State */
          <div className="card-modern" style={{ textAlign: "center", padding: "54px 24px" }}>
            <div style={{ fontSize: "2.5rem", marginBottom: "12px" }}>📦</div>
            <h3 style={{ fontSize: "1.2rem", fontWeight: "700", color: "#1e293b", marginBottom: "6px" }}>
              No orders placed yet
            </h3>
            <p style={{ color: "#64748b", maxWidth: "380px", margin: "0 auto 20px" }}>
              Ready to send a delivery? Pick an item and select your destination on the map.
            </p>
            <Link
              to="/customer/order"
              className="btn-modern btn-modern-primary"
              style={{ textDecoration: "none" }}
            >
              Place Your First Order
            </Link>
          </div>
        ) : (
          /* Order Cards List */
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {orders.map((order) => {
              const formattedPrice = `Rs. ${Number(order.total_price || 0).toLocaleString()}`;
              const isDelivered = String(order.delivery_status || "").toLowerCase() === "delivered";

              return (
                <div
                  key={order.id}
                  className="card-modern card-modern-hover"
                  style={{ cursor: "pointer" }}
                  onClick={() => navigate(`/customer/orders/${order.id}`)}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      flexWrap: "wrap",
                      gap: "12px",
                      marginBottom: "12px",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                        <span style={{ fontSize: "1.1rem", fontWeight: "800", color: "#0f172a" }}>
                          Order #{order.id}
                        </span>
                        <span
                          className={`badge-modern ${
                            isDelivered ? "badge-status success" : "badge-status active"
                          }`}
                        >
                          {String(order.delivery_status || order.order_status || "Placed").replace(/_/g, " ")}
                        </span>
                      </div>
                      <p style={{ fontSize: "1rem", fontWeight: "600", color: "#334155", margin: 0 }}>
                        {order.item_name || "Delivery Item"}
                        {order.quantity > 1 ? ` (Qty: ${order.quantity})` : ""}
                      </p>
                    </div>

                    <div style={{ textAlign: "right" }}>
                      <span style={{ fontSize: "1.25rem", fontWeight: "800", color: "#0f172a" }}>
                        {formattedPrice}
                      </span>
                      <p style={{ fontSize: "0.8rem", color: "#64748b", margin: 0 }}>
                        {order.is_cod ? "Cash on Delivery" : "Prepaid"}
                      </p>
                    </div>
                  </div>

                  {/* Address */}
                  <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#475569", fontSize: "0.9rem", marginBottom: "14px" }}>
                    <span style={{ color: "#2563eb" }}>📍</span>
                    <span>{order.address}</span>
                  </div>

                  {/* Status Timeline */}
                  <div
                    style={{
                      paddingTop: "12px",
                      borderTop: "1px solid #f1f5f9",
                    }}
                  >
                    <StatusTimeline
                      status={order.delivery_status || order.order_status}
                      compact={true}
                    />
                  </div>

                  <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "12px" }}>
                    <span style={{ fontSize: "0.85rem", fontWeight: "600", color: "#2563eb" }}>
                      Track Order Details →
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default CustomerDashboard;
