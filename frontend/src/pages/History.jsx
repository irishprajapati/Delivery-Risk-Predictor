import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHistory } from "../services/api";

const getPhoneNumber = (item) =>
  item.input_data?.phone_number ?? item.phone_number ?? "Unknown";

const formatPrediction = (value) => {
  if (value === 1 || value === "1") return "Failure Likely";
  if (value === 0 || value === "0") return "Success Likely";
  return String(value ?? "—");
};

const History = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await getHistory();
        setData(res);
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to load history");
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  if (loading) {
    return <p style={styles.message}>Loading history...</p>;
  }

  if (error) {
    return <p style={{ ...styles.message, color: "#ef4444" }}>{error}</p>;
  }

  return (
    <div>
      <h1 style={styles.title}>Prediction History</h1>

      {data.length === 0 ? (
        <p style={styles.message}>No prediction history found.</p>
      ) : (
        <div style={styles.list}>
          {[...data].reverse().map((item) => {
            const phone = getPhoneNumber(item);
            const high = String(item.risk).toLowerCase() === "high";

            return (
              <Link
                key={item.id}
                to={`/route/${encodeURIComponent(phone)}`}
                style={styles.cardLink}
              >
                <div style={styles.card}>
                  <div style={styles.cardHeader}>
                    <span style={styles.phoneLink}>{phone}</span>
                    <span
                      style={{
                        ...styles.riskBadge,
                        color: high ? "#ef4444" : "#16a34a",
                        borderColor: high ? "#fecaca" : "#bbf7d0",
                        background: high ? "#fef2f2" : "#f0fdf4",
                      }}
                    >
                      {String(item.risk).toUpperCase()}
                    </span>
                  </div>
                  <div style={styles.cardRow}>
                    <span style={styles.label}>Prediction</span>
                    <span style={styles.value}>{formatPrediction(item.prediction)}</span>
                  </div>
                  <div style={styles.viewRoute}>
                    📍 View Route
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
};

const styles = {
  title: {
    margin: "0 0 24px",
    fontSize: "1.75rem",
    color: "#1e293b",
  },
  list: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  },
  cardLink: {
    textDecoration: "none",
    color: "inherit",
  },
  card: {
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: "8px",
    padding: "16px 20px",
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    transition: "box-shadow 0.15s, border-color 0.15s",
    cursor: "pointer",
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  phoneLink: {
    color: "#2563eb",
    fontWeight: "700",
    fontSize: "1rem",
    textDecoration: "none",
  },
  riskBadge: {
    fontSize: "0.75rem",
    fontWeight: "700",
    padding: "3px 10px",
    borderRadius: "999px",
    border: "1px solid",
  },
  cardRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  label: {
    color: "#64748b",
    fontSize: "0.875rem",
  },
  value: {
    color: "#1e293b",
    fontWeight: "600",
  },
  viewRoute: {
    marginTop: "4px",
    fontSize: "0.875rem",
    fontWeight: "600",
    color: "#3b82f6",
  },
  message: {
    color: "#64748b",
  },
};

export default History;
