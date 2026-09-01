import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { phone, logout, isAdmin, isCustomer, isRider } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const isActive = (path) => {
    if (path === "/customer/dashboard" && (location.pathname === "/" || location.pathname === "/customer/dashboard")) {
      return true;
    }
    if (path === "/rider/dashboard" && (location.pathname === "/" || location.pathname === "/rider/dashboard")) {
      return true;
    }
    if (path === "/admin/dashboard" && (location.pathname === "/" || location.pathname === "/admin/dashboard")) {
      return true;
    }
    return location.pathname === path || location.pathname.startsWith(path + "/");
  };

  return (
    <header style={styles.header}>
      <div style={styles.container}>
        {/* Brand */}
        <div style={styles.brandGroup}>
          <Link to={isAdmin ? "/admin/dashboard" : isRider ? "/rider/dashboard" : "/customer/dashboard"} style={styles.logo}>
            <span style={styles.logoText}>Delivery Failure Prediction</span>
          </Link>
          <span style={isAdmin ? styles.adminBadge : isRider ? styles.riderBadge : styles.customerBadge}>
            {isAdmin ? "Admin" : isRider ? "Rider" : "Customer"}
          </span>
        </div>

        {/* Links */}
        <nav style={styles.navLinks}>
          {isCustomer && (
            <>
              <Link
                to="/customer/dashboard"
                style={{
                  ...styles.link,
                  ...(isActive("/customer/dashboard") ? styles.activeLink : {}),
                }}
              >
                Dashboard
              </Link>
              <Link
                to="/customer/orders"
                style={{
                  ...styles.link,
                  ...(isActive("/customer/orders") ? styles.activeLink : {}),
                }}
              >
                My Orders
              </Link>
              <Link
                to="/customer/order"
                style={{
                  ...styles.link,
                  ...(isActive("/customer/order") ? styles.activeLink : {}),
                }}
              >
                Place Order
              </Link>
              <Link
                to="/customer/profile"
                style={{
                  ...styles.link,
                  ...(isActive("/customer/profile") ? styles.activeLink : {}),
                }}
              >
                Profile
              </Link>
            </>
          )}

          {isRider && (
            <>
              <Link
                to="/rider/dashboard"
                style={{
                  ...styles.link,
                  ...(isActive("/rider/dashboard") ? styles.activeLink : {}),
                }}
              >
                Operations Dashboard
              </Link>
              <Link
                to="/rider/deliveries"
                style={{
                  ...styles.link,
                  ...(isActive("/rider/deliveries") ? styles.activeLink : {}),
                }}
              >
                My Deliveries
              </Link>
            </>
          )}

          {isAdmin && (
            <>
              <Link
                to="/admin/dashboard"
                style={{
                  ...styles.link,
                  ...(isActive("/admin/dashboard") ? styles.activeLink : {}),
                }}
              >
                Dashboard
              </Link>
              <Link
                to="/admin/deliveries"
                style={{
                  ...styles.link,
                  ...(isActive("/admin/deliveries") ? styles.activeLink : {}),
                }}
              >
                Deliveries
              </Link>
              <Link
                to="/admin/dispatch"
                style={{
                  ...styles.link,
                  ...(isActive("/admin/dispatch") ? styles.activeLink : {}),
                }}
              >
                Dispatch
              </Link>
              <Link
                to="/admin/customers"
                style={{
                  ...styles.link,
                  ...(isActive("/admin/customers") ? styles.activeLink : {}),
                }}
              >
                Customers
              </Link>
              <Link
                to="/admin/riders"
                style={{
                  ...styles.link,
                  ...(isActive("/admin/riders") ? styles.activeLink : {}),
                }}
              >
                Riders
              </Link>
              <Link
                to="/admin/prediction"
                style={{
                  ...styles.link,
                  ...(isActive("/admin/prediction") ? styles.activeLink : {}),
                }}
              >
                Predictions
              </Link>
              <Link
                to="/admin/profile"
                style={{
                  ...styles.link,
                  ...(isActive("/admin/profile") ? styles.activeLink : {}),
                }}
              >
                Profile
              </Link>
            </>
          )}
        </nav>

        {/* Right side Profile & Logout */}
        <div style={styles.actions}>
          {(isCustomer || isRider) && phone && (
            <Link
              to={isCustomer ? "/customer/profile" : "/rider/profile"}
              style={{ textDecoration: "none" }}
            >
              <div style={styles.userPhoneBadge}>
                <span style={{ color: "#64748b" }}>{isRider ? "Rider:" : "User:"}</span>
                <strong style={{ color: "#0f172a" }}>{phone}</strong>
              </div>
            </Link>
          )}

          {isAdmin && (
            <Link
              to="/admin/profile"
              style={{ textDecoration: "none" }}
            >
              <div style={styles.userPhoneBadge}>
                <span style={{ color: "#64748b" }}>Admin:</span>
                <strong style={{ color: "#0f172a" }}>Profile</strong>
              </div>
            </Link>
          )}

          <button
            type="button"
            onClick={handleLogout}
            className="btn-modern btn-modern-sm btn-modern-secondary"
            style={{ padding: "6px 14px", fontSize: "0.825rem" }}
          >
            Logout
          </button>
        </div>
      </div>
    </header>
  );
};

const styles = {
  header: {
    backgroundColor: "#ffffff",
    borderBottom: "1px solid #e2e8f0",
    position: "sticky",
    top: 0,
    zIndex: 100,
  },
  container: {
    maxWidth: "1240px",
    margin: "0 auto",
    padding: "10px 20px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "16px",
    flexWrap: "wrap",
  },
  brandGroup: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  logo: {
    display: "flex",
    alignItems: "center",
    textDecoration: "none",
  },
  logoText: {
    fontSize: "1.05rem",
    fontWeight: "700",
    color: "#0f172a",
    letterSpacing: "-0.02em",
  },
  adminBadge: {
    fontSize: "0.7rem",
    fontWeight: "700",
    textTransform: "uppercase",
    padding: "2px 8px",
    borderRadius: "4px",
    background: "#f1f5f9",
    color: "#475569",
    border: "1px solid #e2e8f0",
  },
  riderBadge: {
    fontSize: "0.7rem",
    fontWeight: "700",
    textTransform: "uppercase",
    padding: "2px 8px",
    borderRadius: "4px",
    background: "#eff6ff",
    color: "#2563eb",
    border: "1px solid #bfdbfe",
  },
  customerBadge: {
    fontSize: "0.7rem",
    fontWeight: "700",
    textTransform: "uppercase",
    padding: "2px 8px",
    borderRadius: "4px",
    background: "#f0fdf4",
    color: "#16a34a",
    border: "1px solid #bbf7d0",
  },
  navLinks: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
  },
  link: {
    padding: "6px 12px",
    fontSize: "0.85rem",
    fontWeight: "600",
    color: "#64748b",
    borderRadius: "6px",
    textDecoration: "none",
    transition: "all 0.15s ease",
  },
  activeLink: {
    color: "#2563eb",
    backgroundColor: "#eff6ff",
  },
  actions: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
  },
  userPhoneBadge: {
    fontSize: "0.825rem",
    background: "#f8fafc",
    padding: "5px 10px",
    borderRadius: "6px",
    border: "1px solid #e2e8f0",
    display: "flex",
    gap: "6px",
    alignItems: "center",
  },
};

export default Navbar;
