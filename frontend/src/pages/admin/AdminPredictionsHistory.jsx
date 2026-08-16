import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getHistory } from "../../services/api";
import RiskBadge from "../../components/RiskBadge";

const AdminPredictionsHistory = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const res = await getHistory();
      setData(res);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load prediction history");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const formatDate = (dateStr) => {
    if (!dateStr) return "—";
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="animate-fade-in" style={{ maxWidth: "1080px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Title */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Model Inference Logs
          </span>
          <h1 style={{ fontSize: "1.85rem", fontWeight: "800", color: "#0f172a", marginTop: "2px" }}>
            PREDICTION HISTORY
          </h1>
        </div>

        <div style={{ display: "flex", gap: "10px" }}>
          <button
            type="button"
            onClick={fetchHistory}
            className="btn-modern btn-modern-secondary btn-modern-sm"
          >
            ↻ Refresh History
          </button>
          <Link to="/admin/prediction" className="btn-modern btn-modern-primary btn-modern-sm">
            ⚡ New Prediction
          </Link>
        </div>
      </div>

      {error && (
        <div style={{ padding: "14px", background: "#fef2f2", color: "#dc2626", borderRadius: "8px", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      <div className="card-modern" style={{ padding: "20px" }}>
        {loading ? (
          <p style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>Loading prediction inference logs...</p>
        ) : data.length === 0 ? (
          <div style={{ textAlign: "center", padding: "48px", color: "#64748b" }}>
            <p style={{ marginBottom: "16px" }}>No predictions recorded in the database yet.</p>
            <Link to="/admin/prediction" className="btn-modern btn-modern-primary">
              Run First Prediction →
            </Link>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.925rem" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e2e8f0", color: "#64748b", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  <th style={{ padding: "12px" }}>Prediction ID</th>
                  <th style={{ padding: "12px" }}>Order / Phone</th>
                  <th style={{ padding: "12px" }}>Probability</th>
                  <th style={{ padding: "12px" }}>Risk</th>
                  <th style={{ padding: "12px" }}>Date</th>
                  <th style={{ padding: "12px", textAlign: "right" }}>Route Details</th>
                </tr>
              </thead>
              <tbody>
                {data.map((item) => {
                  const prob = item.probability != null ? `${(Number(item.probability) * 100).toFixed(1)}%` : "—";
                  const phone = item.input_data?.phone_number || item.phone_number || (item.order_id ? `#${item.order_id}` : "—");

                  return (
                    <tr
                      key={item.id}
                      style={{ borderBottom: "1px solid #f1f5f9", transition: "background 0.15s" }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = "#f8fafc")}
                      onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                    >
                      <td style={{ padding: "14px 12px", fontWeight: "700", color: "#0f172a" }}>
                        #{item.id}
                      </td>
                      <td style={{ padding: "14px 12px", color: "#334155" }}>
                        {item.order_id ? (
                          <span style={{ fontWeight: "700" }}>Order #{item.order_id}</span>
                        ) : (
                          <span>{phone}</span>
                        )}
                      </td>
                      <td style={{ padding: "14px 12px", fontWeight: "700", color: "#0f172a" }}>
                        {prob}
                      </td>
                      <td style={{ padding: "14px 12px" }}>
                        <RiskBadge risk={item.risk} size="small" />
                      </td>
                      <td style={{ padding: "14px 12px", color: "#64748b", fontSize: "0.85rem" }}>
                        {formatDate(item.created_at)}
                      </td>
                      <td style={{ padding: "14px 12px", textAlign: "right" }}>
                        <Link
                          to={`/route/prediction/${item.id}`}
                          className="btn-modern btn-modern-secondary btn-modern-sm"
                          style={{ padding: "4px 10px", fontSize: "0.775rem" }}
                        >
                          View Map & Route →
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminPredictionsHistory;
