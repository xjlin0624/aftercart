import React from "react";
import { NavLink } from "react-router-dom";

const items = [
  { label: "Dashboard", path: "/dashboard", icon: "▦" },
  { label: "My Orders", path: "/orders", icon: "🛒" },
  { label: "Price Alerts", path: "/alerts", icon: "🔔" },
  { label: "Savings Tool", path: "/savings", icon: "〰" },
  { label: "Subscriptions", path: "/subscriptions", icon: "▭" },
  { label: "Settings", path: "/settings", icon: "⚙" },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand-wrap">
        <div className="brand-icon"></div>
        <div className="brand-text">AfterCart</div>
      </div>

      <nav className="sidebar-nav">
        {items.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              isActive ? "sidebar-link active" : "sidebar-link"
            }
          >
            <span className="sidebar-link-icon">{item.icon}</span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="sidebar-bottom-link">ⓘ Support</div>
        <div className="sidebar-bottom-link">⇠ Logout</div>
      </div>
    </aside>
  );
}