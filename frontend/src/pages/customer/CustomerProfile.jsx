import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getCustomerProfile, getErrorMessage } from "../../services/api";

const CustomerProfile = () => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchProfile = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getCustomerProfile();
      setProfile(data);
    } catch (err) {
      setError(getErrorMessage(err, "Failed to load customer profile. Please log in again."));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  if (loading) {
    return (
      <div className="card-modern" style={{ textAlign: "center", padding: "48px 24px", maxWidth: "600px", margin: "0 auto" }}>
        <p style={{ color: "#64748b" }}>Loading profile information...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="card-modern" style={{ maxWidth: "600px", margin: "0 auto", borderColor: "#fecaca", backgroundColor: "#fef2f2" }}>
        <p style={{ color: "#dc2626", marginBottom: "12px" }}>{error}</p>
        <Link to="/login" className="btn-modern btn-modern-primary btn-modern-sm">
          Go to Login
        </Link>
      </div>
    );
  }

  const successRate =
    profile?.total_orders > 0
      ? ((profile.successful_deliveries / profile.total_orders) * 100).toFixed(1) + "%"
      : "100%";

  return (
    <div className="animate-fade-in" style={{ maxWidth: "680px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Header */}
      <div style={{ marginBottom: "20px" }}>
        <h1 style={{ fontSize: "1.65rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
          Customer Profile
        </h1>
        <p style={{ fontSize: "0.875rem", color: "#64748b", margin: "4px 0 0" }}>
          Registered account details and historical delivery statistics
        </p>
      </div>

      <div className="card-modern" style={{ padding: "28px" }}>
        {/* Phone & Status */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #f1f5f9", paddingBottom: "20px", marginBottom: "20px" }}>
          <div>
            <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
              Registered Mobile
            </span>
            <div style={{ fontSize: "1.4rem", fontWeight: "700", color: "#0f172a", marginTop: "2px" }}>
              {profile?.phone}
            </div>
            <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Customer ID: #{profile?.id}</span>
          </div>

          <span
            className="badge-modern badge-status success"
            style={{ fontSize: "0.8rem", padding: "4px 10px" }}
          >
            Verified Account
          </span>
        </div>

        {/* Delivery Statistics */}
        <h2 style={{ fontSize: "1rem", fontWeight: "700", color: "#0f172a", marginBottom: "14px" }}>
          Delivery Reliability History
        </h2>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px", marginBottom: "24px" }}>
          <div style={{ padding: "14px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "600", color: "#64748b" }}>Total Orders</span>
            <div style={{ fontSize: "1.5rem", fontWeight: "700", color: "#0f172a", marginTop: "2px" }}>
              {profile?.total_orders ?? 0}
            </div>
          </div>

          <div style={{ padding: "14px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "600", color: "#64748b" }}>Successful</span>
            <div style={{ fontSize: "1.5rem", fontWeight: "700", color: "#16a34a", marginTop: "2px" }}>
              {profile?.successful_deliveries ?? 0}
            </div>
          </div>

          <div style={{ padding: "14px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "600", color: "#64748b" }}>Success Rate</span>
            <div style={{ fontSize: "1.5rem", fontWeight: "700", color: "#2563eb", marginTop: "2px" }}>
              {successRate}
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div style={{ display: "flex", gap: "10px", borderTop: "1px solid #f1f5f9", paddingTop: "20px" }}>
          <Link to="/customer/order" className="btn-modern btn-modern-primary">
            + Place New Order
          </Link>
          <Link to="/customer/dashboard" className="btn-modern btn-modern-secondary">
            View My Orders
          </Link>
        </div>
      </div>
    </div>
  );
};

export default CustomerProfile;
