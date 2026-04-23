import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { getOrders } from "../api";

function normalizeOrders(data) {
  if (Array.isArray(data)) return data;
  return data.orders || data.results || data.data || [];
}

function formatMoney(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function formatDate(value) {
  if (!value) return "N/A";
  return new Date(value).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
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
    itemCount: Array.isArray(order.items) ? order.items.length : 0,
    pricePaid: formatMoney(paid),
    currentPrice: formatMoney(subtotal),
    savings: formatMoney(savings),
    status: order.order_status || "Unknown",
    orderDate: order.order_date,
    order,
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

function matchesDateFilter(order, dateFilter) {
  if (!order.order_date || dateFilter === "all") return true;
  const orderDate = new Date(order.order_date).getTime();
  const now = Date.now();
  const dayMs = 24 * 60 * 60 * 1000;

  if (dateFilter === "last30") return now - orderDate <= 30 * dayMs;
  if (dateFilter === "last90") return now - orderDate <= 90 * dayMs;
  return true;
}

function updateParams(searchParams, updates, setSearchParams) {
  const next = new window.URLSearchParams(searchParams);
  Object.entries(updates).forEach(([key, value]) => {
    if (!value || value === "all") {
      next.delete(key);
    } else {
      next.set(key, value);
    }
  });
  setSearchParams(next, { replace: true });
}

export default function Orders() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const [selectedOrderId, setSelectedOrderId] = useState("");

  const query = searchParams.get("q") || "";
  const statusFilter = searchParams.get("status") || "all";
  const retailerFilter = searchParams.get("retailer") || "all";
  const dateFilter = searchParams.get("date") || "all";

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

  const filteredOrders = useMemo(() => {
    const loweredQuery = query.trim().toLowerCase();

    return mappedOrders.filter((row) => {
      const matchesQuery =
        !loweredQuery ||
        row.id.toLowerCase().includes(loweredQuery) ||
        row.store.toLowerCase().includes(loweredQuery) ||
        row.item.toLowerCase().includes(loweredQuery);

      const matchesStatus =
        statusFilter === "all" || String(row.status).toLowerCase() === statusFilter;
      const matchesRetailer =
        retailerFilter === "all" || String(row.store).toLowerCase() === retailerFilter;
      const matchesDate = matchesDateFilter(row.order, dateFilter);

      return matchesQuery && matchesStatus && matchesRetailer && matchesDate;
    });
  }, [dateFilter, mappedOrders, query, retailerFilter, statusFilter]);

  useEffect(() => {
    if (filteredOrders.length === 0) {
      setSelectedOrderId("");
      return;
    }

    if (!selectedOrderId || !filteredOrders.some((row) => row.order.id === selectedOrderId)) {
      setSelectedOrderId(filteredOrders[0].order.id);
    }
  }, [filteredOrders, selectedOrderId]);

  const selectedOrder = useMemo(() => {
    return filteredOrders.find((row) => row.order.id === selectedOrderId)?.order || null;
  }, [filteredOrders, selectedOrderId]);

  const summary = useMemo(() => {
    const totalOrders = filteredOrders.length;
    const totalSpent = filteredOrders.reduce(
      (sum, row) => sum + Number(row.order.paid_price || row.order.subtotal || 0),
      0
    );
    const totalSavings = filteredOrders.reduce((sum, row) => {
      const subtotal = Number(row.order.subtotal || 0);
      const paid = Number(row.order.paid_price || subtotal || 0);
      return sum + Math.max(paid - subtotal, 0);
    }, 0);

    const alertCount = filteredOrders.filter((row) =>
      String(row.status || "").toLowerCase().includes("alert")
    ).length;

    const trackingCount = filteredOrders.filter((row) =>
      String(row.status || "").toLowerCase().includes("track")
    ).length;

    const deliveredCount = filteredOrders.filter((row) =>
      String(row.status || "").toLowerCase().includes("deliver")
    ).length;

    return {
      totalOrders,
      activeAlerts: alertCount,
      totalSpent: formatMoney(totalSpent),
      potentialSavings: formatMoney(totalSavings),
      quickStats: [
        { label: "Price Drops", value: alertCount },
        { label: "Delivered", value: deliveredCount },
        { label: "Tracking", value: trackingCount },
      ],
    };
  }, [filteredOrders]);

  const retailerOptions = useMemo(() => {
    return [...new Set(mappedOrders.map((row) => String(row.store).toLowerCase()))].sort();
  }, [mappedOrders]);

  const statusOptions = useMemo(() => {
    return [...new Set(mappedOrders.map((row) => String(row.status).toLowerCase()))].sort();
  }, [mappedOrders]);

  return (
    <div className="page-content">
      {loading && <p>Loading orders...</p>}
      {errorMsg && <p style={{ color: "red" }}>{errorMsg}</p>}

      <div className="filter-bar">
        <input
          className="inner-search"
          value={query}
          onChange={(event) =>
            updateParams(searchParams, { q: event.target.value }, setSearchParams)
          }
          placeholder="Search orders, stores, or items..."
        />
        <select
          className="ghost-select"
          value={statusFilter}
          onChange={(event) =>
            updateParams(searchParams, { status: event.target.value }, setSearchParams)
          }
        >
          <option value="all">All Statuses</option>
          {statusOptions.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
        <select
          className="ghost-select"
          value={retailerFilter}
          onChange={(event) =>
            updateParams(searchParams, { retailer: event.target.value }, setSearchParams)
          }
        >
          <option value="all">All Stores</option>
          {retailerOptions.map((retailer) => (
            <option key={retailer} value={retailer}>
              {retailer}
            </option>
          ))}
        </select>
        <select
          className="ghost-select"
          value={dateFilter}
          onChange={(event) =>
            updateParams(searchParams, { date: event.target.value }, setSearchParams)
          }
        >
          <option value="all">All Dates</option>
          <option value="last30">Last 30 Days</option>
          <option value="last90">Last 90 Days</option>
        </select>
      </div>

      <div className="orders-layout">
        <div className="table-card">
          <table className="data-table">
            <thead>
              <tr>
                <th>ORDER ID</th>
                <th>STORE</th>
                <th>ITEMS</th>
                <th>PRICE PAID</th>
                <th>CURRENT PRICE</th>
                <th>SAVINGS</th>
                <th>STATUS</th>
                <th>ACTION</th>
              </tr>
            </thead>
            <tbody>
              {filteredOrders.length === 0 && !loading ? (
                <tr>
                  <td colSpan="8">
                    {mappedOrders.length === 0
                      ? "No orders found."
                      : "No orders match the current search or filters."}
                  </td>
                </tr>
              ) : (
                filteredOrders.map((row) => (
                  <tr key={row.order.id}>
                    <td>{row.id}</td>
                    <td>{row.store}</td>
                    <td>
                      {row.item}
                      {row.itemCount > 1 && (
                        <span style={{ marginLeft: "6px", fontSize: "0.75rem", color: "#6b7280" }}>
                          +{row.itemCount - 1} more
                        </span>
                      )}
                    </td>
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
                      <button
                        className="secondary-btn"
                        type="button"
                        onClick={() => setSelectedOrderId(row.order.id)}
                      >
                        {selectedOrderId === row.order.id ? "Viewing" : "View"}
                      </button>
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
            <span>Visible Orders</span>
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

          <div className="summary-divider"></div>

          <div className="summary-subtitle">Order Details</div>

          {!selectedOrder ? (
            <p style={{ color: "#6b7280", margin: 0 }}>
              Select an order to view tracking, return window, and item details.
            </p>
          ) : (
            <div style={{ display: "grid", gap: "12px" }}>
              <div className="summary-row">
                <span>Order</span>
                <strong>{selectedOrder.retailer_order_id}</strong>
              </div>
              <div className="summary-row">
                <span>Store</span>
                <strong>{selectedOrder.retailer}</strong>
              </div>
              <div className="summary-row">
                <span>Status</span>
                <strong>{selectedOrder.order_status}</strong>
              </div>
              <div className="summary-row">
                <span>Order Date</span>
                <strong>{formatDate(selectedOrder.order_date)}</strong>
              </div>
              <div className="summary-row">
                <span>Estimated Delivery</span>
                <strong>{formatDate(selectedOrder.estimated_delivery)}</strong>
              </div>
              <div className="summary-row">
                <span>Return Deadline</span>
                <strong>{formatDate(selectedOrder.return_deadline)}</strong>
              </div>
              <div className="summary-row">
                <span>Tracking Number</span>
                <strong>{selectedOrder.tracking_number || "Not available"}</strong>
              </div>
              <div className="summary-row">
                <span>Carrier</span>
                <strong>{selectedOrder.carrier || "Not available"}</strong>
              </div>
              <div className="summary-row">
                <span>Order URL</span>
                <strong>
                  {selectedOrder.order_url ? (
                    <a href={selectedOrder.order_url} target="_blank" rel="noreferrer">
                      Open order page
                    </a>
                  ) : (
                    "Not available"
                  )}
                </strong>
              </div>

              <div className="summary-divider"></div>

              <div className="summary-subtitle">Items</div>
              {(selectedOrder.items || []).length === 0 ? (
                <p style={{ color: "#6b7280", margin: 0 }}>No item details available.</p>
              ) : (
                (selectedOrder.items || []).map((item) => (
                  <div
                    key={item.id}
                    style={{
                      border: "1px solid #ececec",
                      borderRadius: "12px",
                      padding: "12px",
                      display: "grid",
                      gap: "8px",
                    }}
                  >
                    <strong>{item.product_name}</strong>
                    <div className="summary-row" style={{ marginBottom: 0 }}>
                      <span>Paid</span>
                      <strong>{formatMoney(item.paid_price)}</strong>
                    </div>
                    <div className="summary-row" style={{ marginBottom: 0 }}>
                      <span>Current</span>
                      <strong>{formatMoney(item.current_price ?? item.paid_price)}</strong>
                    </div>
                    <div className="summary-row" style={{ marginBottom: 0 }}>
                      <span>Monitoring</span>
                      <strong>{item.is_monitoring_active ? "Active" : "Stopped"}</strong>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
