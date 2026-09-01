import React from "react";

const STEPS = [
  { key: "placed", label: "Placed" },
  { key: "assigned", label: "Assigned" },
  { key: "picked_up", label: "Picked Up" },
  { key: "out_for_delivery", label: "Out for Delivery" },
  { key: "delivered", label: "Delivered" },
];

const getStepIndex = (status) => {
  const s = String(status || "").toLowerCase().trim();
  switch (s) {
    case "placed":
      return 0;
    case "assigned":
      return 1;
    case "picked_up":
    case "started":
      return 2;
    case "out_for_delivery":
      return 3;
    case "delivered":
    case "completed":
      return 4;
    case "failed":
    case "unreachable":
    case "cancelled":
      return -1; // special failed state
    default:
      return 0;
  }
};

const StatusTimeline = ({ status, compact = false }) => {
  const currentIndex = getStepIndex(status);
  const isFailed = currentIndex === -1;

  if (compact) {
    return (
      <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
        {STEPS.map((step, idx) => {
          const isDone = !isFailed && idx < currentIndex;
          const isCurrent = !isFailed && idx === currentIndex;

          let color = "#94a3b8";
          let bg = "#f1f5f9";
          let border = "#e2e8f0";

          if (isDone) {
            color = "#16a34a";
            bg = "#f0fdf4";
            border = "#bbf7d0";
          } else if (isCurrent) {
            color = "#2563eb";
            bg = "#eff6ff";
            border = "#bfdbfe";
          }

          return (
            <React.Fragment key={step.key}>
              <span
                style={{
                  fontSize: "0.75rem",
                  fontWeight: isCurrent ? "700" : "500",
                  color: color,
                  backgroundColor: bg,
                  border: `1px solid ${border}`,
                  padding: "2px 8px",
                  borderRadius: "4px",
                }}
              >
                {step.label}
              </span>
              {idx < STEPS.length - 1 && (
                <span style={{ color: "#cbd5e1", fontSize: "0.75rem" }}>→</span>
              )}
            </React.Fragment>
          );
        })}
        {isFailed && (
          <span
            style={{
              fontSize: "0.75rem",
              fontWeight: "700",
              color: "#dc2626",
              backgroundColor: "#fef2f2",
              border: "1px solid #fecaca",
              padding: "2px 8px",
              borderRadius: "4px",
            }}
          >
            {String(status).toUpperCase()}
          </span>
        )}
      </div>
    );
  }

  const progressPercent = isFailed
    ? 0
    : Math.max(0, Math.min(100, (currentIndex / (STEPS.length - 1)) * 100));

  return (
    <div style={{ margin: "24px 0 16px" }}>
      <div className="timeline-track">
        <div className="timeline-line">
          <div
            className="timeline-progress"
            style={{ width: `${progressPercent}%` }}
          />
        </div>

        {STEPS.map((step, index) => {
          const isCompleted = !isFailed && index < currentIndex;
          const isCurrent = !isFailed && index === currentIndex;

          let stepClass = "timeline-step";
          if (isCompleted) stepClass += " completed";
          if (isCurrent) stepClass += " current";

          return (
            <div key={step.key} className={stepClass}>
              <div className="timeline-dot">
                {index + 1}
              </div>
              <span className="timeline-label">{step.label}</span>
            </div>
          );
        })}
      </div>

      {isFailed && (
        <div
          style={{
            marginTop: "12px",
            padding: "8px 12px",
            background: "#fef2f2",
            border: "1px solid #fecaca",
            borderRadius: "6px",
            color: "#dc2626",
            fontSize: "0.85rem",
            fontWeight: "600",
            textAlign: "center",
          }}
        >
          Delivery Status: {String(status).toUpperCase()}
        </div>
      )}
    </div>
  );
};

export default StatusTimeline;
