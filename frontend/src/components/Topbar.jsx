import React from "react";
import { useLocation } from "react-router-dom";

function getPageTitle(pathname) {
  if (pathname === "/dashboard") return "Overview";
  if (pathname === "/orders") return "My Orders";
  if (pathname === "/alerts") return "Price Alerts";
  if (pathname === "/savings") return "Savings Tool";
  if (pathname === "/subscriptions") return "Subscriptions";
  if (pathname === "/settings") return "Settings";
  return "Overview";
}

export default function Topbar() {
  const location = useLocation();
  const pageTitle = getPageTitle(location.pathname);

  return (
    <header className="topbar">
      <div className="topbar-title">{pageTitle}</div>

      <div className="topbar-right">
        <div className="search-wrap">
          <span className="search-icon">⌕</span>
          <input
            className="search-input"
            placeholder="Search orders or stores..."
          />
        </div>

        <div className="profile-wrap">
          <div className="profile-text">
            <div className="profile-name">Alex Johnson</div>
            <div className="profile-sub">Premium Member</div>
          </div>
          <div className="profile-avatar">⍟</div>
        </div>
      </div>
    </header>
  );
}