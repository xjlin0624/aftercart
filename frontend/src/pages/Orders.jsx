import React, { useEffect, useMemo, useState } from "react";
import { getOrders } from "../api";

function normalizeOrders(data) {
  if (Array.isArray(data)) return data;
  return data.orders || data.results || data.data || [];
}

function formatMoney(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function mapOrder(order) {
  const firstItem =
    Array.isArray(order.items) && order.items.length > 0 ? order.items[0] : null;

  const subtotal = Number(order.subtotal || 0);
  const paid = Number(order.paid_price || subtotal || 0);
  const savings = Math.max(paid - subtotal, 0);

  return {
    id: order.retailer_order_id || order.id || "N/A",
    store: order.retailer || "Unknown",
    item: firstItem?.product_name || "Unknown Item",
    pricePaid: formatMoney(paid),
    currentPrice: formatMoney(subtotal),
    savings: formatMoney(savings),
    status: order.order_status || "Unknown",
  };
}

function getStatusClass(status) {
  const value = String(status || "").toLowerCase();
  if (value.includes("deliver")) return "delivered";
  if (value.includes("ship")) return "shipped";
  if (value.includes("delay")) return "delayed";
  if (value.includes("track")) return "tracking";
  if (value.includes("alert")) return "alert";
  if (value.includes("change")) return "no-change";
  return "tracking";
}

export default function Orders() {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    async function loadOrders() {
      try {
        setLoading(true);
        setErrorMsg("");
        const res = await getOrders();
        setOrders(normalizeOrders(res));
      } catch (error) {
        setErrorMsg(error.message || "Failed to load orders");
      } finally {
        setLoading(false);
      }
    }

    loadOrders();
  }, []);

  const mappedOrders = useMemo(() => orders.map(mapOrder), [orders]);

  const summary = useMemo(() => {
    const totalOrders = orders.length;
    const totalSpent = orders.reduce(
      (sum, order) => sum + Number(order.paid_price || order.subtotal || 0),
      0
    );
    const totalSavings = orders.reduce((sum, order) => {
      const subtotal = Number(order.subtotal || 0);
      const paid = Number(order.paid_price || subtotal || 0);
      return sum + Math.max(paid - subtotal, 0);
    }, 0);

    const alertCount = orders.filter((o) =>
      String(o.order_status || "").toLowerCase().includes("alert")
    ).length;

    const trackingCount = orders.filter((o) =>
      String(o.order_status || "").toLowerCase().includes("track")
    ).length;

    const noChangeCount = orders.filter((o) =>
      String(o.order_status || "").toLowerCase().includes("change")
    ).length;

    return {
      totalOrders,
      activeAlerts: alertCount,
      totalSpent: formatMoney(totalSpent),
      potentialSavings: formatMoney(totalSavings),
      quickStats: [
        { label: "Price Drops", value: alertCount },
        { label: "No Changes", value: noChangeCount },
        { label: "Tracking", value: trackingCount },
      ],
    };
  }, [orders]);

  return (
    <div className="page-content">
      {loading && <p>Loading orders...</p>}
      {errorMsg && <p style={{ color: "red" }}>{errorMsg}</p>}

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
              {mappedOrders.length === 0 && !loading ? (
                <tr>
                  <td colSpan="8">No orders found.</td>
                </tr>
              ) : (
                mappedOrders.map((row) => (
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
                      <span className={`status-pill ${getStatusClass(row.status)}`}>
                        {row.status}
                      </span>
                    </td>
                    <td>
                      <button className="secondary-btn">View</button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        <div className="summary-card">
          <div className="summary-title">Order Summary</div>

          <div className="summary-row">
            <span>Total Orders</span>
            <strong>{summary.totalOrders}</strong>
          </div>
          <div className="summary-row">
            <span>Active Alerts</span>
            <strong>{summary.activeAlerts}</strong>
          </div>
          <div className="summary-row">
            <span>Total Spent</span>
            <strong>{summary.totalSpent}</strong>
          </div>

          <div className="summary-divider"></div>

          <div className="summary-row">
            <span>Potential Savings</span>
            <strong className="green-text">{summary.potentialSavings}</strong>
          </div>

          <div className="summary-divider"></div>

          <div className="summary-subtitle">Quick Stats</div>

          {summary.quickStats.map((item) => (
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