import React from "react";
import { Link } from "react-router-dom";

export default function Sidebar() {
  return (
    <div style={{ width: 200, background: "#111", color: "#fff", height: "100vh", padding: 20 }}>
      <h3>P.U.R.</h3>
      <Link to="/" style={link}>Dashboard</Link>
      <Link to="/orders" style={link}>Orders</Link>
      <Link to="/alerts" style={link}>Alerts</Link>
      <Link to="/settings" style={link}>Settings</Link>
    </div>
  );
}

const link = { display: "block", color: "#fff", padding: "10px 0" };