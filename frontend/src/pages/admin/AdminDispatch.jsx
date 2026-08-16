import { useEffect, useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import {
  getAdminDeliveries,
  getDeliveryRiderOptions,
  assignDeliveryRider,
  getDeliverySummary,
} from "../../services/api";
import RiskBadge from "../../components/RiskBadge";

const AdminDispatch = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const deliveryIdParam = searchParams.get("deliveryId");

  const [deliveries, setDeliveries] = useState([]);
  const [selectedDeliveryId, setSelectedDeliveryId] = useState(deliveryIdParam || "");
  const [deliveryInfo, setDeliveryInfo] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [assigning, setAssigning] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Fetch all deliveries for the selector dropdown
  useEffect(() => {
    const fetchDeliveriesList = async () => {
      try {
        const list = await getAdminDeliveries();
        setDeliveries(list);

        if (!selectedDeliveryId && list.length > 0) {
          // Default to first unassigned delivery, or first delivery
          const unassigned = list.find((d) => d.status === "unassigned");
          const targetId = unassigned ? unassigned.delivery_id : list[0].delivery_id;
          setSelectedDeliveryId(String(targetId));
          setSearchParams({ deliveryId: String(targetId) });
        }
      } catch (err) {
        console.warn("Could not load deliveries list:", err);
      }
    };

    fetchDeliveriesList();
  }, []);

  // Fetch ranked candidates for the selected delivery
  useEffect(() => {
    if (!selectedDeliveryId) return;

    const fetchCandidates = async () => {
      try {
        setLoading(true);
        setError("");
        setSuccessMsg("");

        const [summary, options] = await Promise.allSettled([
          getDeliverySummary(selectedDeliveryId),
          getDeliveryRiderOptions(selectedDeliveryId),
        ]);

        if (summary.status === "fulfilled") {
          setDeliveryInfo(summary.value);
        }

        if (options.status === "fulfilled") {
          setCandidates(options.value.candidates || []);
        } else {
          setCandidates([]);
          console.warn("Rider options not available:", options.reason);
        }
      } catch (err) {
        setError(err.response?.data?.detail || "Failed to load dispatch candidates");
      } finally {
        setLoading(false);
      }
    };

    fetchCandidates();
  }, [selectedDeliveryId]);

  const handleSelectDelivery = (id) => {
    setSelectedDeliveryId(id);
    setSearchParams({ deliveryId: id });
  };

  const handleAssign = async (riderId = null) => {
    if (!selectedDeliveryId) return;
    try {
      setAssigning(true);
      setError("");

      const res = await assignDeliveryRider(selectedDeliveryId, riderId);
      setSuccessMsg(res.message || "Rider assigned successfully!");

      setTimeout(() => {
        navigate(`/admin/deliveries/${selectedDeliveryId}`);
      }, 1200);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to assign rider");
    } finally {
      setAssigning(false);
    }
  };

  const topCandidate = candidates[0];

  return (
    <div className="animate-fade-in" style={{ maxWidth: "1000px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Title */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <span style={{ fontSize: "0.8rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Multi-Criteria Decision Ranking
          </span>
          <h1 style={{ fontSize: "1.85rem", fontWeight: "800", color: "#0f172a", marginTop: "2px" }}>
            DELIVERY DISPATCH
          </h1>
        </div>

        <Link to="/admin/dashboard" style={{ fontSize: "0.85rem", color: "#2563eb", fontWeight: "600" }}>
          ← Back to Operations
        </Link>
      </div>

      {error && (
        <div style={{ padding: "14px", background: "#fef2f2", color: "#dc2626", borderRadius: "8px", marginBottom: "20px" }}>
          {error}
        </div>
      )}

      {successMsg && (
        <div style={{ padding: "14px", background: "#f0fdf4", color: "#16a34a", borderRadius: "8px", marginBottom: "20px", fontWeight: "600" }}>
          ✓ {successMsg}
        </div>
      )}

      {/* Delivery Selector Bar */}
      <div className="card-modern" style={{ padding: "16px 20px", marginBottom: "24px", display: "flex", alignItems: "center", gap: "16px", flexWrap: "wrap" }}>
        <span style={{ fontSize: "0.875rem", fontWeight: "700", color: "#0f172a" }}>
          Select Delivery:
        </span>

        <select
          className="form-control-modern"
          style={{ width: "auto", minWidth: "300px", fontSize: "0.9rem" }}
          value={selectedDeliveryId}
          onChange={(e) => handleSelectDelivery(e.target.value)}
        >
          {deliveries.map((d) => (
            <option key={d.delivery_id} value={d.delivery_id}>
              Delivery #{d.delivery_id} (Order #{d.order_id}) — {d.area} [{String(d.status).toUpperCase()}]
            </option>
          ))}
        </select>
      </div>

      {/* Selected Delivery Banner */}
      {deliveryInfo && (
        <div
          className="card-modern"
          style={{
            marginBottom: "24px",
            background: "#f8fafc",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "16px",
          }}
        >
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <h2 style={{ fontSize: "1.35rem", fontWeight: "800", color: "#0f172a", margin: 0 }}>
                DELIVERY #{deliveryInfo.delivery_id} (Order #{deliveryInfo.order_id})
              </h2>
              <span className="badge-modern badge-status active">
                {String(deliveryInfo.status).replace(/_/g, " ")}
              </span>
            </div>
            <p style={{ margin: "4px 0 0", color: "#475569", fontSize: "0.95rem" }}>
              📍 {deliveryInfo.order?.address || "Address"}
            </p>
          </div>

          <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
            <div style={{ textAlign: "right" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
                Risk Profile
              </span>
              <div>
                <RiskBadge risk={deliveryInfo.risk_level || "MEDIUM"} />
              </div>
            </div>

            <div style={{ textAlign: "right" }}>
              <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#64748b", textTransform: "uppercase" }}>
                Area
              </span>
              <div style={{ fontSize: "1.1rem", fontWeight: "700", color: "#0f172a" }}>
                {deliveryInfo.order?.area || "Kathmandu"}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Multi-Criteria Ranked Table */}
      <div className="card-modern">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <div>
            <h2 style={{ fontSize: "1.15rem", fontWeight: "800", color: "#0f172a" }}>
              Eligible Riders & Multi-Criteria Ranking
            </h2>
            <p style={{ fontSize: "0.85rem", color: "#64748b", margin: 0 }}>
              Calculated via proximity, load capacity, overall success rate, and historical area performance weights.
            </p>
          </div>
        </div>

        {loading ? (
          <p style={{ textAlign: "center", padding: "36px", color: "#64748b" }}>
            Evaluating eligible rider ranking scores...
          </p>
        ) : candidates.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px", color: "#64748b" }}>
            <p>No active eligible riders available or delivery already completed.</p>
            <Link to={`/admin/deliveries/${selectedDeliveryId}`} className="btn-modern btn-modern-secondary btn-modern-sm">
              View Delivery Lifecycle →
            </Link>
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.925rem" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e2e8f0", color: "#64748b", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  <th style={{ padding: "12px" }}>Rider</th>
                  <th style={{ padding: "12px" }}>Load</th>
                  <th style={{ padding: "12px" }}>Success Rate</th>
                  <th style={{ padding: "12px" }}>Area Match</th>
                  <th style={{ padding: "12px" }}>Score</th>
                  <th style={{ padding: "12px", textAlign: "right" }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c, index) => {
                  const isRecommended = index === 0;
                  const successPct = `${(Number(c.overall_success_rate || 0.85) * 100).toFixed(1)}%`;
                  const scoreVal = Number(c.score || c.final_score || 0).toFixed(2);
                  const areaMatch = c.area_match ? "YES" : "NO";

                  return (
                    <tr
                      key={c.rider_id || c.id || index}
                      style={{
                        borderBottom: "1px solid #f1f5f9",
                        backgroundColor: isRecommended ? "#f0fdf4" : "transparent",
                      }}
                    >
                      <td style={{ padding: "14px 12px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span style={{ fontWeight: "700", color: "#0f172a" }}>
                            {c.name || c.rider_name || `Rider ${c.rider_id}`}
                          </span>
                          {isRecommended && (
                            <span className="badge-modern badge-status success" style={{ fontSize: "0.7rem" }}>
                              Recommended
                            </span>
                          )}
                        </div>
                        <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                          Zone: {c.rider_area || "General"}
                        </span>
                      </td>

                      <td style={{ padding: "14px 12px", fontWeight: "600", color: "#334155" }}>
                        {c.current_order_count ?? 0} / {c.max_orders_per_day ?? 20}
                      </td>

                      <td style={{ padding: "14px 12px", fontWeight: "600", color: "#16a34a" }}>
                        {successPct}
                      </td>

                      <td style={{ padding: "14px 12px" }}>
                        <span
                          style={{
                            fontWeight: "700",
                            color: areaMatch === "YES" ? "#16a34a" : "#64748b",
                          }}
                        >
                          {areaMatch}
                        </span>
                      </td>

                      <td style={{ padding: "14px 12px" }}>
                        <span
                          style={{
                            fontSize: "1.1rem",
                            fontWeight: "800",
                            color: isRecommended ? "#16a34a" : "#0f172a",
                          }}
                        >
                          {scoreVal}
                        </span>
                      </td>

                      <td style={{ padding: "14px 12px", textAlign: "right" }}>
                        <button
                          type="button"
                          disabled={assigning}
                          onClick={() => handleAssign(c.rider_id || c.id)}
                          className={`btn-modern btn-modern-sm ${
                            isRecommended ? "btn-modern-primary" : "btn-modern-secondary"
                          }`}
                        >
                          {assigning ? "Assigning..." : `Assign ${c.name || "Rider"}`}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Bottom Recommendation CTA */}
            {topCandidate && (
              <div
                style={{
                  marginTop: "24px",
                  padding: "16px 20px",
                  background: "#eff6ff",
                  borderRadius: "10px",
                  border: "1px solid #bfdbfe",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "12px",
                }}
              >
                <div>
                  <strong style={{ color: "#1e40af", display: "block" }}>
                    Algorithm Recommendation
                  </strong>
                  <span style={{ fontSize: "0.875rem", color: "#3b82f6" }}>
                    {topCandidate.name || "Top Rider"} achieves the highest multi-criteria composite score ({Number(topCandidate.score || 0).toFixed(2)}) based on current workload and area reliability.
                  </span>
                </div>

                <button
                  type="button"
                  disabled={assigning}
                  onClick={() => handleAssign(topCandidate.rider_id || topCandidate.id)}
                  className="btn-modern btn-modern-primary btn-modern-lg"
                >
                  {assigning ? "Assigning..." : `Assign ${topCandidate.name || "Top Rider"}`}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDispatch;
