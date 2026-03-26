import React, { useEffect, useMemo, useState } from "react";
import { dismissAlert, getAlerts, resolveAlert } from "../api";

function normalizeAlerts(data) {
  if (Array.isArray(data)) return data;
  return data.alerts || data.results || data.data || [];
}

function mapAlert(alert, index) {
  return {
    id: alert.id || alert.alert_id || index,
    product: alert.title || alert.alert_type || "Alert",
    store: alert.status || "Unknown",
    targetPrice: alert.evidence || "-",
    currentPrice: alert.body || "-",
    active: String(alert.status || "").toLowerCase() !== "dismissed",
  };
}

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  async function loadAlerts() {
    try {
      setLoading(true);
      setErrorMsg("");
      const res = await getAlerts();
      setAlerts(normalizeAlerts(res));
    } catch (error) {
      setErrorMsg(error.message || "Failed to load alerts");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAlerts();
  }, []);

  async function handleResolve(id) {
    try {
      await resolveAlert(id);
      await loadAlerts();
    } catch (error) {
      setErrorMsg(error.message || "Failed to resolve alert");
    }
  }

  async function handleDismiss(id) {
    try {
      await dismissAlert(id);
      await loadAlerts();
    } catch (error) {
      setErrorMsg(error.message || "Failed to dismiss alert");
    }
  }

  const mappedAlerts = useMemo(() => alerts.map(mapAlert), [alerts]);

  return (
    <div className="page-content">
      {loading && <p>Loading alerts...</p>}
      {errorMsg && <p style={{ color: "red" }}>{errorMsg}</p>}

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
        {mappedAlerts.length === 0 && !loading ? (
          <p>No alerts found.</p>
        ) : (
          mappedAlerts.map((item) => (
            <div className="alert-card" key={item.id}>
              <div className="alert-card-top">
                <div className="alert-image-box">🔔</div>
                <div>
                  <div className="alert-product">{item.product}</div>
                  <div className="alert-store">{item.store}</div>
                </div>
              </div>

              <div className="alert-info-list">
                <div className="alert-info-row">
                  <span>Evidence</span>
                  <strong>{item.targetPrice}</strong>
                </div>
                <div className="alert-info-row">
                  <span>Message</span>
                  <strong>{item.currentPrice}</strong>
                </div>
              </div>

              <div className="alert-actions-row">
                <span className="mini-status">
                  {item.active ? "◔ Active" : "○ Dismissed"}
                </span>
                <div className="alert-action-buttons">
                  <button
                    className="secondary-btn"
                    onClick={() => handleResolve(item.id)}
                  >
                    Resolve
                  </button>
                  <button
                    className="danger-text-btn"
                    onClick={() => handleDismiss(item.id)}
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}