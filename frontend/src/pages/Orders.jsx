import React from "react";
import { orders, ordersSummary } from "../mockData";

export default function Orders() {
  return (
    <div className="page-content">
      <div className="filter-bar">
        <div className="inner-search">⌕ Search orders...</div>
        <button className="ghost-select">Status ▾</button>
        <button className="ghost-select">Store ▾</button>
        <button className="ghost-select">⌁ Date Filter</button>
      </div>

      <div className="orders-layout">
        <div className="table-card">
          <table className="data-table">
            <thead>
              <tr>
                <th>ORDER ID</th>
                <th>STORE</th>
                <th>ITEM</th>
                <th>PRICE PAID</th>
                <th>CURRENT PRICE</th>
                <th>SAVINGS</th>
                <th>STATUS</th>
                <th>ACTION</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((row) => (
                <tr key={row.id}>
                  <td>{row.id}</td>
                  <td>{row.store}</td>
                  <td>{row.item}</td>
                  <td>{row.pricePaid}</td>
                  <td>{row.currentPrice}</td>
                  <td className={row.savings === "$0.00" ? "muted-text" : "green-text"}>
                    {row.savings}
                  </td>
                  <td>
                    <span className={`status-pill ${row.status.toLowerCase().replace(" ", "-")}`}>
                      {row.status}
                    </span>
                  </td>
                  <td>
                    <button className="secondary-btn">View</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="summary-card">
          <div className="summary-title">Order Summary</div>

          <div className="summary-row">
            <span>Total Orders</span>
            <strong>{ordersSummary.totalOrders}</strong>
          </div>
          <div className="summary-row">
            <span>Active Alerts</span>
            <strong>{ordersSummary.activeAlerts}</strong>
          </div>
          <div className="summary-row">
            <span>Total Spent</span>
            <strong>{ordersSummary.totalSpent}</strong>
          </div>

          <div className="summary-divider"></div>

          <div className="summary-row">
            <span>Potential Savings</span>
            <strong className="green-text">{ordersSummary.potentialSavings}</strong>
          </div>

          <div className="summary-divider"></div>

          <div className="summary-subtitle">Quick Stats</div>

          {ordersSummary.quickStats.map((item) => (
            <div className="summary-row" key={item.label}>
              <span>{item.label}</span>
              <span className="count-badge">{item.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}