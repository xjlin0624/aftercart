import React from "react";
import {
  LineChart,
  Line,
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

export default function PriceLineChart({ data }) {
  return (
    <div className="chart-card">
      <div className="chart-header">
        <div className="section-card-title">Historical Price Tracking</div>
        <button className="ghost-select">Last 7 Days ▾</button>
      </div>

      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 16, right: 8, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#ececec" />
            <XAxis dataKey="day" tick={{ fontSize: 12, fill: "#7b7b7b" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 12, fill: "#7b7b7b" }} axisLine={false} tickLine={false} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="price"
              stroke="#2f2f2f"
              strokeWidth={2.5}
              dot={{ r: 4, fill: "#2f2f2f" }}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}