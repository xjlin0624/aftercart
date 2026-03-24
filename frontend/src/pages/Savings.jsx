import React from "react";
import { savingsStats, savingsByMonth, savingsHistory } from "../mockData";
import StatCard from "../components/StatCard";
import BarSavingsChart from "../components/BarSavingsChart";

export default function Savings() {
  return (
    <div className="page-content">
      <div className="three-col-grid">
        {savingsStats.map((item) => (
          <StatCard key={item.title} {...item} />
        ))}
      </div>

      <div className="section-space"></div>

      <BarSavingsChart data={savingsByMonth} />

      <div className="section-space"></div>

      <div className="table-card">
        <div className="table-card-header left-only">
          <div>
            <div className="section-card-title">Savings History</div>
            <div className="section-card-subtitle">
              Detailed breakdown of all your savings
            </div>
          </div>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>DATE</th>
              <th>STORE</th>
              <th>ITEM</th>
              <th>SAVED AMOUNT</th>
              <th>TYPE</th>
            </tr>
          </thead>
          <tbody>
            {savingsHistory.map((row, index) => (
              <tr key={index}>
                <td>{row.date}</td>
                <td>{row.store}</td>
                <td>{row.item}</td>
                <td className="green-text strong-text">{row.savedAmount}</td>
                <td>
                  <span className={row.type === "Price Match" ? "type-pill green" : "type-pill blue"}>
                    {row.type}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}