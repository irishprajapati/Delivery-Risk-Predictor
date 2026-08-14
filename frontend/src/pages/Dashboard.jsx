import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHistory } from "../services/api";

const getPhoneNumber = (item) =>
  item.input_data?.phone_number ?? item.phone_number ?? "Unknown";

const formatRiskLevel = (risk) => {
  if (!risk) return "UNKNOWN";
  return String(risk).toUpperCase();
};

const formatPrediction = (value) => {
  if (value === 1 || value === "1") return "Delivery Failure Likely";
  if (value === 0 || value === "0") return "Delivery Success Likely";
  return "Unknown";
};

const isHighRisk = (risk) => String(risk).toLowerCase() === "high";

const sortByLatest = (items) =>
  [...items].sort((a, b) => {
    if (a.created_at && b.created_at) {
      return new Date(b.created_at) - new Date(a.created_at);
    }
    return (b.id ?? 0) - (a.id ?? 0);
  });

const Dashboard = () => {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const data = await getHistory();
        setHistory(data);
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to load predictions");
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, []);

  const sorted = sortByLatest(history);
  const latest = sorted[0] ?? null;
  const recentHistory = sorted.slice(1);

  if (loading) {
    return (
      <div style={styles.page}>
        <p style={styles.message}>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.page}>
        <p style={{ ...styles.message, color: "#ef4444" }}>{error}</p>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <h1 style={styles.title}>Dashboard</h1>

      <div style={styles.layout}>
        <section style={styles.leftPanel}>
          <h2 style={styles.panelHeading}>Latest Prediction</h2>

          {!latest ? (
            <div style={styles.mainCard}>
              <div style={styles.emptyMain}>
                <p style={styles.emptyTitle}>No predictions yet</p>
                <p style={styles.emptyText}>
                  Run a prediction from the Predict page to see results here.
                </p>
              </div>
            </div>
          ) : (
            <div style={styles.mainCard}>
              <div style={styles.mainContent}>
                <div style={styles.mainField}>
                  <span style={styles.mainLabel}>Phone Number</span>
                  <span style={styles.mainPhone}>{getPhoneNumber(latest)}</span>
                </div>

                <div style={styles.mainField}>
                  <span style={styles.mainLabel}>Risk Level</span>
                  <span
                    style={{
                      ...styles.mainRisk,
                      color: isHighRisk(latest.risk) ? "#ef4444" : "#16a34a",
                    }}
                  >
                    {formatRiskLevel(latest.risk)}
                  </span>
                </div>

                <div style={styles.mainField}>
                  <span style={styles.mainLabel}>Prediction Result</span>
                  <span style={styles.mainPrediction}>
                    {formatPrediction(latest.prediction)}
                  </span>
                </div>

                <Link
                  to={`/history?selected=${latest.id}`}
                  style={styles.viewLink}
                >
                  View in History →
                </Link>
              </div>
            </div>
          )}
        </section>

        <aside style={styles.rightPanel}>
          <h2 style={styles.panelHeading}>Recent History</h2>

          <div style={styles.historyCard}>
            {recentHistory.length === 0 ? (
              <p style={styles.emptyHistory}>
                {latest ? "No previous predictions." : "No history available."}
              </p>
            ) : (
              <ul style={styles.historyList}>
                {recentHistory.map((item, index) => {
                  const high = isHighRisk(item.risk);

                  return (
                    <li key={item.id}>
                      <Link
                        to={`/history?selected=${item.id}`}
                        style={styles.historyItem}
                      >
                        <span style={styles.historyNumber}>{index + 1}</span>
                        <span style={styles.historyPhone}>
                          {getPhoneNumber(item)}
                        </span>
                        <span style={styles.historyArrow}>→</span>
                        <span
                          style={{
                            ...styles.historyRisk,
                            color: high ? "#ef4444" : "#64748b",
                            fontWeight: high ? "700" : "500",
                          }}
                        >
                          {formatRiskLevel(item.risk)}
                        </span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
};

const styles = {
  page: {
    minHeight: "calc(100vh - 120px)",
    display: "flex",
    flexDirection: "column",
  },
  title: {
    margin: "0 0 24px",
    fontSize: "1.75rem",
    color: "#1e293b",
    fontWeight: "600",
  },
  layout: {
    display: "flex",
    gap: "24px",
    flex: 1,
    alignItems: "stretch",
    minHeight: "480px",
  },
  leftPanel: {
    flex: "0 0 70%",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    background: "#f1f5f9",
    borderRadius: "12px",
    padding: "20px",
  },
  rightPanel: {
    flex: "0 0 calc(30% - 24px)",
    display: "flex",
    flexDirection: "column",
    gap: "12px",
    background: "#eef2f7",
    borderRadius: "12px",
    padding: "20px",
    minWidth: "220px",
  },
  panelHeading: {
    margin: 0,
    fontSize: "0.875rem",
    fontWeight: "600",
    color: "#64748b",
    textTransform: "uppercase",
    letterSpacing: "0.04em",
  },
  mainCard: {
    flex: 1,
    background: "#ffffff",
    borderRadius: "10px",
    boxShadow: "0 4px 12px rgba(15, 23, 42, 0.08)",
    border: "1px solid #e2e8f0",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "40px 32px",
    minHeight: "360px",
  },
  mainContent: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "28px",
    textAlign: "center",
    width: "100%",
    maxWidth: "420px",
  },
  mainField: {
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  mainLabel: {
    fontSize: "0.8rem",
    fontWeight: "600",
    color: "#94a3b8",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  mainPhone: {
    fontSize: "1.75rem",
    fontWeight: "700",
    color: "#1e293b",
    letterSpacing: "0.02em",
  },
  mainRisk: {
    fontSize: "2.25rem",
    fontWeight: "800",
    letterSpacing: "0.04em",
  },
  mainPrediction: {
    fontSize: "1.125rem",
    fontWeight: "600",
    color: "#334155",
  },
  viewLink: {
    marginTop: "8px",
    fontSize: "0.875rem",
    fontWeight: "600",
    color: "#3b82f6",
    textDecoration: "none",
  },
  emptyMain: {
    textAlign: "center",
  },
  emptyTitle: {
    margin: "0 0 8px",
    fontSize: "1.125rem",
    fontWeight: "600",
    color: "#475569",
  },
  emptyText: {
    margin: 0,
    fontSize: "0.95rem",
    color: "#94a3b8",
    maxWidth: "280px",
  },
  historyCard: {
    flex: 1,
    background: "#ffffff",
    borderRadius: "10px",
    boxShadow: "0 2px 8px rgba(15, 23, 42, 0.06)",
    border: "1px solid #e2e8f0",
    padding: "12px",
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
  },
  historyList: {
    listStyle: "none",
    margin: 0,
    padding: 0,
    overflowY: "auto",
    maxHeight: "360px",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  },
  historyItem: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "10px 12px",
    background: "#f8fafc",
    borderRadius: "6px",
    border: "1px solid #f1f5f9",
    fontSize: "0.875rem",
    textDecoration: "none",
    color: "inherit",
    cursor: "pointer",
    transition: "background 0.15s, border-color 0.15s",
  },
  historyNumber: {
    flexShrink: 0,
    width: "22px",
    height: "22px",
    borderRadius: "50%",
    background: "#e2e8f0",
    color: "#475569",
    fontSize: "0.75rem",
    fontWeight: "700",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
  historyPhone: {
    fontWeight: "600",
    color: "#1e293b",
    flex: 1,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  historyArrow: {
    color: "#cbd5e1",
    flexShrink: 0,
  },
  historyRisk: {
    flexShrink: 0,
    fontSize: "0.8rem",
  },
  emptyHistory: {
    margin: 0,
    padding: "16px 8px",
    fontSize: "0.875rem",
    color: "#94a3b8",
    textAlign: "center",
  },
  message: {
    color: "#64748b",
  },
};

export default Dashboard;
