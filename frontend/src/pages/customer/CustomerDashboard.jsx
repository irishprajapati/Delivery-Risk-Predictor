import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getCustomerOrders, getCustomerProfile, getErrorMessage } from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import StatusTimeline from "../../components/StatusTimeline";

const CustomerDashboard = () => {
  const navigate = useNavigate();
  const { phone } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [customerPhone, setCustomerPhone] = useState(phone || "");

  useEffect(() => {
    let isMounted = true;

    const fetchCustomerData = async () => {
      try {
        setLoading(true);
        setError("");

        const [ordersRes, profileRes] = await Promise.allSettled([
          getCustomerOrders(),
          getCustomerProfile(),
        ]);

        if (!isMounted) return;

        if (ordersRes.status === "fulfilled") {
          setOrders(ordersRes.value || []);
        } else {
          const err = ordersRes.reason;
          if (err?.response?.status === 401 || err?.response?.status === 403) {
            setError("Session expired or unauthorized. Please log in again as a customer.");
            return;
          }
          console.warn("Orders fetch error:", err);
        }

        if (profileRes.status === "fulfilled" && profileRes.value?.phone) {
          setCustomerPhone(profileRes.value.phone);
        }
      } catch (err) {
        if (isMounted) {
          setError(getErrorMessage(err, "Failed to load customer dashboard"));
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchCustomerData();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="animate-fade-in" style={{ maxWidth: "860px", margin: "0 auto", paddingBottom: "40px" }}>
      {/* Top Welcome Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "16px",
          marginBottom: "24px",
          paddingBottom: "16px",
          borderBottom: "1px solid #e2e8f0",
        }}
      >
        <div>
          <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            Customer Portal
          </span>
          <h1 style={{ fontSize: "1.65rem", fontWeight: "700", color: "#0f172a", margin: "2px 0 0" }}>
            Welcome, {customerPhone || phone || "Customer"}
          </h1>
        </div>

        <Link
          to="/customer/order"
          className="btn-modern btn-modern-primary"
          style={{ textDecoration: "none", padding: "10px 18px" }}
        >
          [ Place New Order ]
        </Link>
      </div>

      {/* Main Content Area */}
      <div>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
          <h2 style={{ fontSize: "1.15rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
            Recent Orders
          </h2>
          {orders.length > 0 && (
            <span style={{ fontSize: "0.825rem", color: "#64748b" }}>
              {orders.length} order{orders.length > 1 ? "s" : ""} recorded
            </span>
          )}
        </div>

        {loading ? (
          <div className="card-modern" style={{ textAlign: "center", padding: "48px 24px" }}>
            <p style={{ color: "#64748b", fontSize: "0.9rem" }}>Loading your orders...</p>
          </div>
        ) : error ? (
          <div className="card-modern" style={{ borderColor: "#fecaca", backgroundColor: "#fef2f2", padding: "20px" }}>
            <p style={{ color: "#dc2626", margin: "0 0 12px 0" }}>{error}</p>
            <Link to="/login" className="btn-modern btn-modern-primary btn-modern-sm">
              Log in again
            </Link>
          </div>
        ) : orders.length === 0 ? (
          /* Empty State */
          <div className="card-modern" style={{ textAlign: "center", padding: "48px 24px" }}>
            <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#0f172a", marginBottom: "6px" }}>
              No orders placed yet
            </h3>
            <p style={{ color: "#64748b", fontSize: "0.875rem", maxWidth: "360px", margin: "0 auto 18px" }}>
              You haven't placed any delivery requests. Select an item and location to submit your first order.
            </p>
            <Link to="/customer/order" className="btn-modern btn-modern-primary btn-modern-sm">
              Place Your First Order
            </Link>
          </div>
        ) : (
          /* Orders List */
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {orders.map((order) => {
              const formattedPrice = `Rs. ${Number(order.total_price || 0).toLocaleString()}`;
              const orderDate = order.created_at
                ? new Date(order.created_at).toLocaleDateString("en-US", {
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })
                : "Recent";

              return (
                <div
                  key={order.order_id || order.id}
                  className="card-modern card-modern-hover"
                  style={{
                    padding: "20px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "14px",
                    cursor: "pointer",
                  }}
                  onClick={() => navigate(`/customer/orders/${order.order_id || order.id}`)}
                >
                  {/* Order Card Header */}
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      flexWrap: "wrap",
                      gap: "8px",
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{ fontWeight: "700", fontSize: "1.1rem", color: "#0f172a" }}>
                          Order #{order.order_id || order.id}
                        </span>
                        <span style={{ fontSize: "0.8rem", color: "#64748b" }}>• {orderDate}</span>
                      </div>
                      <div style={{ fontSize: "0.95rem", fontWeight: "600", color: "#334155", marginTop: "2px" }}>
                        {order.item_name || "Item"} (Qty: {order.quantity || 1})
                      </div>
                    </div>

                    <div style={{ textAlign: "right" }}>
                      <span style={{ fontSize: "1.15rem", fontWeight: "800", color: "#0f172a" }}>
                        {formattedPrice}
                      </span>
                      <span style={{ display: "block", fontSize: "0.75rem", color: "#64748b" }}>
                        {order.is_cod ? "Cash on Delivery" : "Prepaid"}
                      </span>
                    </div>
                  </div>

                  {/* Delivery Address */}
                  <div style={{ fontSize: "0.875rem", color: "#475569" }}>
                    Destination: <strong>{order.address || "Kathmandu Valley"}</strong>
                  </div>

                  {/* Linear Status Timeline */}
                  <div style={{ borderTop: "1px solid #f1f5f9", paddingTop: "12px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                      <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
                        Delivery Lifecycle Status
                      </span>
                      <span className="badge-modern badge-status active" style={{ fontSize: "0.75rem" }}>
                        {String(order.delivery_status || order.status || "placed").replace(/_/g, " ")}
                      </span>
                    </div>
                    <StatusTimeline status={order.delivery_status || order.status} />
                  </div>

                  {/* Card Bottom Link */}
                  <div style={{ textAlign: "right" }}>
                    <span style={{ fontSize: "0.8rem", color: "#2563eb", fontWeight: "600" }}>
                      View Order & Live Tracking →
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
