import { API_BASE } from "./api-client.js";

async function login(email, password) {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Login failed");
  }

  const { access_token, user } = await res.json();
  await chrome.storage.local.set({
    authToken: access_token,
    user: user,
  });
  return user;
}

async function logout() {
  await chrome.storage.local.remove(["authToken", "user"]);
}

export async function isAuthenticated() {
  const { authToken } = await chrome.storage.local.get("authToken");
  return !!authToken;
}
