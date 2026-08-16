import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { login } from "../services/api";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const navigate = useNavigate();
  const { login: authLogin } = useAuth();

  const [role, setRole] = useState("customer");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRoleChange = (newRole) => {
    setRole(newRole);
    setIdentifier(newRole === "customer" ? "9841878273" : "admin");
    setError("");
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const data = await login(role, identifier, password);

      const phoneVal = role === "customer" ? identifier : "";
      authLogin(data.access_token, role, phoneVal);

      if (role === "admin") {
        navigate("/admin/dashboard", { replace: true });
      } else {
        navigate("/customer/dashboard", { replace: true });
      }
    } catch (err) {
      console.error("Login error:", err);
      if (err.response) {
        setError(err.response.data?.detail || "Invalid credentials. Please check your details.");
      } else {
        setError("Unable to connect to the backend server. Please verify FastAPI is running.");
      }
    } finally {
      setLoading(false);
    }
  };

  const isAdmin = role === "admin";

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)",
        padding: "20px",
      }}
    >
      <div
        className="card-modern animate-fade-in"
        style={{
          width: "100%",
          maxWidth: "420px",
          padding: "36px 32px",
          boxShadow: "0 20px 25px -5px rgba(15, 23, 42, 0.1), 0 8px 10px -6px rgba(15, 23, 42, 0.1)",
        }}
      >
        {/* Brand */}
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div style={{ fontSize: "2rem", marginBottom: "6px" }}>⚡</div>
          <h1 style={{ fontSize: "1.6rem", fontWeight: "800", color: "#0f172a" }}>
            LogiRisk Platform
          </h1>
          <p style={{ color: "#64748b", fontSize: "0.875rem", margin: "4px 0 0" }}>
            Delivery Risk Prediction & Operational Dispatch
          </p>
        </div>

        {/* Role Toggle */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "4px",
            background: "#f1f5f9",
            padding: "4px",
            borderRadius: "10px",
            marginBottom: "24px",
          }}
        >
          <button
            type="button"
            onClick={() => handleRoleChange("customer")}
            style={{
              padding: "8px 12px",
              fontSize: "0.875rem",
              fontWeight: "700",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
              background: !isAdmin ? "#ffffff" : "transparent",
              color: !isAdmin ? "#0f172a" : "#64748b",
              boxShadow: !isAdmin ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
              transition: "all 0.15s ease",
            }}
          >
            Customer
          </button>

          <button
            type="button"
            onClick={() => handleRoleChange("admin")}
            style={{
              padding: "8px 12px",
              fontSize: "0.875rem",
              fontWeight: "700",
              border: "none",
              borderRadius: "8px",
              cursor: "pointer",
              background: isAdmin ? "#ffffff" : "transparent",
              color: isAdmin ? "#0f172a" : "#64748b",
              boxShadow: isAdmin ? "0 1px 3px rgba(0,0,0,0.1)" : "none",
              transition: "all 0.15s ease",
            }}
          >
            Admin Operations
          </button>
        </div>

        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">
              {isAdmin ? "Admin Username" : "Customer Phone Number"}
            </label>
            <input
              type={isAdmin ? "text" : "tel"}
              className="form-control-modern"
              placeholder={isAdmin ? "e.g. admin" : "e.g. 9841878273"}
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
            />
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-control-modern"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && (
            <div
              style={{
                padding: "10px 14px",
                background: "#fef2f2",
                border: "1px solid #fecaca",
                borderRadius: "8px",
                color: "#dc2626",
                fontSize: "0.85rem",
                textAlign: "center",
              }}
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-modern btn-modern-primary btn-modern-lg"
            style={{ width: "100%", marginTop: "8px" }}
          >
            {loading ? "Signing in..." : `Sign In as ${isAdmin ? "Admin" : "Customer"}`}
          </button>
        </form>

        {!isAdmin && (
          <div style={{ textAlign: "center", marginTop: "20px", fontSize: "0.875rem", color: "#64748b" }}>
            Don't have a verified account?{" "}
            <Link to="/register" style={{ fontWeight: "700", color: "#2563eb" }}>
              Register & Verify OTP
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}