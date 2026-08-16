import React from "react";

const RiskBadge = ({ risk, size = "normal" }) => {
  const normalized = String(risk || "LOW").toUpperCase();

  let className = "badge-modern badge-low";
  if (normalized === "HIGH") {
    className = "badge-modern badge-high";
  } else if (normalized === "MEDIUM" || normalized === "MED") {
    className = "badge-modern badge-medium";
  }

  const isSmall = size === "small";

  return (
    <span
      className={className}
      style={{
        fontSize: isSmall ? "0.7rem" : "0.75rem",
        padding: isSmall ? "2px 8px" : "4px 10px",
      }}
    >
      <span
        style={{
          width: isSmall ? "5px" : "6px",
          height: isSmall ? "5px" : "6px",
          borderRadius: "50%",
          backgroundColor: "currentColor",
          display: "inline-block",
        }}
      />
      {normalized}
    </span>
  );
};

export default RiskBadge;
