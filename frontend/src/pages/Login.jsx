import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { login, getErrorMessage } from "../services/api";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const navigate = useNavigate();
  const { login: authLogin } = useAuth();

  const [role, setRole] = useState("customer");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

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
      const msg = getErrorMessage(
        err,
        "Invalid credentials. Please check your username/phone and password."
      );
      setError(msg);
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
        backgroundColor: "#f1f5f9",
        padding: "20px",
      }}
    >
      <div
        className="card-modern animate-fade-in"
        style={{
          width: "100%",
          maxWidth: "400px",
          padding: "32px 28px",
          background: "#ffffff",
          border: "1px solid #cbd5e1",
          borderRadius: "12px",
          boxShadow: "0 4px 12px rgba(15, 23, 42, 0.08)",
        }}
      >
        {/* Project Header */}
        <div style={{ textAlign: "center", marginBottom: "20px", borderBottom: "1px solid #f1f5f9", paddingBottom: "16px" }}>
          <h1 style={{ fontSize: "1.35rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
            Delivery Failure Prediction
          </h1>
          <p style={{ color: "#475569", fontSize: "0.9rem", fontWeight: "600", marginTop: "4px" }}>
            Login
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
            borderRadius: "8px",
            marginBottom: "20px",
          }}
        >
          <button
            type="button"
            onClick={() => handleRoleChange("customer")}
            style={{
              padding: "8px 12px",
              fontSize: "0.875rem",
              fontWeight: "600",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              background: !isAdmin ? "#ffffff" : "transparent",
              color: !isAdmin ? "#0f172a" : "#64748b",
              boxShadow: !isAdmin ? "0 1px 2px rgba(0,0,0,0.08)" : "none",
              transition: "all 0.15s ease",
            }}
          >
            Customer Login
          </button>

          <button
            type="button"
            onClick={() => handleRoleChange("admin")}
            style={{
              padding: "8px 12px",
              fontSize: "0.875rem",
              fontWeight: "600",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
              background: isAdmin ? "#ffffff" : "transparent",
              color: isAdmin ? "#0f172a" : "#64748b",
              boxShadow: isAdmin ? "0 1px 2px rgba(0,0,0,0.08)" : "none",
              transition: "all 0.15s ease",
            }}
          >
            Admin Login
          </button>
        </div>

        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Username / Phone Number */}
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ color: "#334155" }}>
              {isAdmin ? "Username" : "Phone Number"}
            </label>
            <input
              type={isAdmin ? "text" : "tel"}
              className="form-control-modern"
              placeholder={isAdmin ? "Enter admin username" : "Enter phone number (e.g. 9841878273)"}
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
            />
          </div>

          {/* Password with Eye Toggle Button */}
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ color: "#334155" }}>
              Password
            </label>
            <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
              <input
                type={showPassword ? "text" : "password"}
                className="form-control-modern"
                placeholder="Enter password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={{ paddingRight: "42px" }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: "absolute",
                  right: "10px",
                  background: "transparent",
                  border: "none",
                  cursor: "pointer",
                  color: "#64748b",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "4px",
                }}
                title={showPassword ? "Hide password" : "Show password"}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  /* Eye Off SVG */
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  /* Eye SVG */
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {error && (
            <div
              style={{
                padding: "10px 12px",
                background: "#fef2f2",
                border: "1px solid #fecaca",
                borderRadius: "6px",
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
            className="btn-modern btn-modern-primary"
            style={{ width: "100%", marginTop: "6px", padding: "10px" }}
          >
            {loading ? "Logging in..." : `Login as ${isAdmin ? "Admin" : "Customer"}`}
          </button>
        </form>

        {!isAdmin && (
          <div style={{ textAlign: "center", marginTop: "18px", fontSize: "0.85rem", color: "#64748b" }}>
            Don't have an account?{" "}
            <Link to="/register" style={{ fontWeight: "600", color: "#2563eb" }}>
              Register & Verify OTP
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}