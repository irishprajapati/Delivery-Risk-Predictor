import { useState } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { verifyOTP, getErrorMessage } from "../services/api";

export default function VerifyOTP() {
  const navigate = useNavigate();
  const location = useLocation();

  const phone = location.state?.phone || "";

  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");

  const handleVerify = async (e) => {
    e.preventDefault();
    setError("");

    if (!phone) {
      setError("Phone number is missing. Please register again.");
      return;
    }

    setLoading(true);

    try {
      await verifyOTP(phone, otp);
      setSuccess("OTP verified successfully! Redirecting to login...");
      setTimeout(() => {
        navigate("/login", { replace: true });
      }, 1200);
    } catch (err) {
      console.error("OTP verification error:", err);
      const msg = getErrorMessage(err, "Invalid OTP code. Please try again.");
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

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
            Verify OTP Code
          </p>
          <p style={{ color: "#64748b", fontSize: "0.8rem", margin: "2px 0 0" }}>
            Sent to: <strong>{phone || "your phone"}</strong>
          </p>
        </div>

        <form onSubmit={handleVerify} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ color: "#334155" }}>Enter 6-Digit OTP</label>
            <input
              type="text"
              inputMode="numeric"
              maxLength="6"
              className="form-control-modern"
              style={{ textAlign: "center", fontSize: "1.35rem", letterSpacing: "0.2em", fontWeight: "700" }}
              placeholder="••••••"
              value={otp}
              onChange={(e) => {
                setOtp(e.target.value.replace(/\D/g, ""));
                setError("");
              }}
              required
            />
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

          {success && (
            <div
              style={{
                padding: "10px 12px",
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: "6px",
                color: "#16a34a",
                fontSize: "0.85rem",
                textAlign: "center",
                fontWeight: "600",
              }}
            >
              {success}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-modern btn-modern-primary"
            style={{ width: "100%", marginTop: "6px", padding: "10px" }}
          >
            {loading ? "Verifying..." : "Verify & Complete"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: "18px", fontSize: "0.85rem" }}>
          <Link to="/register" style={{ color: "#64748b", textDecoration: "none" }}>
            ← Back to Registration
          </Link>
        </div>
      </div>
    </div>
  );
}