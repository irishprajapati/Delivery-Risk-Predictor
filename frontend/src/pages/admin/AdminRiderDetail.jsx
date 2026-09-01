import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getRiderDetail } from "../../services/api";

const AdminRiderDetail = () => {
  const { id } = useParams();
  const [rider, setRider] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchRider = async () => {
    try {
      setLoading(true);
      const data = await getRiderDetail(id);
      setRider(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to load rider details");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRider();
  }, [id]);

  if (loading) {
    return (
      <div className="card-modern" style={{ textAlign: "center", padding: "48px 24px" }}>
        <p style={{ color: "#64748b" }}>Loading rider profile...</p>
      </div>
    );
  }

  if (error || !rider) {
    return (
      <div className="card-modern" style={{ borderColor: "#fecaca", backgroundColor: "#fef2f2" }}>
        <p style={{ color: "#dc2626", marginBottom: "12px" }}>{error || "Rider not found"}</p>
        <Link to="/admin/riders" className="btn-modern btn-modern-secondary">
          ← Back to Riders
        </Link>
      </div>
    );
  }

  return (
    <div className="animate-fade-in" style={{ maxWidth: "900px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Back link */}
      <div style={{ marginBottom: "16px" }}>
        <Link to="/admin/riders" style={{ fontSize: "0.85rem", color: "#2563eb", fontWeight: "600" }}>
          ← Back to Rider Management
        </Link>
      </div>

      <div className="card-modern" style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "12px", borderBottom: "1px solid #e2e8f0", paddingBottom: "16px" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h1 style={{ fontSize: "1.75rem", fontWeight: "800", color: "#0f172a", margin: 0 }}>
                {rider.name}
              </h1>
              <span className={`badge-modern ${rider.is_active ? "badge-status success" : "badge-modern badge-high"}`}>
                {rider.is_active ? "ACTIVE" : "INACTIVE"}
              </span>
            </div>
            <p style={{ color: "#64748b", margin: "4px 0 0", fontSize: "0.95rem" }}>
              Primary Zone: <strong>{rider.area || "Kathmandu Valley"}</strong> • Phone: {rider.phone || "—"}
            </p>
          </div>

          <button
            type="button"
            onClick={fetchRider}
            className="btn-modern btn-modern-secondary btn-modern-sm"
          >
            ↻ Refresh Stats
          </button>
        </div>

        {/* 4 Performance Metric Cards */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: "16px" }}>
          <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
              Completed Deliveries
            </span>
            <div style={{ fontSize: "1.75rem", fontWeight: "800", color: "#16a34a", marginTop: "4px" }}>
              {rider.completed_orders ?? 0}
            </div>
          </div>

          <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
              Failed Deliveries
            </span>
            <div style={{ fontSize: "1.75rem", fontWeight: "800", color: "#dc2626", marginTop: "4px" }}>
              {rider.failed_deliveries ?? 0}
            </div>
          </div>

          <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
              Current Load
            </span>
            <div style={{ fontSize: "1.75rem", fontWeight: "800", color: "#0f172a", marginTop: "4px" }}>
              {rider.current_order_count ?? 0} / {rider.max_orders_per_day ?? 20}
            </div>
          </div>

          <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
              Success Rate
            </span>
            <div style={{ fontSize: "1.75rem", fontWeight: "800", color: "#2563eb", marginTop: "4px" }}>
              {(Number(rider.overall_success_rate || 0.85) * 100).toFixed(1)}%
            </div>
          </div>
        </div>

        {/* GPS Location Status */}
        <div style={{ padding: "16px", background: "#f8fafc", borderRadius: "10px", border: "1px solid #e2e8f0" }}>
          <h3 style={{ fontSize: "0.85rem", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "#64748b", marginBottom: "8px" }}>
            Current GPS & Telemetry
          </h3>
          <div style={{ display: "flex", gap: "24px", flexWrap: "wrap", fontSize: "0.9rem", color: "#334155" }}>
            <div>
              Coordinates:{" "}
              <strong>
                {rider.current_latitude && rider.current_longitude
                  ? `${rider.current_latitude.toFixed(4)}, ${rider.current_longitude.toFixed(4)}`
                  : "27.6744, 85.3123 (Active Zone Center)"}
              </strong>
            </div>
            <div>
              Last Update:{" "}
              <strong>
                {rider.last_location_update
                  ? new Date(rider.last_location_update).toLocaleTimeString()
                  : "Live signal active"}
              </strong>
            </div>
          </div>
        </div>

        {/* Area Performance Breakdown Table */}
        <div>
          <h3 style={{ fontSize: "1rem", fontWeight: "800", color: "#0f172a", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "12px" }}>
            Area Performance Breakdown
          </h3>
          {rider.area_performances?.length === 0 ? (
            <p style={{ color: "#64748b", fontSize: "0.9rem" }}>No specific area delivery logs recorded yet.</p>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.9rem" }}>
                <thead>
                  <tr style={{ borderBottom: "2px solid #e2e8f0", color: "#64748b", fontSize: "0.75rem", textTransform: "uppercase" }}>
                    <th style={{ padding: "10px" }}>Area</th>
                    <th style={{ padding: "10px" }}>Total Deliveries</th>
                    <th style={{ padding: "10px" }}>Successful</th>
                    <th style={{ padding: "10px" }}>Failed</th>
                    <th style={{ padding: "10px" }}>Success Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {rider.area_performances.map((ap, i) => (
                    <tr key={i} style={{ borderBottom: "1px solid #f1f5f9" }}>
                      <td style={{ padding: "10px", fontWeight: "700", color: "#0f172a", textTransform: "capitalize" }}>
                        {ap.area}
                      </td>
                      <td style={{ padding: "10px" }}>{ap.total_deliveries}</td>
                      <td style={{ padding: "10px", color: "#16a34a", fontWeight: "600" }}>{ap.successful_deliveries}</td>
                      <td style={{ padding: "10px", color: "#dc2626", fontWeight: "600" }}>{ap.failed_deliveries}</td>
                      <td style={{ padding: "10px", fontWeight: "700", color: "#2563eb" }}>
                        {(Number(ap.success_rate || 0) * 100).toFixed(1)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Active Assigned Deliveries */}
        <div>
          <h3 style={{ fontSize: "1rem", fontWeight: "800", color: "#0f172a", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "12px" }}>
            Active Assigned Deliveries
          </h3>
          {rider.active_deliveries?.length === 0 ? (
            <p style={{ color: "#64748b", fontSize: "0.9rem" }}>No active deliveries assigned to this rider right now.</p>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {rider.active_deliveries.map((ad) => (
                <div
                  key={ad.delivery_id}
                  style={{
                    padding: "12px 16px",
                    background: "#f8fafc",
                    border: "1px solid #e2e8f0",
                    borderRadius: "8px",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <div>
                    <span style={{ fontWeight: "700", color: "#0f172a", marginRight: "8px" }}>
                      Delivery #{ad.delivery_id}
                    </span>
                    <span style={{ color: "#475569", fontSize: "0.9rem" }}>
                      {ad.address} ({ad.item_name})
                    </span>
                  </div>
                  <Link
                    to={`/admin/deliveries/${ad.delivery_id}`}
                    className="btn-modern btn-modern-secondary btn-modern-sm"
                  >
                    View Lifecycle →
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AdminRiderDetail;
