import React, { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import {
  createAlert,
  dismissAlert,
  getAlertMessage,
  getAlertRecommendation,
  getAlerts,
  getOrders,
  logOutcome,
  resolveAlert,
} from "../api";

function normalizeAlerts(data) {
  if (Array.isArray(data)) return data;
  return data.alerts || data.results || data.data || data.value || [];
}

function normalizeOrders(data) {
  if (Array.isArray(data)) return data;
  return data.orders || data.results || data.data || [];
}

function formatCurrency(value) {
  const amount = Number(value);
  return Number.isFinite(amount) ? `$${amount.toFixed(2)}` : null;
}

function formatAlertType(value) {
  const text = String(value || "alert").replaceAll("_", " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function formatEvidence(alert) {
  const evidence =
    alert && typeof alert.evidence === "object" && alert.evidence !== null
      ? alert.evidence
      : null;

  if (!evidence) {
    return "No additional evidence.";
  }

  if (alert.alert_type === "price_drop") {
    const current = formatCurrency(evidence.current_price);
    const paid = formatCurrency(evidence.paid_price);
    const delta = formatCurrency(evidence.price_delta);

    if (current && paid && delta) {
      return `Now ${current}, paid ${paid}, potential savings ${delta}.`;
    }
    if (current && paid) {
      return `Now ${current}, paid ${paid}.`;
    }
  }

  if (alert.alert_type === "delivery_anomaly") {
    if (evidence.event_type === "eta_updated") {
      return `ETA changed from ${evidence.previous_eta || "unknown"} to ${evidence.new_eta || "unknown"}.`;
    }
    if (evidence.event_type === "tracking_stalled") {
      return "Tracking appears to be stalled.";
    }
  }

  return Object.entries(evidence)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : String(value)}`)
    .join(" | ");
}

function formatOrderOption(order) {
  const firstItem =
    Array.isArray(order.items) && order.items.length > 0 ? order.items[0] : null;
  return `${order.retailer_order_id || order.id} | ${order.retailer || "Unknown"} | ${
    firstItem?.product_name || "Order"
  }`;
}

function mapRecommendedActionToOutcome(action) {
  if (action === "price_match") return "price_matched";
  if (action === "return_and_rebuy") return "returned_and_rebought";
  return "ignored";
}

function isActiveAlert(alert) {
  const status = String(alert.status || "").toLowerCase();
  return status !== "dismissed" && status !== "resolved";
}

const defaultCreateForm = {
  order_id: "",
  alert_type: "price_drop",
  priority: "medium",
  title: "",
  body: "",
};

const inputLikeStyle = {
  minHeight: "48px",
  borderRadius: "10px",
  border: "none",
  background: "#f3f3f3",
  padding: "12px 14px",
  outline: "none",
  width: "100%",
};

export default function Alerts() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [alerts, setAlerts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [busyId, setBusyId] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [statusMsg, setStatusMsg] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState(defaultCreateForm);
  const [recommendations, setRecommendations] = useState({});
  const [messages, setMessages] = useState({});

  const activeTab = searchParams.get("tab") === "history" ? "history" : "active";

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

  async function ensureOrdersLoaded() {
    if (orders.length > 0) return;

    try {
      setLoadingOrders(true);
      const data = await getOrders();
      setOrders(normalizeOrders(data));
    } catch (error) {
      setErrorMsg(error.message || "Failed to load orders for alert creation");
    } finally {
      setLoadingOrders(false);
    }
  }

  async function handleToggleCreateForm() {
    setStatusMsg("");
    setErrorMsg("");

    if (!showCreateForm) {
      await ensureOrdersLoaded();
    }
    setShowCreateForm((current) => !current);
  }

  function handleTabChange(nextTab) {
    const next = new window.URLSearchParams(searchParams);
    if (nextTab === "history") {
      next.set("tab", "history");
    } else {
      next.delete("tab");
    }
    setSearchParams(next, { replace: true });
  }

  function updateCreateForm(field, value) {
    setCreateForm((current) => ({
      ...current,
      [field]: value,
    }));
  }

  async function handleCreateAlert(event) {
    event.preventDefault();

    try {
      setBusyId("create-alert");
      setStatusMsg("");
      setErrorMsg("");

      await createAlert({
        order_id: createForm.order_id || null,
        alert_type: createForm.alert_type,
        priority: createForm.priority,
        title: createForm.title.trim(),
        body: createForm.body.trim(),
      });

      setCreateForm(defaultCreateForm);
      setShowCreateForm(false);
      handleTabChange("active");
      await loadAlerts();
      setStatusMsg("Alert created successfully.");
    } catch (error) {
      setErrorMsg(error.message || "Failed to create alert");
    } finally {
      setBusyId("");
    }
  }

  async function handleResolve(id) {
    try {
      setBusyId(id);
      setStatusMsg("");
      await resolveAlert(id);
      await loadAlerts();
    } catch (error) {
      setErrorMsg(error.message || "Failed to resolve alert");
    } finally {
      setBusyId("");
    }
  }

  async function handleDismiss(id) {
    try {
      setBusyId(id);
      setStatusMsg("");
      await dismissAlert(id);
      await loadAlerts();
    } catch (error) {
      setErrorMsg(error.message || "Failed to dismiss alert");
    } finally {
      setBusyId("");
    }
  }

  async function handleLoadRecommendation(alertId) {
    try {
      setBusyId(alertId);
      setErrorMsg("");
      const data = await getAlertRecommendation(alertId);
      setRecommendations((current) => ({
        ...current,
        [alertId]: data,
      }));
    } catch (error) {
      setErrorMsg(error.message || "Failed to load recommendation");
    } finally {
      setBusyId("");
    }
  }

  async function handleLoadMessage(alertId) {
    try {
      setBusyId(alertId);
      setErrorMsg("");
      const data = await getAlertMessage(alertId);
      setMessages((current) => ({
        ...current,
        [alertId]: data,
      }));
    } catch (error) {
      setErrorMsg(error.message || "Failed to generate support message");
    } finally {
      setBusyId("");
    }
  }

  async function handleLogOutcome(alert) {
    try {
      setBusyId(alert.id);
      setErrorMsg("");
      setStatusMsg("");

      await logOutcome({
        alert_id: alert.id,
        order_item_id: alert.order_item_id || null,
        action_taken: mapRecommendedActionToOutcome(alert.recommended_action),
        recovered_value:
          alert.estimated_savings !== null && alert.estimated_savings !== undefined
            ? Number(alert.estimated_savings)
            : null,
        was_successful: true,
      });

      setStatusMsg("Outcome logged. Your Savings page will reflect it after refresh.");
      await loadAlerts();
    } catch (error) {
      setErrorMsg(error.message || "Failed to log outcome");
    } finally {
      setBusyId("");
    }
  }

  const filteredAlerts = useMemo(() => {
    return alerts.filter((alert) =>
      activeTab === "active" ? isActiveAlert(alert) : !isActiveAlert(alert)
    );
  }, [activeTab, alerts]);

  return (
    <div className="page-content">
      {loading && <p>Loading alerts...</p>}
      {statusMsg && <p style={{ color: "green" }}>{statusMsg}</p>}
      {errorMsg && <p style={{ color: "red" }}>{errorMsg}</p>}

      <div className="page-helper-row">
        <div className="page-helper-text">
          Review price drops and delivery issues, then generate a message, log the result, or add a manual alert.
        </div>
        <button className="primary-btn" type="button" onClick={handleToggleCreateForm}>
          {showCreateForm ? "Close Alert Form" : "Create New Alert"}
        </button>
      </div>

      {showCreateForm ? (
        <div className="settings-card" style={{ margin: "0 0 22px 0", maxWidth: "100%" }}>
          <div className="section-card-title">Create Alert</div>
          <div className="section-card-subtitle" style={{ marginBottom: "16px" }}>
            Create a manual alert tied to an order, or leave the order blank for a general reminder.
          </div>

          <form onSubmit={handleCreateAlert}>
            <div className="settings-grid two-col">
              <div className="form-group">
                <label>Related Order (Optional)</label>
                <select
                  value={createForm.order_id}
                  onChange={(event) => updateCreateForm("order_id", event.target.value)}
                  style={inputLikeStyle}
                  disabled={loadingOrders || busyId === "create-alert"}
                >
                  <option value="">No related order</option>
                  {orders.map((order) => (
                    <option key={order.id} value={order.id}>
                      {formatOrderOption(order)}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label>Alert Type</label>
                <select
                  value={createForm.alert_type}
                  onChange={(event) => updateCreateForm("alert_type", event.target.value)}
                  style={inputLikeStyle}
                  disabled={busyId === "create-alert"}
                >
                  <option value="price_drop">Price Drop</option>
                  <option value="delivery_anomaly">Delivery Anomaly</option>
                  <option value="return_window_expiring">Return Window Expiring</option>
                  <option value="alternative_product">Alternative Product</option>
                </select>
              </div>
            </div>

            <div className="settings-grid two-col" style={{ marginTop: "16px" }}>
              <div className="form-group">
                <label>Priority</label>
                <select
                  value={createForm.priority}
                  onChange={(event) => updateCreateForm("priority", event.target.value)}
                  style={inputLikeStyle}
                  disabled={busyId === "create-alert"}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>

              <div className="form-group">
                <label>Title</label>
                <input
                  value={createForm.title}
                  onChange={(event) => updateCreateForm("title", event.target.value)}
                  placeholder="Short alert title"
                  required
                  disabled={busyId === "create-alert"}
                />
              </div>
            </div>

            <div className="settings-grid one-col" style={{ marginTop: "16px" }}>
              <div className="form-group">
                <label>Details</label>
                <textarea
                  value={createForm.body}
                  onChange={(event) => updateCreateForm("body", event.target.value)}
                  placeholder="Describe what the alert should remind you to do."
                  required
                  rows={4}
                  style={{ ...inputLikeStyle, resize: "vertical" }}
                  disabled={busyId === "create-alert"}
                />
              </div>
            </div>

            <div className="settings-actions" style={{ marginTop: "16px" }}>
              <button
                className="secondary-btn"
                type="button"
                onClick={() => {
                  setCreateForm(defaultCreateForm);
                  setShowCreateForm(false);
                }}
                disabled={busyId === "create-alert"}
              >
                Cancel
              </button>
              <button className="primary-btn" type="submit" disabled={busyId === "create-alert"}>
                {busyId === "create-alert" ? "Creating..." : "Create Alert"}
              </button>
            </div>
          </form>
        </div>
      ) : null}

      <div className="pill-tabs">
        <button
          className={`pill-tab ${activeTab === "active" ? "active" : ""}`}
          type="button"
          onClick={() => handleTabChange("active")}
        >
          Active Alerts
        </button>
        <button
          className={`pill-tab ${activeTab === "history" ? "active" : ""}`}
          type="button"
          onClick={() => handleTabChange("history")}
        >
          Alert History
        </button>
      </div>

      <div className="page-helper-row" style={{ marginTop: "-8px" }}>
        <div className="page-helper-text">
          Use recommendation and message actions on price-drop alerts, then log the result to update Savings.
        </div>
        <Link className="plain-link-btn" to="/savings">
          View Savings History
        </Link>
      </div>

      <div className="three-col-grid alerts-grid">
        {filteredAlerts.length === 0 && !loading ? (
          <p>
            {activeTab === "active"
              ? "No active alerts found."
              : "No resolved or dismissed alerts yet."}
          </p>
        ) : (
          filteredAlerts.map((alert) => {
            const recommendation = recommendations[alert.id];
            const message = messages[alert.id];
            const isBusy = busyId === alert.id;

            return (
              <div className="alert-card" key={alert.id}>
                <div className="alert-card-top">
                  <div className="alert-image-box">!</div>
                  <div>
                    <div className="alert-product">{alert.title || formatAlertType(alert.alert_type)}</div>
                    <div className="alert-store">
                      {formatAlertType(alert.alert_type)} | {String(alert.priority || "medium").toUpperCase()}
                    </div>
                  </div>
                </div>

                <div className="alert-info-list">
                  <div className="alert-info-row">
                    <span>Evidence</span>
                    <strong>{formatEvidence(alert)}</strong>
                  </div>
                  <div className="alert-info-row">
                    <span>Message</span>
                    <strong>{String(alert.body || "No message available.")}</strong>
                  </div>
                </div>

                {recommendation ? (
                  <div className="alert-info-list" style={{ marginTop: "12px" }}>
                    <div className="alert-info-row">
                      <span>Recommendation</span>
                      <strong>{String(recommendation.recommended_action).replaceAll("_", " ")}</strong>
                    </div>
                    <div className="alert-info-row">
                      <span>Why</span>
                      <strong>{recommendation.rationale}</strong>
                    </div>
                    <div className="alert-info-row">
                      <span>Estimated savings</span>
                      <strong>{formatCurrency(recommendation.estimated_savings) || "Not available"}</strong>
                    </div>
                    {Array.isArray(recommendation.action_steps) && recommendation.action_steps.length > 0 ? (
                      <div>
                        <span style={{ display: "block", fontSize: "0.8rem", color: "#6b7280", marginBottom: "6px" }}>
                          Action steps
                        </span>
                        <ol style={{ margin: 0, paddingLeft: "18px" }}>
                          {recommendation.action_steps.map((step) => (
                            <li key={`${alert.id}-step-${step.step}`}>{step.instruction}</li>
                          ))}
                        </ol>
                      </div>
                    ) : null}
                  </div>
                ) : null}

                {message ? (
                  <div style={{ marginTop: "12px", borderTop: "1px solid #efefef", paddingTop: "12px" }}>
                    <div style={{ fontSize: "11px", fontWeight: 700, color: "#9a9a9a", textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: "6px" }}>
                      Support Draft
                    </div>
                    <div className="support-draft-box">{message.message}</div>
                  </div>
                ) : null}

                <div
                  className="alert-action-buttons"
                  style={{ display: "flex", gap: "8px", flexWrap: "wrap", marginTop: "16px" }}
                >
                  {alert.recommended_action ? (
                    <button
                      className="secondary-btn"
                      type="button"
                      disabled={isBusy}
                      onClick={() => handleLoadRecommendation(alert.id)}
                    >
                      Recommendation
                    </button>
                  ) : null}
                  <button
                    className="secondary-btn"
                    type="button"
                    disabled={isBusy}
                    onClick={() => handleLoadMessage(alert.id)}
                  >
                    Draft Message
                  </button>
                  {alert.recommended_action ? (
                    <button
                      className="secondary-btn"
                      type="button"
                      disabled={isBusy}
                      onClick={() => handleLogOutcome(alert)}
                    >
                      Log Success
                    </button>
                  ) : null}
                </div>

                <div className="alert-actions-row">
                  <span className="mini-status">
                    {isActiveAlert(alert)
                      ? `Active: ${String(alert.status || "new")}`
                      : String(alert.status || "unknown")}
                  </span>
                  <div className="alert-action-buttons">
                    <button
                      className="secondary-btn"
                      type="button"
                      disabled={isBusy}
                      onClick={() => handleResolve(alert.id)}
                    >
                      Resolve
                    </button>
                    <button
                      className="danger-text-btn"
                      type="button"
                      disabled={isBusy}
                      onClick={() => handleDismiss(alert.id)}
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
