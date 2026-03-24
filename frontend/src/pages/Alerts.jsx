import React from "react";
import { alertsCards } from "../mockData";

export default function Alerts() {
  return (
    <div className="page-content">
      <div className="page-helper-row">
        <div className="page-helper-text">
          Get notified when prices drop below your target
        </div>
        <button className="primary-btn">＋ Create New Alert</button>
      </div>

      <div className="pill-tabs">
        <button className="pill-tab active">Active Alerts</button>
        <button className="pill-tab">Triggered Alerts</button>
      </div>

      <div className="three-col-grid alerts-grid">
        {alertsCards.map((item, index) => (
          <div className="alert-card" key={index}>
            <div className="alert-card-top">
              <div className="alert-image-box">{item.icon}</div>
              <div>
                <div className="alert-product">{item.product}</div>
                <div className="alert-store">{item.store}</div>
              </div>
            </div>

            <div className="alert-info-list">
              <div className="alert-info-row">
                <span>〰 Target Price</span>
                <strong>{item.targetPrice}</strong>
              </div>
              <div className="alert-info-row">
                <span>Current Price</span>
                <strong>{item.currentPrice}</strong>
              </div>
            </div>

            <div className="alert-actions-row">
              <span className="mini-status">◔ Active</span>
              <div className="alert-action-buttons">
                <button className="secondary-btn">Edit</button>
                <button className="danger-text-btn">Delete</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}