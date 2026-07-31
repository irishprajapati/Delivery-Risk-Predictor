import { Link, useNavigate, useLocation } from "react-router-dom";

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/login", { replace: true });
  };

  const isActive = (path) => location.pathname === path;

  return (
    <nav style={styles.nav}>
      <h2 style={styles.logo}>Delivery Admin</h2>

      <div style={styles.links}>
        <Link
          to="/"
          style={{ ...styles.link, ...(isActive("/") ? styles.activeLink : {}) }}
        >
          Dashboard
        </Link>
        <Link
          to="/predict"
          style={{
            ...styles.link,
            ...(isActive("/predict") ? styles.activeLink : {}),
          }}
        >
          Predict
        </Link>
        <Link
          to="/history"
          style={{
            ...styles.link,
            ...(isActive("/history") ? styles.activeLink : {}),
          }}
        >
          History
        </Link>
      </div>

      <button type="button" onClick={handleLogout} style={styles.logout}>
        Logout
      </button>
    </nav>
  );
};

const styles = {
  nav: {
    display: "flex",
    justifyContent: "space-between",
    padding: "12px 24px",
    background: "#1e293b",
    color: "white",
    alignItems: "center",
  },
  logo: {
    margin: 0,
    fontSize: "1.25rem",
  },
  links: {
    display: "flex",
    gap: "8px",
  },
  link: {
    color: "#cbd5e1",
    textDecoration: "none",
    fontWeight: "500",
    padding: "6px 14px",
    borderRadius: "6px",
    transition: "background 0.2s, color 0.2s",
  },
  activeLink: {
    color: "white",
    background: "#334155",
  },
  logout: {
    background: "#ef4444",
    color: "white",
    border: "none",
    padding: "8px 16px",
    cursor: "pointer",
    borderRadius: "6px",
    fontWeight: "500",
  },
};

export default Navbar;
