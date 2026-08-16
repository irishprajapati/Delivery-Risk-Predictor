import { useState } from "react";
import { useLocation, useNavigate, Link } from "react-router-dom";
import { verifyOTP } from "../services/api";

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
      if (err.response) {
        setError(err.response.data?.detail || "Invalid OTP code. Please try again.");
      } else {
        setError("Backend server not responding.");
      }
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
        background: "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)",
        padding: "20px",
      }}
    >
      <div
        className="card-modern animate-fade-in"
        style={{
          width: "100%",
          maxWidth: "400px",
          padding: "36px 32px",
          boxShadow: "0 20px 25px -5px rgba(15, 23, 42, 0.1), 0 8px 10px -6px rgba(15, 23, 42, 0.1)",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "24px" }}>
          <div style={{ fontSize: "2rem", marginBottom: "6px" }}>🔒</div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: "800", color: "#0f172a" }}>
            Verify OTP Code
          </h1>
          <p style={{ color: "#64748b", fontSize: "0.875rem", margin: "4px 0 0" }}>
            Enter the code sent to <strong>{phone || "your phone"}</strong>
          </p>
        </div>

        <form onSubmit={handleVerify} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label">Verification Code (OTP)</label>
            <input
              type="text"
              inputMode="numeric"
              maxLength="6"
              className="form-control-modern"
              style={{ textAlign: "center", fontSize: "1.35rem", letterSpacing: "0.2em", fontWeight: "700" }}
              placeholder="••••••"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
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

          {success && (
            <div
              style={{
                padding: "10px 14px",
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: "8px",
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
            className="btn-modern btn-modern-primary btn-modern-lg"
            style={{ width: "100%", marginTop: "6px" }}
          >
            {loading ? "Verifying..." : "Verify & Complete"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: "20px", fontSize: "0.875rem" }}>
          <Link to="/register" style={{ color: "#64748b", textDecoration: "none" }}>
            ← Back to Registration
          </Link>
        </div>
      </div>
    </div>
  );
}