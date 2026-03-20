import React from "react";
export default function AlertCard({ title, desc }) {
  return (
    <div style={{ border: "1px solid #ddd", padding: 10, marginTop: 10 }}>
      <strong>{title}</strong>
      <p>{desc}</p>
    </div>
  );
}