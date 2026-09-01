import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getAdminProfile,
  changeAdminPassword,
  getErrorMessage,
} from "../../services/api";

const AdminProfile = () => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Change Password state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [passwordError, setPasswordError] = useState("");

  const fetchProfile = async () => {
    try {
      setLoading(true);
      setError("");
      const data = await getAdminProfile();
      setProfile(data);
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          "Failed to load admin profile. Please re-login."
        )
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordSuccess("");
    setPasswordError("");

    if (!currentPassword) {
      setPasswordError("Please enter your current password.");
      return;
    }

    if (newPassword.length < 6) {
      setPasswordError("New password must be at least 6 characters long.");
      return;
    }

    if (newPassword !== confirmPassword) {
      setPasswordError("New passwords do not match.");
      return;
    }

    try {
      setPasswordSaving(true);
      await changeAdminPassword(currentPassword, newPassword);
      setPasswordSuccess("Admin password updated successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPasswordError(getErrorMessage(err, "Failed to update password."));
    } finally {
      setPasswordSaving(false);
    }
  };

  if (loading) {
    return (
      <div
        className="card-modern"
        style={{
          textAlign: "center",
          padding: "48px 24px",
          maxWidth: "800px",
          margin: "0 auto",
        }}
      >
        <p style={{ color: "#64748b" }}>Loading administrator profile...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="card-modern"
        style={{
          maxWidth: "800px",
          margin: "0 auto",
          borderColor: "#fecaca",
          backgroundColor: "#fef2f2",
        }}
      >
        <p style={{ color: "#dc2626", marginBottom: "12px" }}>{error}</p>
        <Link
          to="/login"
          className="btn-modern btn-modern-primary btn-modern-sm"
        >
          Go to Login
        </Link>
      </div>
    );
  }

  return (
    <div
      className="animate-fade-in"
      style={{ maxWidth: "860px", margin: "0 auto", paddingBottom: "48px" }}
    >
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <h1
          style={{
            fontSize: "1.65rem",
            fontWeight: "700",
            color: "#0f172a",
            margin: 0,
          }}
        >
          Administrator Profile
        </h1>
        <p
          style={{
            fontSize: "0.875rem",
            color: "#64748b",
            margin: "4px 0 0",
          }}
        >
          System administrator credentials, role permissions, and security
          settings
        </p>
      </div>

      {/* Account Info Card */}
      <div
        className="card-modern"
        style={{ padding: "24px", marginBottom: "20px" }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "16px",
            borderBottom: "1px solid #f1f5f9",
            paddingBottom: "18px",
            marginBottom: "18px",
          }}
        >
          <div>
            <span
              style={{
                fontSize: "0.75rem",
                fontWeight: "700",
                color: "#64748b",
                textTransform: "uppercase",
              }}
            >
              Account Username
            </span>
            <div
              style={{
                fontSize: "1.35rem",
                fontWeight: "700",
                color: "#0f172a",
                marginTop: "2px",
              }}
            >
              {profile?.username}
            </div>
            <div
              style={{
                fontSize: "0.825rem",
                color: "#64748b",
                marginTop: "2px",
              }}
            >
              Admin ID: <strong>#{profile?.id}</strong>
            </div>
          </div>

          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            <span
              className="badge-modern badge-status"
              style={{
                fontSize: "0.75rem",
                padding: "4px 10px",
                background: "#f1f5f9",
                color: "#334155",
                fontWeight: "700",
              }}
            >
              Role: {profile?.role?.toUpperCase() || "ADMIN"}
            </span>

            {profile?.is_active ? (
              <span
                className="badge-modern badge-status success"
                style={{ fontSize: "0.75rem", padding: "4px 10px" }}
              >
                Active Status
              </span>
            ) : (
              <span
                className="badge-modern badge-status"
                style={{
                  fontSize: "0.75rem",
                  padding: "4px 10px",
                  background: "#fef2f2",
                  color: "#dc2626",
                }}
              >
                Disabled
              </span>
            )}
          </div>
        </div>

        {/* Admin Permissions & System Overview */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "12px",
          }}
        >
          <div
            style={{
              padding: "12px 14px",
              background: "#f8fafc",
              borderRadius: "8px",
              border: "1px solid #e2e8f0",
            }}
          >
            <span
              style={{
                fontSize: "0.75rem",
                fontWeight: "600",
                color: "#64748b",
              }}
            >
              Access Level
            </span>
            <div
              style={{
                fontSize: "0.95rem",
                fontWeight: "700",
                color: "#0f172a",
                marginTop: "2px",
              }}
            >
              Full Operational Authority
            </div>
          </div>

          <div
            style={{
              padding: "12px 14px",
              background: "#f8fafc",
              borderRadius: "8px",
              border: "1px solid #e2e8f0",
            }}
          >
            <span
              style={{
                fontSize: "0.75rem",
                fontWeight: "600",
                color: "#64748b",
              }}
            >
              Customer Management
            </span>
            <div
              style={{
                fontSize: "0.95rem",
                fontWeight: "700",
                color: "#0f172a",
                marginTop: "2px",
              }}
            >
              Directory & Account Status
            </div>
          </div>

          <div
            style={{
              padding: "12px 14px",
              background: "#f8fafc",
              borderRadius: "8px",
              border: "1px solid #e2e8f0",
            }}
          >
            <span
              style={{
                fontSize: "0.75rem",
                fontWeight: "600",
                color: "#64748b",
              }}
            >
              ML Failure Prediction
            </span>
            <div
              style={{
                fontSize: "0.95rem",
                fontWeight: "700",
                color: "#0f172a",
                marginTop: "2px",
              }}
            >
              Dispatch & Explanations
            </div>
          </div>
        </div>
      </div>

      {/* Grid: Change Password + Quick Navigation */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
          gap: "20px",
        }}
      >
        {/* Change Admin Password */}
        <div className="card-modern" style={{ padding: "24px" }}>
          <h2
            style={{
              fontSize: "1rem",
              fontWeight: "700",
              color: "#0f172a",
              marginBottom: "6px",
            }}
          >
            Change Administrator Password
          </h2>
          <p
            style={{
              fontSize: "0.825rem",
              color: "#64748b",
              marginBottom: "16px",
            }}
          >
            Update password for account <strong>{profile?.username}</strong>
          </p>

          {passwordSuccess && (
            <div
              style={{
                padding: "10px 12px",
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                borderRadius: "6px",
                color: "#16a34a",
                fontSize: "0.85rem",
                marginBottom: "14px",
              }}
            >
              {passwordSuccess}
            </div>
          )}

          {passwordError && (
            <div
              style={{
                padding: "10px 12px",
                background: "#fef2f2",
                border: "1px solid #fecaca",
                borderRadius: "6px",
                color: "#dc2626",
                fontSize: "0.85rem",
                marginBottom: "14px",
              }}
            >
              {passwordError}
            </div>
          )}

          <form onSubmit={handleChangePassword}>
            <div className="form-group" style={{ marginBottom: "10px" }}>
              <label className="form-label" htmlFor="admin-curr-pass">
                Current Password
              </label>
              <input
                id="admin-curr-pass"
                type="password"
                className="form-control-modern"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter current admin password"
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: "10px" }}>
              <label className="form-label" htmlFor="admin-new-pass">
                New Password
              </label>
              <input
                id="admin-new-pass"
                type="password"
                className="form-control-modern"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="At least 6 characters"
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: "14px" }}>
              <label className="form-label" htmlFor="admin-confirm-pass">
                Confirm New Password
              </label>
              <input
                id="admin-confirm-pass"
                type="password"
                className="form-control-modern"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                required
              />
            </div>

            <button
              type="submit"
              disabled={passwordSaving}
              className="btn-modern btn-modern-primary btn-modern-sm"
              style={{ width: "100%" }}
            >
              {passwordSaving ? "Updating Password..." : "Update Password"}
            </button>
          </form>
        </div>

        {/* Quick Management Shortcuts */}
        <div className="card-modern" style={{ padding: "24px" }}>
          <h2
            style={{
              fontSize: "1rem",
              fontWeight: "700",
              color: "#0f172a",
              marginBottom: "6px",
            }}
          >
            Administrative Navigation
          </h2>
          <p
            style={{
              fontSize: "0.825rem",
              color: "#64748b",
              marginBottom: "16px",
            }}
          >
            Quick access to core modules of the delivery system
          </p>

          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            <Link
              to="/admin/customers"
              className="btn-modern btn-modern-secondary"
              style={{
                justifyContent: "space-between",
                padding: "10px 14px",
                fontSize: "0.875rem",
              }}
            >
              <span>Customer Directory & Profiles</span>
              <span style={{ color: "#64748b" }}>→</span>
            </Link>

            <Link
              to="/admin/dashboard"
              className="btn-modern btn-modern-secondary"
              style={{
                justifyContent: "space-between",
                padding: "10px 14px",
                fontSize: "0.875rem",
              }}
            >
              <span>Operations Dashboard</span>
              <span style={{ color: "#64748b" }}>→</span>
            </Link>

            <Link
              to="/admin/deliveries"
              className="btn-modern btn-modern-secondary"
              style={{
                justifyContent: "space-between",
                padding: "10px 14px",
                fontSize: "0.875rem",
              }}
            >
              <span>All Deliveries & Lifecycles</span>
              <span style={{ color: "#64748b" }}>→</span>
            </Link>

            <Link
              to="/admin/dispatch"
              className="btn-modern btn-modern-secondary"
              style={{
                justifyContent: "space-between",
                padding: "10px 14px",
                fontSize: "0.875rem",
              }}
            >
              <span>Dispatch & Rider Ranking</span>
              <span style={{ color: "#64748b" }}>→</span>
            </Link>

            <Link
              to="/admin/riders"
              className="btn-modern btn-modern-secondary"
              style={{
                justifyContent: "space-between",
                padding: "10px 14px",
                fontSize: "0.875rem",
              }}
            >
              <span>Riders & Performance</span>
              <span style={{ color: "#64748b" }}>→</span>
            </Link>

            <Link
              to="/admin/predictions"
              className="btn-modern btn-modern-secondary"
              style={{
                justifyContent: "space-between",
                padding: "10px 14px",
                fontSize: "0.875rem",
              }}
            >
              <span>ML Prediction Audit History</span>
              <span style={{ color: "#64748b" }}>→</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminProfile;
