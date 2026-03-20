import React from "react";
import { alerts } from "../mockData";

export default function Alerts() {
  return (
    <div>
      <h2>Alerts</h2>
      {alerts.map(a => <div key={a.id}>{a.title}</div>)}
    </div>
  );
}