import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { phone, logout, switchRole, isAdmin, isCustomer } = useAuth();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  const isActive = (path) => {
    if (path === "/customer/dashboard" && (location.pathname === "/" || location.pathname === "/customer/dashboard")) {
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
          <Link to={isAdmin ? "/admin/dashboard" : "/customer/dashboard"} style={styles.logo}>
            <span style={styles.logoIcon}>⚡</span>
            <span style={styles.logoText}>LogiRisk</span>
          </Link>
          <span style={isAdmin ? styles.adminBadge : styles.customerBadge}>
            {isAdmin ? "Admin Portal" : "Customer"}
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
                My Orders
              </Link>
              <Link
                to="/customer/order"
                style={{
                  ...styles.link,
                  ...(isActive("/customer/order") ? styles.activeLink : {}),
                }}
              >
                + Place Order
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
                Operations
              </Link>
              <Link
                to="/admin/prediction"
                style={{
                  ...styles.link,
                  ...(isActive("/admin/prediction") ? styles.activeLink : {}),
                }}
              >
                ML Risk Analyzer
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
                to="/admin/riders"
                style={{
                  ...styles.link,
                  ...(isActive("/admin/riders") ? styles.activeLink : {}),
                }}
              >
                Riders
              </Link>
              <Link
                to="/admin/predictions"
                style={{
                  ...styles.link,
                  ...(isActive("/admin/predictions") ? styles.activeLink : {}),
                }}
              >
                History
              </Link>
            </>
          )}
        </nav>

        {/* Right side Profile & Actions */}
        <div style={styles.actions}>
          {isCustomer && phone && (
            <div style={styles.userPhoneBadge}>
              <span style={{ color: "#64748b" }}>User:</span>
              <strong style={{ color: "#0f172a" }}>{phone}</strong>
            </div>
          )}

          {/* Quick Demo Switcher */}
          <button
            type="button"
            onClick={() => {
              const nextRole = isAdmin ? "customer" : "admin";
              switchRole(nextRole);
              navigate(nextRole === "admin" ? "/admin/dashboard" : "/customer/dashboard");
            }}
            style={styles.switchRoleBtn}
            title="Switch view between Customer and Admin for testing"
          >
            Switch to {isAdmin ? "Customer" : "Admin"}
          </button>

          <button
            type="button"
            onClick={handleLogout}
            className="btn-modern btn-modern-sm btn-modern-secondary"
            style={{ padding: "6px 12px", fontSize: "0.8rem" }}
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
    zIndex: 1000,
    boxShadow: "0 1px 3px 0 rgba(15, 23, 42, 0.04)",
  },
  container: {
    maxWidth: "1280px",
    margin: "0 auto",
    padding: "0 24px",
    height: "64px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: "16px",
  },
  brandGroup: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  logo: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    textDecoration: "none",
  },
  logoIcon: {
    fontSize: "1.25rem",
    background: "#eff6ff",
    padding: "4px 8px",
    borderRadius: "8px",
  },
  logoText: {
    fontSize: "1.15rem",
    fontWeight: "800",
    color: "#0f172a",
    letterSpacing: "-0.03em",
  },
  adminBadge: {
    fontSize: "0.7rem",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    padding: "2px 8px",
    borderRadius: "999px",
    background: "#f1f5f9",
    color: "#475569",
    border: "1px solid #e2e8f0",
  },
  customerBadge: {
    fontSize: "0.7rem",
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    padding: "2px 8px",
    borderRadius: "999px",
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
    padding: "8px 14px",
    fontSize: "0.875rem",
    fontWeight: "600",
    color: "#64748b",
    borderRadius: "8px",
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
    fontSize: "0.85rem",
    display: "flex",
    alignItems: "center",
    gap: "6px",
    background: "#f8fafc",
    padding: "6px 12px",
    borderRadius: "8px",
    border: "1px solid #e2e8f0",
  },
  switchRoleBtn: {
    background: "transparent",
    border: "1px dashed #94a3b8",
    color: "#475569",
    padding: "5px 10px",
    borderRadius: "6px",
    fontSize: "0.75rem",
    fontWeight: "600",
    cursor: "pointer",
  },
};

export default Navbar;
