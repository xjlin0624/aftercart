import { buildApiUrl } from "./api-client.js";

export async function login(email, password) {
  const url = await buildApiUrl("/auth/login");
  const res = await fetch(url, {
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
    user,
  });
  return user;
}

export async function logout() {
  await chrome.storage.local.remove(["authToken", "user"]);
}

export async function isAuthenticated() {
  const { authToken } = await chrome.storage.local.get("authToken");
  return !!authToken;
}
