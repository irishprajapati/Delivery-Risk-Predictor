import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
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
  const [searchParams] = useSearchParams();
  const selectedId = searchParams.get("selected");
  const itemRefs = useRef({});

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

  useEffect(() => {
    if (!selectedId || loading || data.length === 0) return;

    const id = Number(selectedId);
    const el = itemRefs.current[id];
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [selectedId, loading, data]);

  if (loading) {
    return <p style={styles.message}>Loading history...</p>;
  }

  if (error) {
    return <p style={{ ...styles.message, color: "#ef4444" }}>{error}</p>;
  }

  const sorted = [...data].sort((a, b) => {
    if (a.created_at && b.created_at) {
      return new Date(b.created_at) - new Date(a.created_at);
    }
    return (b.id ?? 0) - (a.id ?? 0);
  });

  return (
    <div>
      <h1 style={styles.title}>Prediction History</h1>

      {sorted.length === 0 ? (
        <p style={styles.message}>No prediction history found.</p>
      ) : (
        <div style={styles.list}>
          {sorted.map((item, index) => {
            const phone = getPhoneNumber(item);
            const high = String(item.risk).toLowerCase() === "high";
            const isSelected = selectedId && Number(selectedId) === item.id;

            return (
              <Link
                key={item.id}
                ref={(el) => { itemRefs.current[item.id] = el; }}
                to={`/route/prediction/${item.id}`}
                style={styles.cardLink}
              >
                <div
                  style={{
                    ...styles.card,
                    ...(isSelected ? styles.cardSelected : {}),
                  }}
                >
                  <div style={styles.cardHeader}>
                    <div style={styles.cardTitleRow}>
                      <span style={styles.itemNumber}>{index + 1}</span>
                      <span style={styles.phoneLink}>{phone}</span>
                    </div>
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
                  {item.input_data?.pickup_address && (
                    <div style={styles.addressPreview}>
                      {item.input_data.pickup_address} → {item.input_data.delivery_address}
                    </div>
                  )}
                  <div style={styles.viewRoute}>View Route →</div>
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
  cardSelected: {
    borderColor: "#3b82f6",
    boxShadow: "0 0 0 2px rgba(59, 130, 246, 0.2)",
  },
  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  cardTitleRow: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
  },
  itemNumber: {
    width: "26px",
    height: "26px",
    borderRadius: "50%",
    background: "#eff6ff",
    color: "#2563eb",
    fontSize: "0.8rem",
    fontWeight: "700",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    flexShrink: 0,
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
  addressPreview: {
    fontSize: "0.8rem",
    color: "#64748b",
    lineHeight: 1.4,
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
