import { useEffect, useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import {
  getAdminDeliveries,
  getDeliveryRiderOptions,
  assignDeliveryRider,
  getDeliverySummary,
  getErrorMessage,
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
  const [showAllRiders, setShowAllRiders] = useState(false);

  // Fetch all deliveries for the selector dropdown
  useEffect(() => {
    const fetchDeliveriesList = async () => {
      try {
        const list = await getAdminDeliveries();
        setDeliveries(list);

        if (!selectedDeliveryId && list.length > 0) {
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
        }
      } catch (err) {
        setError(getErrorMessage(err, "Failed to load dispatch candidates"));
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
      setError(getErrorMessage(err, "Failed to assign rider"));
    } finally {
      setAssigning(false);
    }
  };

  const topCandidate = candidates[0] || null;

  const getCandidateLoad = (c) => c?.details?.workload?.current_orders ?? c?.current_order_count ?? 0;
  const getCandidateCapacity = (c) => c?.details?.workload?.capacity ?? c?.max_orders_per_day ?? 20;
  const getCandidateSuccess = (c) => c?.details?.overall_performance?.success_rate ?? c?.overall_success_rate ?? 0.85;
  const getCandidateAreaMatch = (c) => c?.details?.area_match?.matched ?? c?.area_match ?? false;
  const getCandidateScore = (c) => Number(c?.score ?? c?.final_score ?? 0).toFixed(2);

  return (
    <div className="animate-fade-in" style={{ maxWidth: "1000px", margin: "0 auto", paddingBottom: "48px" }}>
      {/* Title */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <h1 style={{ fontSize: "1.65rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
            Rider Dispatch Engine
          </h1>
          <p style={{ fontSize: "0.875rem", color: "#64748b", margin: "3px 0 0" }}>
            Operational Multi-Criteria Decision Ranking (Workload, Area Match, Reliability, Proximity)
          </p>
        </div>

        <Link to="/admin/dashboard" style={{ fontSize: "0.85rem", color: "#2563eb", fontWeight: "600" }}>
          ← Back to Dashboard
        </Link>
      </div>

      {error && (
        <div style={{ padding: "12px 16px", background: "#fef2f2", color: "#dc2626", borderRadius: "8px", border: "1px solid #fecaca", marginBottom: "16px" }}>
          {error}
        </div>
      )}

      {successMsg && (
        <div style={{ padding: "12px 16px", background: "#f0fdf4", color: "#16a34a", borderRadius: "8px", border: "1px solid #bbf7d0", marginBottom: "16px", fontWeight: "600" }}>
          {successMsg}
        </div>
      )}

      {/* Delivery Selector Bar */}
      <div className="card-modern" style={{ padding: "14px 20px", marginBottom: "20px", display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap" }}>
        <span style={{ fontSize: "0.875rem", fontWeight: "700", color: "#0f172a" }}>
          Select Delivery:
        </span>

        <select
          className="form-control-modern"
          style={{ width: "auto", minWidth: "320px", fontSize: "0.875rem" }}
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

      {/* Selected Delivery Context Banner */}
      {deliveryInfo && (
        <div
          className="card-modern"
          style={{
            marginBottom: "20px",
            padding: "18px 22px",
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
              <h2 style={{ fontSize: "1.25rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
                DELIVERY #{deliveryInfo.delivery_id} (Order #{deliveryInfo.order_id})
              </h2>
              <span className="badge-modern badge-status active">
                {String(deliveryInfo.status).replace(/_/g, " ")}
              </span>
            </div>
            <p style={{ margin: "4px 0 0", color: "#475569", fontSize: "0.875rem" }}>
              Address: {deliveryInfo.order?.address || "Delivery Address"}
            </p>
          </div>

          <div style={{ display: "flex", gap: "20px", alignItems: "center" }}>
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
              <div style={{ fontSize: "1.05rem", fontWeight: "700", color: "#0f172a" }}>
                {deliveryInfo.order?.area || "Kathmandu"}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Recommended Rider Section */}
      {topCandidate && (
        <div
          className="card-modern"
          style={{
            marginBottom: "20px",
            padding: "24px",
            background: "#eff6ff",
            border: "1px solid #bfdbfe",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "12px", borderBottom: "1px solid #dbeafe", paddingBottom: "16px", marginBottom: "16px" }}>
            <div>
              <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#1e40af", background: "#dbeafe", padding: "2px 8px", borderRadius: "4px", textTransform: "uppercase" }}>
                Top Recommended Candidate
              </span>
              <h2 style={{ fontSize: "1.35rem", fontWeight: "700", color: "#0f172a", margin: "4px 0 0" }}>
                {topCandidate.rider_name || topCandidate.name || `Rider ${topCandidate.rider_id}`}
              </h2>
              <span style={{ fontSize: "0.85rem", color: "#3b82f6", display: "block", marginTop: "2px" }}>
                Highest multi-criteria composite score ({getCandidateScore(topCandidate)}) for {deliveryInfo?.risk_level || "this"} risk.
              </span>
            </div>

            <button
              type="button"
              disabled={assigning}
              onClick={() => handleAssign(topCandidate.rider_id || topCandidate.id)}
              className="btn-modern btn-modern-primary btn-modern-lg"
            >
              {assigning ? "Assigning..." : `Assign Recommended Rider (${topCandidate.rider_name || topCandidate.name || "Rider"})`}
            </button>
          </div>

          {/* Metrics Grid */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "12px" }}>
            <div style={{ background: "#ffffff", padding: "10px 14px", borderRadius: "8px", border: "1px solid #bfdbfe" }}>
              <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Current Load</span>
              <div style={{ fontSize: "1.1rem", fontWeight: "700", color: "#0f172a" }}>
                {getCandidateLoad(topCandidate)} / {getCandidateCapacity(topCandidate)}
              </div>
            </div>

            <div style={{ background: "#ffffff", padding: "10px 14px", borderRadius: "8px", border: "1px solid #bfdbfe" }}>
              <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Overall Success</span>
              <div style={{ fontSize: "1.1rem", fontWeight: "700", color: "#16a34a" }}>
                {(Number(getCandidateSuccess(topCandidate)) * 100).toFixed(1)}%
              </div>
            </div>

            <div style={{ background: "#ffffff", padding: "10px 14px", borderRadius: "8px", border: "1px solid #bfdbfe" }}>
              <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Area Match</span>
              <div style={{ fontSize: "1.1rem", fontWeight: "700", color: getCandidateAreaMatch(topCandidate) ? "#16a34a" : "#64748b" }}>
                {getCandidateAreaMatch(topCandidate) ? "Yes" : "No"}
              </div>
            </div>

            <div style={{ background: "#ffffff", padding: "10px 14px", borderRadius: "8px", border: "1px solid #bfdbfe" }}>
              <span style={{ fontSize: "0.75rem", color: "#64748b" }}>Assignment Score</span>
              <div style={{ fontSize: "1.1rem", fontWeight: "700", color: "#2563eb" }}>
                {getCandidateScore(topCandidate)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Ranked Eligible Riders Table (Secondary / Collapsible or Full) */}
      <div className="card-modern" style={{ padding: "20px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
          <div>
            <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#0f172a", margin: 0 }}>
              All Eligible Riders (Ranking Breakdown)
            </h3>
            <span style={{ fontSize: "0.825rem", color: "#64748b" }}>
              Riders evaluated by multi-criteria optimization weights
            </span>
          </div>

          <button
            type="button"
            onClick={() => setShowAllRiders(!showAllRiders)}
            style={{
              background: "none",
              border: "none",
              color: "#2563eb",
              fontSize: "0.85rem",
              fontWeight: "600",
              cursor: "pointer",
            }}
          >
            {showAllRiders ? "▲ Hide Details" : "▼ View All Eligible Riders"}
          </button>
        </div>

        {loading ? (
          <p style={{ textAlign: "center", padding: "30px", color: "#64748b" }}>
            Evaluating eligible rider rankings...
          </p>
        ) : candidates.length === 0 ? (
          <p style={{ textAlign: "center", padding: "30px", color: "#64748b" }}>
            No eligible riders active in the fleet for this delivery.
          </p>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.875rem" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e2e8f0", color: "#64748b", fontSize: "0.75rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                  <th style={{ padding: "10px 12px" }}>Rider</th>
                  <th style={{ padding: "10px 12px" }}>Current Load</th>
                  <th style={{ padding: "10px 12px" }}>Overall Success</th>
                  <th style={{ padding: "10px 12px" }}>Area Match</th>
                  <th style={{ padding: "10px 12px" }}>Score</th>
                  <th style={{ padding: "10px 12px", textAlign: "right" }}>Manual Override</th>
                </tr>
              </thead>
              <tbody>
                {candidates.map((c, index) => {
                  const isRec = index === 0;
                  const load = `${getCandidateLoad(c)} / ${getCandidateCapacity(c)}`;
                  const successPct = `${(Number(getCandidateSuccess(c)) * 100).toFixed(1)}%`;
                  const scoreVal = getCandidateScore(c);
                  const isAreaMatch = getCandidateAreaMatch(c);

                  return (
                    <tr
                      key={c.rider_id || c.id || index}
                      style={{
                        borderBottom: "1px solid #f1f5f9",
                        backgroundColor: isRec ? "#f0fdf4" : "transparent",
                      }}
                    >
                      <td style={{ padding: "12px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <span style={{ fontWeight: "700", color: "#0f172a" }}>
                            {c.rider_name || c.name || `Rider ${c.rider_id}`}
                          </span>
                          {isRec && (
                            <span className="badge-modern badge-status success" style={{ fontSize: "0.7rem", padding: "1px 6px" }}>
                              Recommended
                            </span>
                          )}
                        </div>
                        <span style={{ fontSize: "0.75rem", color: "#64748b" }}>
                          Zone: {c.rider_area || "General"}
                        </span>
                      </td>

                      <td style={{ padding: "12px", fontWeight: "600", color: "#334155" }}>
                        {load}
                      </td>

                      <td style={{ padding: "12px", fontWeight: "600", color: "#16a34a" }}>
                        {successPct}
                      </td>

                      <td style={{ padding: "12px" }}>
                        <span style={{ fontWeight: "600", color: isAreaMatch ? "#16a34a" : "#64748b" }}>
                          {isAreaMatch ? "Yes" : "No"}
                        </span>
                      </td>

                      <td style={{ padding: "12px", fontWeight: "700", color: isRec ? "#16a34a" : "#0f172a" }}>
                        {scoreVal}
                      </td>

                      <td style={{ padding: "12px", textAlign: "right" }}>
                        <button
                          type="button"
                          disabled={assigning}
                          onClick={() => handleAssign(c.rider_id || c.id)}
                          className={`btn-modern btn-modern-sm ${
                            isRec ? "btn-modern-primary" : "btn-modern-secondary"
                          }`}
                          style={{ padding: "4px 10px", fontSize: "0.775rem" }}
                        >
                          {assigning ? "..." : isRec ? "Assign Top" : "Override Assign"}
                        </button>
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

export default AdminDispatch;
