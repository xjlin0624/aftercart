const API_BASE = "http://localhost:8000/api/v1"; // TODO: make configurable

async function getAuthToken() {
  const { authToken } = await chrome.storage.local.get("authToken");
  return authToken;
}

async function apiRequest(method, path, body = null) {
  const token = await getAuthToken();
  if (!token) {
    throw new Error("NOT_AUTHENTICATED");
  }

  const opts = {
    method,
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
    },
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);

  if (res.status === 401) {
    await chrome.storage.local.remove("authToken");
    throw new Error("TOKEN_EXPIRED");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// Convenience wrappers
const api = {
  get:  (path)       => apiRequest("GET", path),
  post: (path, body) => apiRequest("POST", path, body),
  put:  (path, body) => apiRequest("PUT", path, body),
  del:  (path)       => apiRequest("DELETE", path),
};
