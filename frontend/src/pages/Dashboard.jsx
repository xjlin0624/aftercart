import React, { useEffect, useMemo, useState } from "react";
import { getOrders, getAlerts } from "../api";
import { priceHistory } from "../mockData";
import StatCard from "../components/StatCard";
import PriceLineChart from "../components/PriceLineChart";

function normalizeOrders(data) {
  if (Array.isArray(data)) return data;
  return data.orders || data.results || data.data || [];
}

function normalizeAlerts(data) {
  if (Array.isArray(data)) return data;
  return data.alerts || data.results || data.data || [];
}

function formatMoney(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function mapRecentPurchase(order) {
  const firstItem =
    Array.isArray(order.items) && order.items.length > 0 ? order.items[0] : null;

  return {
    store: order.retailer || "Unknown",
    product: firstItem?.product_name || "Unknown Item",
    price: formatMoney(order.subtotal || 0),
    status: order.order_status || "Unknown",
    date: order.order_date
      ? new Date(order.order_date).toLocaleDateString("en-US", {
          month: "short",
          day: "numeric",
          year: "numeric",
        })
      : "N/A",
  };
}

function getStatusClass(status) {
  const value = String(status || "").toLowerCase();
  if (value.includes("deliver")) return "delivered";
  if (value.includes("ship")) return "shipped";
  if (value.includes("delay")) return "delayed";
  if (value.includes("track")) return "tracking";
  if (value.includes("alert")) return "alert";
  return "tracking";
}

export default function Dashboard() {
  const [orders, setOrders] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        setErrorMsg("");

        const [ordersRes, alertsRes] = await Promise.all([
          getOrders(),
          getAlerts("new"),
        ]);

        setOrders(normalizeOrders(ordersRes));
        setAlerts(normalizeAlerts(alertsRes));
      } catch (error) {
        setErrorMsg(error.message || "Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const stats = useMemo(() => {
    const totalSaved = orders.reduce((sum, order) => {
      const subtotal = Number(order.subtotal || 0);
      const paid = Number(order.paid_price || subtotal || 0);
      return sum + Math.max(paid - subtotal, 0);
    }, 0);

    return [
      {
        title: "Total Saved",
        value: formatMoney(totalSaved),
        trend: "from connected orders",
        positive: true,
      },
      {
        title: "Alerts Triggered",
        value: String(alerts.length),
        trend: "live alerts loaded",
        positive: true,
      },
      {
        title: "Active Orders",
        value: String(orders.length),
        trend: "orders in system",
        positive: false,
      },
    ];
  }, [orders, alerts]);

  const smartAlerts = useMemo(() => {
    return alerts.slice(0, 3).map((alert, index) => ({
      id: alert.id || alert.alert_id || index,
      title: alert.title || alert.alert_type || "Alert",
      desc: alert.body || alert.evidence || "No details available.",
      action: "View Details",
    }));
  }, [alerts]);

  const recentPurchases = useMemo(() => {
    return orders.slice(0, 5).map(mapRecentPurchase);
  }, [orders]);

  return (
    <div className="page-content">
      {loading && <p>Loading dashboard...</p>}
      {errorMsg && <p style={{ color: "red" }}>{errorMsg}</p>}

      <section className="section-block">
        <div className="section-label">Savings Overview</div>

        <div className="three-col-grid">
          {stats.map((item) => (
            <StatCard key={item.title} {...item} />
          ))}
        </div>
      </section>

      <section className="dashboard-main-grid">
        <PriceLineChart data={priceHistory} />

        <div className="smart-alerts-card">
          <div className="section-card-title">Smart Alerts</div>

          <div className="alerts-stack">
            {smartAlerts.length === 0 && !loading ? (
              <div className="smart-alert-item">
                <div className="smart-alert-body">
                  <div className="smart-alert-title">No alerts yet</div>
                  <div className="smart-alert-desc">
                    Backend did not return any alerts.
                  </div>
                </div>
              </div>
            ) : (
              smartAlerts.map((alert) => (
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
              ))
            )}
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
              {recentPurchases.length === 0 && !loading ? (
                <tr>
                  <td colSpan="5">No orders found.</td>
                </tr>
              ) : (
                recentPurchases.map((row, index) => (
                  <tr key={index}>
                    <td>{row.store}</td>
                    <td>{row.product}</td>
                    <td className="strong-text">{row.price}</td>
                    <td>
                      <span className={`status-pill ${getStatusClass(row.status)}`}>
                        {row.status}
                      </span>
                    </td>
                    <td>{row.date}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}