import React from "react";
import {
  BarChart,
  Bar,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

export default function BarSavingsChart({ data }) {
  return (
    <div className="big-card">
      <div className="section-card-title">Savings by Month</div>
      <div className="section-card-subtitle">
        Track your cumulative savings over time
      </div>

      <div className="bar-chart-wrap">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 16, right: 8, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={true} stroke="#ececec" />
            <XAxis dataKey="month" tick={{ fontSize: 12, fill: "#7b7b7b" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 12, fill: "#7b7b7b" }} axisLine={false} tickLine={false} />
            <Tooltip />
            <Bar dataKey="amount" radius={[6, 6, 0, 0]} fill="#17a84a" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}