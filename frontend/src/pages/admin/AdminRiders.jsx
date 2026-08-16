import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getRiders } from "../../services/api";

const AdminRiders = () => {
  const navigate = useNavigate();
  const [riders, setRiders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchRidersList = async () => {
    try {
      setLoading(true);
      const data = await getRiders();
      setRiders(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load riders");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRidersList();
  }, []);

  return (
    <div className="animate-fade-in" style={{ maxWidth: "1000px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Title */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Fleet & Dispatch Capacity
          </span>
          <h1 style={{ fontSize: "1.85rem", fontWeight: "800", color: "#0f172a", marginTop: "2px" }}>
            RIDER MANAGEMENT
          </h1>
        </div>

        <button
          type="button"
          onClick={fetchRidersList}
          className="btn-modern btn-modern-secondary btn-modern-sm"
        >
          ↻ Refresh Fleet
        </button>
      </div>

      {error && (
        <div style={{ padding: "14px", background: "#fef2f2", color: "#dc2626", borderRadius: "8px", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {loading ? (
        <p style={{ textAlign: "center", padding: "48px", color: "#64748b" }}>Loading riders fleet...</p>
      ) : riders.length === 0 ? (
        <div className="card-modern" style={{ textAlign: "center", padding: "48px" }}>
          <p style={{ color: "#64748b" }}>No riders registered in the fleet.</p>
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
            gap: "20px",
          }}
        >
          {riders.map((rider) => {
            const currentOrders = rider.current_order_count || 0;
            const maxOrders = rider.max_orders_per_day || 20;
            const loadPercent = Math.min(100, (currentOrders / maxOrders) * 100);
            const successPct = `${(Number(rider.overall_success_rate || 0.85) * 100).toFixed(1)}%`;

            return (
              <div
                key={rider.id}
                className="card-modern card-modern-hover"
                style={{ cursor: "pointer", display: "flex", flexDirection: "column", gap: "14px" }}
                onClick={() => navigate(`/admin/riders/${rider.id}`)}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                  <div>
                    <h2 style={{ fontSize: "1.25rem", fontWeight: "800", color: "#0f172a", margin: 0 }}>
                      {rider.name}
                    </h2>
                    <span style={{ fontSize: "0.85rem", color: "#64748b", fontWeight: "500" }}>
                      📍 {rider.area || "Kathmandu Valley"}
                    </span>
                  </div>

                  <span
                    className={`badge-modern ${
                      rider.is_active ? "badge-status success" : "badge-modern badge-high"
                    }`}
                  >
                    {rider.is_active ? "ACTIVE" : "INACTIVE"}
                  </span>
                </div>

                {/* Capacity progress */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: "4px" }}>
                    <span style={{ color: "#64748b" }}>Workload</span>
                    <strong style={{ color: "#0f172a" }}>
                      {currentOrders} / {maxOrders} orders
                    </strong>
                  </div>
                  <div style={{ height: "6px", background: "#e2e8f0", borderRadius: "999px", overflow: "hidden" }}>
                    <div
                      style={{
                        height: "100%",
                        width: `${loadPercent}%`,
                        backgroundColor: loadPercent > 80 ? "#ef4444" : "#2563eb",
                        borderRadius: "999px",
                      }}
                    />
                  </div>
                </div>

                {/* Success Rate */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: "10px", borderTop: "1px solid #f1f5f9" }}>
                  <span style={{ fontSize: "0.85rem", color: "#64748b" }}>Success Rate</span>
                  <span style={{ fontSize: "1.1rem", fontWeight: "800", color: "#16a34a" }}>
                    {successPct}
                  </span>
                </div>

                <div style={{ textAlign: "right", marginTop: "2px" }}>
                  <span style={{ fontSize: "0.8rem", color: "#2563eb", fontWeight: "600" }}>
                    View Performance →
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default AdminRiders;
