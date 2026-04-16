import React, { useState } from "react";
import { login, signup } from "../api";

export default function Login({ onSuccess }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function switchMode(next) {
    setMode(next);
    setError("");
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (mode === "signup") {
        await signup(email, password, displayName);
        // After signup, log in automatically
        await login(email, password);
      } else {
        await login(email, password);
      }
      onSuccess();
    } catch (err) {
      setError(err.message || (mode === "signup" ? "Sign up failed" : "Login failed"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-form" onSubmit={handleSubmit}>
        <h2>{mode === "signup" ? "Create an AfterCart Account" : "Sign In to AfterCart"}</h2>

        {error && <p style={{ color: "red" }}>{error}</p>}

        {mode === "signup" && (
          <div className="form-group">
            <label>Display Name (optional)</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Your name"
            />
          </div>
        )}

        <div className="form-group">
          <label>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
          />
        </div>

        <div className="form-group">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        <button className="primary-btn" type="submit" disabled={loading}>
          {loading
            ? mode === "signup" ? "Creating account..." : "Signing in..."
            : mode === "signup" ? "Create Account" : "Sign In"}
        </button>

        <p style={{ marginTop: "16px", textAlign: "center", fontSize: "0.9rem", color: "#6b7280" }}>
          {mode === "login" ? (
            <>Don't have an account?{" "}
              <button type="button" className="plain-link-btn" onClick={() => switchMode("signup")}>
                Sign up
              </button>
            </>
          ) : (
            <>Already have an account?{" "}
              <button type="button" className="plain-link-btn" onClick={() => switchMode("login")}>
                Sign in
              </button>
            </>
          )}
        </p>
      </form>
    </div>
  );
}
