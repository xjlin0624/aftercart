import React from "react";
export default function StatCard({ title, value }) {
  return (
    <div style={{ background: "#fff", padding: 20, borderRadius: 10, width: 200 }}>
      <p>{title}</p>
      <h2>{value}</h2>
    </div>
  );
}