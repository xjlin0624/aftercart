import React from "react";

export default function StatCard({ title, value, trend, positive = true }) {
  return (
    <div className="stat-card">
      <div className="stat-title">{title}</div>
      <div className="stat-row">
        <div className="stat-value">{value}</div>
        <div className={positive ? "trend-positive" : "trend-negative"}>
          {positive ? "↗ " : "↘ "}
          {trend}
        </div>
      </div>
    </div>
  );
}