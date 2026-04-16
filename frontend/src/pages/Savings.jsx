import React, { useEffect, useMemo, useState } from "react";

import { getSavingsSummary } from "../api";
import BarSavingsChart from "../components/BarSavingsChart";
import StatCard from "../components/StatCard";

function formatMoney(value) {
  const n = Number(value || 0);
  return `$${n.toFixed(2)}`;
}

function formatActionType(value) {
  return String(value || "unknown")
    .replaceAll("_", " ")
    .replace(/^\w/, (c) => c.toUpperCase());
}

function groupByMonth(history) {
  const map = {};
  for (const entry of history) {
    if (!entry.was_successful || !entry.recovered_value) continue;
    const d = new Date(entry.logged_at);
    const label = d.toLocaleString("en-US", { month: "short", year: "numeric" });
    map[label] = (map[label] || 0) + Number(entry.recovered_value);
  }
  return Object.entries(map)
    .sort((a, b) => new Date(a[0]).getTime() - new Date(b[0]).getTime())
    .map(([month, amount]) => ({ month, amount: parseFloat(amount.toFixed(2)) }));
}

function getOutcomeStatus(row) {
  if (row.was_successful) return { label: "Success", className: "type-pill green" };
  if (row.was_successful === false) {
    return { label: "No recovery", className: "type-pill gray" };
  }
  return { label: "Pending", className: "type-pill blue" };
}

export default function Savings() {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setErrorMsg("");
        const data = await getSavingsSummary();
        setSummary(data);
      } catch (err) {
        setErrorMsg(err.message || "Failed to load savings");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const stats = useMemo(() => {
    if (!summary) return [];
    const avg =
      summary.successful_actions > 0
        ? summary.total_recovered / summary.successful_actions
        : 0;
    return [
      {
        title: "Total Saved",
        value: formatMoney(summary.total_recovered),
        trend:
          summary.total_recovered > 0
            ? "Recovered from successful actions"
            : "No recovered savings yet",
        positive: summary.total_recovered > 0,
      },
      {
        title: "Successful Actions",
        value: String(summary.successful_actions),
        trend: `of ${summary.total_actions} recorded action${summary.total_actions === 1 ? "" : "s"}`,
        positive: summary.successful_actions > 0,
      },
      {
        title: "Avg Savings / Action",
        value: formatMoney(avg),
        trend:
          summary.successful_actions > 0
            ? "Average recovery per successful action"
            : "Waiting for a completed recovery",
        positive: summary.successful_actions > 0,
      },
    ];
  }, [summary]);

  const chartData = useMemo(() => {
    if (!summary) return [];
    return groupByMonth(summary.history);
  }, [summary]);

  const history = summary?.history ?? [];
  const byAction = summary?.by_action ?? [];

  return (
    <div className="page-content">
      {loading && <p>Loading savings...</p>}
      {errorMsg && <p style={{ color: "red" }}>{errorMsg}</p>}

      <div className="three-col-grid">
        {stats.map((item) => (
          <StatCard key={item.title} {...item} />
        ))}
      </div>

      <div className="section-space"></div>

      {chartData.length > 0 ? (
        <BarSavingsChart data={chartData} />
      ) : (
        !loading && (
          <div className="table-card">
            <div className="section-card-title">Savings Over Time</div>
            <p style={{ color: "#6b7280", marginBottom: 0 }}>
              No completed savings outcomes are available to chart yet.
            </p>
          </div>
        )
      )}

      <div className="section-space"></div>

      <div className="dashboard-main-grid">
        <div className="table-card">
          <div className="table-card-header left-only">
            <div>
              <div className="section-card-title">Savings Breakdown</div>
              <div className="section-card-subtitle">
                Totals are grouped by the action you actually completed.
              </div>
            </div>
          </div>

          <div style={{ padding: "0 20px 18px" }}>
            {byAction.length === 0 && !loading ? (
              <p style={{ color: "#9ca3af", margin: 0, fontSize: "0.9rem" }}>
                No savings breakdown is available yet because no successful outcomes have been logged.
              </p>
            ) : (
              byAction.map((row) => (
                <div className="summary-row" key={row.action_taken}>
                  <span>{formatActionType(row.action_taken)}</span>
                  <strong>
                    {formatMoney(row.total_recovered)} across {row.count} action
                    {row.count === 1 ? "" : "s"}
                  </strong>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="table-card">
          <div className="table-card-header left-only">
            <div>
              <div className="section-card-title">What This Page Tracks</div>
              <div className="section-card-subtitle">
                Savings only appear after an alert outcome is logged successfully.
              </div>
            </div>
          </div>
          <p style={{ color: "#6b7280", margin: 0, padding: "0 20px 20px", fontSize: "0.875rem", lineHeight: 1.6 }}>
            Use the Alerts page to generate support messages and log successful outcomes. Those
            logged outcomes feed the totals and history shown here.
          </p>
        </div>
      </div>

      <div className="section-space"></div>

      <div className="table-card">
        <div className="table-card-header left-only">
          <div>
            <div className="section-card-title">Savings History</div>
            <div className="section-card-subtitle">
              Recorded results from the actions you took on alerts.
            </div>
          </div>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th>DATE</th>
              <th>ACTION</th>
              <th>RECOVERED</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {history.length === 0 && !loading ? (
              <tr>
                <td colSpan="4">No savings history yet.</td>
              </tr>
            ) : (
              history.map((row) => {
                const status = getOutcomeStatus(row);

                return (
                  <tr key={row.id}>
                    <td>
                      {new Date(row.logged_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </td>
                    <td>{formatActionType(row.action_taken)}</td>
                    <td className="green-text strong-text">
                      {row.recovered_value != null ? formatMoney(row.recovered_value) : "N/A"}
                    </td>
                    <td>
                      <span className={status.className}>{status.label}</span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
