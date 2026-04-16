import React, { useEffect, useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import Dashboard from "./pages/Dashboard";
import Orders from "./pages/Orders";
import Alerts from "./pages/Alerts";
import Savings from "./pages/Savings";
import Subscriptions from "./pages/Subscriptions";
import Settings from "./pages/Settings";
import Login from "./pages/Login";
import { logout } from "./api";

export default function App() {
  const [authed, setAuthed] = useState(() => !!localStorage.getItem("aftercart_token"));

  useEffect(() => {
    function handleForcedLogout() {
      setAuthed(false);
    }
    window.addEventListener("aftercart:logout", handleForcedLogout);
    return () => window.removeEventListener("aftercart:logout", handleForcedLogout);
  }, []);

  async function handleLogout() {
    await logout();
    setAuthed(false);
  }

  if (!authed) {
    return <Login onSuccess={() => setAuthed(true)} />;
  }

  return (
    <BrowserRouter>
      <div className="app-shell">
        <Sidebar />
        <div className="main-shell">
          <Topbar onLogout={handleLogout} />
          <main className="page-shell">
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/orders" element={<Orders />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/savings" element={<Savings />} />
              <Route path="/subscriptions" element={<Subscriptions />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}