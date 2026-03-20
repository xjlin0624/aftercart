import React from "react";
import StatCard from "../components/StatCard";
import PriceChart from "../components/PriceChart";
import AlertCard from "../components/AlertCard";
import { stats, alerts } from "../mockData";

export default function Dashboard() {
  return (
    <div>
      <h2>Overview</h2>

      <div style={{ display: "flex", gap: 20 }}>
        <StatCard title="Total Saved" value={"$" + stats.totalSaved} />
        <StatCard title="Alerts" value={stats.alerts} />
        <StatCard title="Orders" value={stats.orders} />
      </div>

      <div style={{ display: "flex", marginTop: 30, gap: 20 }}>
        <div style={{ flex: 2, background: "#fff", padding: 20 }}>
          <PriceChart />
        </div>

        <div style={{ flex: 1, background: "#fff", padding: 20 }}>
          {alerts.map(a => (
            <AlertCard key={a.id} title={a.title} desc={a.desc} />
          ))}
        </div>
      </div>
    </div>
  );
}