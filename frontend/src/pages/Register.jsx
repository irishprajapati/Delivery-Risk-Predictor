import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { register, getErrorMessage } from "../services/api";

export default function Register() {
  const navigate = useNavigate();

  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRegister = async (e) => {
    e.preventDefault();
    setError("");

    const cleanPhone = phone.trim();
    if (!cleanPhone) {
      setError("Please enter a valid phone number.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match. Please re-enter.");
      return;
    }

    setLoading(true);

    try {
      await register(cleanPhone, password);
      navigate("/verify-otp", {
        state: {
          phone: cleanPhone,
        },
      });
    } catch (err) {
      console.error("Registration error:", err);
      const msg = getErrorMessage(
        err,
        "Registration failed. Please check your phone format (e.g. 9841878273)."
      );
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const isAlreadyRegistered =
    error.toLowerCase().includes("already exists") ||
    error.toLowerCase().includes("log in") ||
    error.toLowerCase().includes("already registered");

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
        <div style={{ textAlign: "center", marginBottom: "20px", borderBottom: "1px solid #f1f5f9", paddingBottom: "16px" }}>
          <h1 style={{ fontSize: "1.35rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
            Delivery Failure Prediction
          </h1>
          <p style={{ color: "#475569", fontSize: "0.9rem", fontWeight: "600", marginTop: "4px" }}>
            Customer Registration
          </p>
        </div>

        <form onSubmit={handleRegister} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ color: "#334155" }}>Phone Number</label>
            <input
              type="tel"
              className="form-control-modern"
              placeholder="e.g. 9841878273"
              value={phone}
              onChange={(e) => {
                setPhone(e.target.value);
                setError("");
              }}
              required
            />
            <span style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "2px", display: "block" }}>
              Format: 10-digit Nepal mobile (98XXXXXXXX / 97XXXXXXXX)
            </span>
          </div>

          {/* Password with Eye Toggle */}
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ color: "#334155" }}>Password</label>
            <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
              <input
                type={showPassword ? "text" : "password"}
                className="form-control-modern"
                placeholder="Minimum 6 characters"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setError("");
                }}
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
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Confirm Password with Eye Toggle */}
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ color: "#334155" }}>Confirm Password</label>
            <div style={{ position: "relative", display: "flex", alignItems: "center" }}>
              <input
                type={showConfirmPassword ? "text" : "password"}
                className="form-control-modern"
                placeholder="Confirm your password"
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  setError("");
                }}
                required
                style={{ paddingRight: "42px" }}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
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
                title={showConfirmPassword ? "Hide password" : "Show password"}
                aria-label={showConfirmPassword ? "Hide password" : "Show password"}
              >
                {showConfirmPassword ? (
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
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
                lineHeight: "1.4",
              }}
            >
              {error}
              {isAlreadyRegistered && (
                <div style={{ marginTop: "6px" }}>
                  <Link to="/login" style={{ color: "#2563eb", fontWeight: "700", textDecoration: "underline" }}>
                    Click here to Login
                  </Link>
                </div>
              )}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-modern btn-modern-primary"
            style={{ width: "100%", marginTop: "6px", padding: "10px" }}
          >
            {loading ? "Sending OTP Code..." : "Create Account & Send OTP"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: "18px", fontSize: "0.85rem", color: "#64748b" }}>
          Already have an account?{" "}
          <Link to="/login" style={{ fontWeight: "600", color: "#2563eb" }}>
            Login
          </Link>
        </div>
      </div>
    </div>
  );
}