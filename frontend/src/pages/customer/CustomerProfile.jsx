import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  getCustomerProfile,
  updateCustomerProfile,
  changeCustomerPassword,
  getCustomerOrders,
  getErrorMessage,
} from "../../services/api";
import { useAuth } from "../../context/AuthContext";

const CustomerProfile = () => {
  const { setUser } = useAuth();
  const [profile, setProfile] = useState(null);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Edit Phone State
  const [editPhone, setEditPhone] = useState("");
  const [phoneSaving, setPhoneSaving] = useState(false);
  const [phoneSuccess, setPhoneSuccess] = useState("");
  const [phoneError, setPhoneError] = useState("");

  // Change Password State
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState("");
  const [passwordError, setPasswordError] = useState("");

  const fetchProfileAndOrders = async () => {
    try {
      setLoading(true);
      setError("");
      const [profileData, ordersData] = await Promise.all([
        getCustomerProfile(),
        getCustomerOrders().catch(() => []),
      ]);
      setProfile(profileData);
      setEditPhone(profileData.phone || "");
      setOrders(ordersData || []);
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          "Failed to load customer profile. Please log in again."
        )
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfileAndOrders();
  }, []);

  const handleUpdatePhone = async (e) => {
    e.preventDefault();
    setPhoneSuccess("");
    setPhoneError("");

    if (!editPhone.trim()) {
      setPhoneError("Phone number cannot be empty.");
      return;
    }

    try {
      setPhoneSaving(true);
      const res = await updateCustomerProfile({ phone: editPhone.trim() });
      setProfile(res.profile);
      setUser(res.profile);
      localStorage.setItem("phone", res.profile.phone);
      setPhoneSuccess("Account information updated successfully.");
    } catch (err) {
      setPhoneError(
        getErrorMessage(err, "Failed to update account information.")
      );
    } finally {
      setPhoneSaving(false);
    }
  };

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
      await changeCustomerPassword(currentPassword, newPassword);
      setPasswordSuccess("Password changed successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setPasswordError(getErrorMessage(err, "Failed to change password."));
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
          maxWidth: "860px",
          margin: "0 auto",
        }}
      >
        <p style={{ color: "#64748b" }}>Loading profile information...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="card-modern"
        style={{
          maxWidth: "860px",
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

  const successRate =
    profile?.success_rate !== undefined
      ? `${profile.success_rate}%`
      : profile?.total_orders > 0
      ? `${((profile.successful_deliveries / profile.total_orders) * 100).toFixed(1)}%`
      : "100%";

  const failureRate =
    profile?.failure_rate !== undefined
      ? `${profile.failure_rate}%`
      : profile?.total_orders > 0
      ? `${((profile.failed_deliveries / profile.total_orders) * 100).toFixed(1)}%`
      : "0%";

  const formattedDate = profile?.created_at
    ? new Date(profile.created_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "N/A";

  const formattedLastDelivery = profile?.last_successful_delivery
    ? new Date(profile.last_successful_delivery).toLocaleString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "No completed delivery yet";

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
          Customer Profile
        </h1>
        <p
          style={{
            fontSize: "0.875rem",
            color: "#64748b",
            margin: "4px 0 0",
          }}
        >
          Manage your account information, security credentials, and view
          delivery reliability statistics
        </p>
      </div>

      {/* Account Overview Card */}
      <div className="card-modern" style={{ padding: "24px", marginBottom: "20px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
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
              Registered Mobile
            </span>
            <div
              style={{
                fontSize: "1.35rem",
                fontWeight: "700",
                color: "#0f172a",
                marginTop: "2px",
              }}
            >
              {profile?.phone}
            </div>
            <div
              style={{
                fontSize: "0.825rem",
                color: "#64748b",
                marginTop: "2px",
              }}
            >
              Customer ID: <strong>#{profile?.id}</strong> • Member since:{" "}
              <strong>{formattedDate}</strong>
            </div>
          </div>

          <div>
            {profile?.is_verified ? (
              <span
                className="badge-modern badge-status success"
                style={{ fontSize: "0.8rem", padding: "5px 12px" }}
              >
                Verified Account
              </span>
            ) : (
              <span
                className="badge-modern badge-status"
                style={{
                  fontSize: "0.8rem",
                  padding: "5px 12px",
                  background: "#fffbeb",
                  color: "#d97706",
                  borderColor: "#fde68a",
                }}
              >
                Unverified Account
              </span>
            )}
          </div>
        </div>

        {/* System Delivery Statistics */}
        <div style={{ marginBottom: "8px" }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "12px",
            }}
          >
            <h2
              style={{
                fontSize: "0.95rem",
                fontWeight: "700",
                color: "#0f172a",
                margin: 0,
              }}
            >
              Delivery Statistics & Reliability History
            </h2>
            <span
              style={{
                fontSize: "0.75rem",
                color: "#64748b",
                background: "#f8fafc",
                padding: "2px 8px",
                borderRadius: "4px",
                border: "1px solid #e2e8f0",
              }}
            >
              System Calculated
            </span>
          </div>

          {/* Stats Grid */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
              gap: "10px",
              marginBottom: "14px",
            }}
          >
            <div
              style={{
                padding: "12px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontSize: "0.725rem",
                  fontWeight: "600",
                  color: "#64748b",
                }}
              >
                Total Orders
              </span>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: "700",
                  color: "#0f172a",
                  marginTop: "2px",
                }}
              >
                {profile?.total_orders ?? 0}
              </div>
            </div>

            <div
              style={{
                padding: "12px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontSize: "0.725rem",
                  fontWeight: "600",
                  color: "#64748b",
                }}
              >
                Successful
              </span>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: "700",
                  color: "#16a34a",
                  marginTop: "2px",
                }}
              >
                {profile?.successful_deliveries ?? 0}
              </div>
            </div>

            <div
              style={{
                padding: "12px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontSize: "0.725rem",
                  fontWeight: "600",
                  color: "#64748b",
                }}
              >
                Failed
              </span>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: "700",
                  color: "#dc2626",
                  marginTop: "2px",
                }}
              >
                {profile?.failed_deliveries ?? 0}
              </div>
            </div>

            <div
              style={{
                padding: "12px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontSize: "0.725rem",
                  fontWeight: "600",
                  color: "#64748b",
                }}
              >
                Unreachable
              </span>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: "700",
                  color: "#d97706",
                  marginTop: "2px",
                }}
              >
                {profile?.unreachable_count ?? 0}
              </div>
            </div>

            <div
              style={{
                padding: "12px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontSize: "0.725rem",
                  fontWeight: "600",
                  color: "#64748b",
                }}
              >
                Cancellations
              </span>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: "700",
                  color: "#64748b",
                  marginTop: "2px",
                }}
              >
                {profile?.cancellation_count ?? 0}
              </div>
            </div>

            <div
              style={{
                padding: "12px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontSize: "0.725rem",
                  fontWeight: "600",
                  color: "#64748b",
                }}
              >
                Success Rate
              </span>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: "700",
                  color: "#2563eb",
                  marginTop: "2px",
                }}
              >
                {successRate}
              </div>
            </div>

            <div
              style={{
                padding: "12px",
                background: "#f8fafc",
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
              }}
            >
              <span
                style={{
                  fontSize: "0.725rem",
                  fontWeight: "600",
                  color: "#64748b",
                }}
              >
                Failure Rate
              </span>
              <div
                style={{
                  fontSize: "1.35rem",
                  fontWeight: "700",
                  color: "#475569",
                  marginTop: "2px",
                }}
              >
                {failureRate}
              </div>
            </div>
          </div>

          <div
            style={{
              fontSize: "0.8rem",
              color: "#64748b",
              background: "#f8fafc",
              padding: "8px 12px",
              borderRadius: "6px",
              border: "1px solid #e2e8f0",
            }}
          >
            Last Successful Delivery: <strong>{formattedLastDelivery}</strong>
          </div>
        </div>
      </div>

      {/* Account Settings & Security Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))",
          gap: "20px",
          marginBottom: "20px",
        }}
      >
        {/* Update Account Info Form */}
        <div className="card-modern" style={{ padding: "24px" }}>
          <h2
            style={{
              fontSize: "1rem",
              fontWeight: "700",
              color: "#0f172a",
              marginBottom: "6px",
            }}
          >
            Account Information
          </h2>
          <p
            style={{
              fontSize: "0.825rem",
              color: "#64748b",
              marginBottom: "16px",
            }}
          >
            Update your registered mobile contact number
          </p>

          {phoneSuccess && (
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
              {phoneSuccess}
            </div>
          )}

          {phoneError && (
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
              {phoneError}
            </div>
          )}

          <form onSubmit={handleUpdatePhone}>
            <div className="form-group">
              <label className="form-label" htmlFor="customer-phone-input">
                Mobile Number
              </label>
              <input
                id="customer-phone-input"
                type="text"
                className="form-control-modern"
                value={editPhone}
                onChange={(e) => setEditPhone(e.target.value)}
                placeholder="e.g. 9841878273"
                required
              />
              <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                Format: 10-digit Nepal mobile number (98XXXXXXXX or 97XXXXXXXX)
              </span>
            </div>

            <button
              type="submit"
              disabled={phoneSaving || editPhone === profile?.phone}
              className="btn-modern btn-modern-primary btn-modern-sm"
              style={{ marginTop: "6px", width: "100%" }}
            >
              {phoneSaving ? "Saving..." : "Save Phone Number"}
            </button>
          </form>
        </div>

        {/* Change Password Form */}
        <div className="card-modern" style={{ padding: "24px" }}>
          <h2
            style={{
              fontSize: "1rem",
              fontWeight: "700",
              color: "#0f172a",
              marginBottom: "6px",
            }}
          >
            Change Password
          </h2>
          <p
            style={{
              fontSize: "0.825rem",
              color: "#64748b",
              marginBottom: "16px",
            }}
          >
            Update your account password securely
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
              <label className="form-label" htmlFor="curr-pass-input">
                Current Password
              </label>
              <input
                id="curr-pass-input"
                type="password"
                className="form-control-modern"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter current password"
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: "10px" }}>
              <label className="form-label" htmlFor="new-pass-input">
                New Password
              </label>
              <input
                id="new-pass-input"
                type="password"
                className="form-control-modern"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="At least 6 characters"
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: "14px" }}>
              <label className="form-label" htmlFor="confirm-pass-input">
                Confirm New Password
              </label>
              <input
                id="confirm-pass-input"
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
      </div>

      {/* Recent Orders Overview */}
      <div className="card-modern" style={{ padding: "24px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "14px",
          }}
        >
          <div>
            <h2
              style={{
                fontSize: "1rem",
                fontWeight: "700",
                color: "#0f172a",
                margin: 0,
              }}
            >
              Recent Orders & Delivery History
            </h2>
            <p
              style={{
                fontSize: "0.8rem",
                color: "#64748b",
                margin: "2px 0 0",
              }}
            >
              Showing your latest placed orders
            </p>
          </div>
          <Link
            to="/customer/dashboard"
            className="btn-modern btn-modern-secondary btn-modern-sm"
          >
            View All Orders
          </Link>
        </div>

        {orders.length === 0 ? (
          <div
            style={{
              padding: "24px",
              textAlign: "center",
              background: "#f8fafc",
              borderRadius: "8px",
              border: "1px solid #e2e8f0",
            }}
          >
            <p style={{ color: "#64748b", margin: 0, fontSize: "0.875rem" }}>
              No orders placed yet.
            </p>
            <Link
              to="/customer/order"
              className="btn-modern btn-modern-primary btn-modern-sm"
              style={{ marginTop: "10px" }}
            >
              Place Your First Order
            </Link>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.85rem",
              }}
            >
              <thead>
                <tr
                  style={{
                    borderBottom: "2px solid #e2e8f0",
                    textAlign: "left",
                    color: "#64748b",
                  }}
                >
                  <th style={{ padding: "8px 10px" }}>Order ID</th>
                  <th style={{ padding: "8px 10px" }}>Date</th>
                  <th style={{ padding: "8px 10px" }}>Item</th>
                  <th style={{ padding: "8px 10px" }}>Total</th>
                  <th style={{ padding: "8px 10px" }}>Payment</th>
                  <th style={{ padding: "8px 10px" }}>Delivery Status</th>
                  <th style={{ padding: "8px 10px", textAlign: "right" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {orders.slice(0, 5).map((ord) => (
                  <tr
                    key={ord.id}
                    style={{
                      borderBottom: "1px solid #f1f5f9",
                    }}
                  >
                    <td style={{ padding: "10px 10px", fontWeight: "600" }}>
                      #{ord.id}
                    </td>
                    <td style={{ padding: "10px 10px", color: "#64748b" }}>
                      {ord.created_at
                        ? new Date(ord.created_at).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                          })
                        : "—"}
                    </td>
                    <td style={{ padding: "10px 10px" }}>{ord.item_name}</td>
                    <td style={{ padding: "10px 10px", fontWeight: "600" }}>
                      Rs. {ord.total_price}
                    </td>
                    <td style={{ padding: "10px 10px" }}>
                      <span
                        className="badge-modern badge-status"
                        style={{ fontSize: "0.7rem" }}
                      >
                        {ord.payment_method?.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: "10px 10px" }}>
                      <span
                        className={`badge-modern badge-status ${
                          ord.delivery_status === "delivered"
                            ? "success"
                            : ord.delivery_status === "failed"
                            ? "danger"
                            : "active"
                        }`}
                        style={{ fontSize: "0.7rem" }}
                      >
                        {ord.delivery_status}
                      </span>
                    </td>
                    <td style={{ padding: "10px 10px", textAlign: "right" }}>
                      <Link
                        to={`/customer/orders/${ord.id}`}
                        className="btn-modern btn-modern-secondary btn-modern-sm"
                        style={{ padding: "4px 8px", fontSize: "0.75rem" }}
                      >
                        Details
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default CustomerProfile;
