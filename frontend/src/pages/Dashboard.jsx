import React from "react";
import {
  dashboardStats,
  priceHistory,
  smartAlerts,
  recentPurchases,
} from "../mockData";
import StatCard from "../components/StatCard";
import PriceLineChart from "../components/PriceLineChart";

export default function Dashboard() {
  return (
    <div className="page-content">
      <section className="section-block">
        <div className="section-label">Savings Overview</div>

        <div className="three-col-grid">
          {dashboardStats.map((item) => (
            <StatCard key={item.title} {...item} />
          ))}
        </div>
      </section>

      <section className="dashboard-main-grid">
        <PriceLineChart data={priceHistory} />

        <div className="smart-alerts-card">
          <div className="section-card-title">Smart Alerts</div>

          <div className="alerts-stack">
            {smartAlerts.map((alert) => (
              <div key={alert.id} className="smart-alert-item">
                <div className="smart-alert-icon">◌</div>

                <div className="smart-alert-body">
                  <div className="smart-alert-title">{alert.title}</div>
                  <div className="smart-alert-desc">{alert.desc}</div>
                  <button className="secondary-btn full-width-btn">
                    {alert.action}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section-block">
        <div className="section-label">Recent Purchases</div>

        <div className="table-card">
          <div className="table-card-header">
            <div>
              <div className="section-card-title">Recent Purchases</div>
            </div>
            <button className="plain-link-btn">View All</button>
          </div>

          <table className="data-table">
            <thead>
              <tr>
                <th>STORE</th>
                <th>PRODUCT</th>
                <th>PRICE</th>
                <th>STATUS</th>
                <th>DATE</th>
              </tr>
            </thead>
            <tbody>
              {recentPurchases.map((row, index) => (
                <tr key={index}>
                  <td>{row.store}</td>
                  <td>{row.product}</td>
                  <td className="strong-text">{row.price}</td>
                  <td>
                    <span className={`status-pill ${row.status.toLowerCase()}`}>
                      {row.status}
                    </span>
                  </td>
                  <td>{row.date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}