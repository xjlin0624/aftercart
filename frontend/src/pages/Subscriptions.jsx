import React from "react";
import { subscriptionPlans, billingHistory } from "../mockData";

export default function Subscriptions() {
  return (
    <div className="page-content">
      <div className="plans-grid">
        <div className="plan-card">
          <div className="plan-header">
            <div className="plan-title">{subscriptionPlans.free.title}</div>
            <span className="small-badge">{subscriptionPlans.free.badge}</span>
          </div>

          <div className="plan-price-row">
            <span className="plan-price">{subscriptionPlans.free.price}</span>
            <span className="plan-price-suffix">/month</span>
          </div>

          <div className="plan-divider"></div>

          <div className="plan-section-title">Features included:</div>

          <div className="plan-feature-list">
            {subscriptionPlans.free.features.map((feature, index) => (
              <div
                key={index}
                className={feature.included ? "feature-item included" : "feature-item excluded"}
              >
                <span>{feature.included ? "✓" : "✕"}</span>
                <span>{feature.text}</span>
              </div>
            ))}
          </div>

          <button className="disabled-btn">{subscriptionPlans.free.buttonText}</button>
        </div>

        <div className="plan-card premium-card">
          <div className="premium-tag">{subscriptionPlans.premium.badge}</div>

          <div className="plan-header premium-header">
            <div className="plan-title">{subscriptionPlans.premium.title}</div>
          </div>

          <div className="plan-price-row">
            <span className="plan-price">{subscriptionPlans.premium.price}</span>
            <span className="plan-price-suffix">/month</span>
          </div>

          <div className="plan-subtitle">{subscriptionPlans.premium.subtitle}</div>

          <div className="plan-divider"></div>

          <div className="plan-section-title">Everything in Free, plus:</div>

          <div className="plan-feature-list">
            {subscriptionPlans.premium.features.map((feature, index) => (
              <div key={index} className="feature-item included">
                <span>✓</span>
                <span>{feature.text}</span>
              </div>
            ))}
          </div>

          <button className="primary-btn full-width-btn">
            {subscriptionPlans.premium.buttonText}
          </button>
        </div>
      </div>

      <div className="section-space"></div>

      <div className="table-card">
        <div className="table-card-header left-only">
          <div>
            <div className="section-card-title">Billing History</div>
            <div className="section-card-subtitle">
              View your past invoices and payment history
            </div>
          </div>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>DATE</th>
              <th>PLAN</th>
              <th>AMOUNT</th>
              <th>STATUS</th>
              <th>ACTION</th>
            </tr>
          </thead>
          <tbody>
            {billingHistory.map((row, index) => (
              <tr key={index}>
                <td>{row.date}</td>
                <td>{row.plan}</td>
                <td>{row.amount}</td>
                <td>
                  <span className={row.status === "Paid" ? "type-pill green" : "type-pill gray"}>
                    {row.status}
                  </span>
                </td>
                <td>{row.action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}