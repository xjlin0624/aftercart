import React, { useState } from "react";
import { login, signup } from "../api";

function friendlyError(message, mode) {
  if (!message) return mode === "signup" ? "Sign up failed. Please try again." : "Sign in failed. Please try again.";

  const lower = message.toLowerCase();

  // 401 / wrong credentials
  if (lower.includes("invalid credentials")) return "Incorrect email or password.";

  // 403 / disabled account
  if (lower.includes("account disabled")) return "Your account has been disabled. Please contact support.";

  // 409 / duplicate email on signup
  if (lower.includes("already registered")) return "An account with this email already exists. Try signing in.";

  // 422 Pydantic validation errors arrive as a JSON-stringified array
  if (lower.includes("password must")) {
    // Extract the first readable message from Pydantic's detail array if present
    try {
      const parsed = JSON.parse(message);
      if (Array.isArray(parsed)) {
        const msg = parsed[0]?.msg || "";
        return msg.replace(/^value error,\s*/i, "");
      }
    } catch {
      // message was already a plain string
    }
    return message;
  }

  // Network / server errors — don't show raw JSON or stack
  if (lower.includes("failed to fetch") || lower.includes("networkerror") || lower.includes("load failed") || lower.startsWith("{") || lower.startsWith("[") || lower.includes("request failed")) {
    return mode === "signup" ? "Sign up failed. Please try again." : "Sign in failed. Please try again.";
  }

  return message;
}

function getPasswordErrors(password) {
  const errors = [];
  if (password.length > 0 && password.length < 8) errors.push("At least 8 characters");
  if (password.length > 0 && !/[A-Z]/.test(password)) errors.push("At least one uppercase letter");
  if (password.length > 0 && !/[0-9]/.test(password)) errors.push("At least one number");
  return errors;
}

export default function Login({ onSuccess }) {
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [passwordTouched, setPasswordTouched] = useState(false);

  const passwordErrors = mode === "signup" ? getPasswordErrors(password) : [];
  const passwordValid = mode === "signup" ? passwordErrors.length === 0 && password.length >= 8 : true;

  function switchMode(next) {
    setMode(next);
    setError("");
    setPasswordTouched(false);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (mode === "signup" && !passwordValid) {
      setPasswordTouched(true);
      return;
    }
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
      setError(friendlyError(err.message, mode));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-page">
      <form className="login-form" onSubmit={handleSubmit}>
        <h2>{mode === "signup" ? "Create an AfterCart Account" : "Sign In to AfterCart"}</h2>

        {mode === "login" && (
          <div className="login-intro">
            <p className="login-tagline">Your post-purchase command center. AfterCart keeps watch after checkout so you don&apos;t have to.</p>
            <ul className="login-feature-list">
              <li>Orders from all your retailers, in one place</li>
              <li>Price-drop alerts after you buy</li>
              <li>Delivery delay detection, automatically</li>
              <li>Subscription and recurring charge tracking</li>
            </ul>
          </div>
        )}

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
            onBlur={() => setPasswordTouched(true)}
            required
          />
          {mode === "signup" && passwordTouched && passwordErrors.length > 0 && (
            <ul style={{ margin: "6px 0 0", padding: "0 0 0 18px", color: "red", fontSize: "0.82rem" }}>
              {passwordErrors.map((msg) => <li key={msg}>{msg}</li>)}
            </ul>
          )}
          {mode === "signup" && !passwordTouched && (
            <p style={{ margin: "4px 0 0", fontSize: "0.82rem", color: "#6b7280" }}>
              Min 8 characters, one uppercase letter, one number
            </p>
          )}
        </div>

        <button className="primary-btn" type="submit" disabled={loading}>
          {loading
            ? mode === "signup" ? "Creating account..." : "Signing in..."
            : mode === "signup" ? "Create Account" : "Sign In"}
        </button>

        <p style={{ marginTop: "16px", textAlign: "center", fontSize: "0.9rem", color: "#6b7280" }}>
          {mode === "login" ? (
            <>Don&apos;t have an account?{" "}
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
