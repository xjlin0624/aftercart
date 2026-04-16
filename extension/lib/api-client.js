const DEFAULT_API_BASE = "http://localhost:8000/api";
const API_BASE_STORAGE_KEY = "apiBaseUrl";

function normalizeApiBaseUrl(value) {
  const raw = String(value || "").trim();
  const candidate = raw || DEFAULT_API_BASE;
  const url = new URL(candidate);

  url.hash = "";
  url.search = "";

  let pathname = url.pathname.replace(/\/+$/, "");
  pathname = pathname.replace(/\/api\/v1$/i, "/api");

  if (!pathname || pathname === "") {
    pathname = "/api";
  } else if (!/\/api$/i.test(pathname)) {
    pathname = `${pathname}/api`.replace(/\/{2,}/g, "/");
  }

  url.pathname = pathname;
  return url.toString().replace(/\/+$/, "");
}

function getApiOriginPattern(apiBase) {
  return `${new URL(apiBase).origin}/*`;
}

async function hasApiOriginPermission(apiBase) {
  if (!chrome.permissions?.contains) {
    return true;
  }

  return chrome.permissions.contains({
    origins: [getApiOriginPattern(apiBase)],
  });
}

async function requestApiOriginPermission(apiBase) {
  if (!chrome.permissions?.request) {
    return true;
  }

  if (await hasApiOriginPermission(apiBase)) {
    return true;
  }

  return chrome.permissions.request({
    origins: [getApiOriginPattern(apiBase)],
  });
}

export async function getApiBaseUrl() {
  const { [API_BASE_STORAGE_KEY]: storedBase } = await chrome.storage.local.get(
    API_BASE_STORAGE_KEY
  );
  return normalizeApiBaseUrl(storedBase);
}

export async function setApiBaseUrl(value) {
  const normalized = normalizeApiBaseUrl(value);
  const granted = await requestApiOriginPermission(normalized);

  if (!granted) {
    throw new Error(`Permission to reach ${new URL(normalized).origin} was denied`);
  }

  await chrome.storage.local.set({ [API_BASE_STORAGE_KEY]: normalized });
  return normalized;
}

export async function buildApiUrl(path) {
  const apiBase = await getApiBaseUrl();

  if (!(await hasApiOriginPermission(apiBase))) {
    throw new Error(`API host permission is missing for ${new URL(apiBase).origin}`);
  }

  const normalizedBase = apiBase.endsWith("/") ? apiBase : `${apiBase}/`;
  const normalizedPath = String(path || "").startsWith("/")
    ? String(path).slice(1)
    : String(path || "");

  return new URL(normalizedPath, normalizedBase).toString();
}

async function getAuthToken() {
  const { authToken } = await chrome.storage.local.get("authToken");
  return authToken;
}

async function apiRequest(method, path, body = null) {
  const token = await getAuthToken();
  if (!token) {
    throw new Error("NOT_AUTHENTICATED");
  }

  const url = await buildApiUrl(path);
  const opts = {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
  };

  if (body) {
    opts.body = JSON.stringify(body);
  }

  const res = await fetch(url, opts);

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

export const api = {
  get: (path) => apiRequest("GET", path),
  post: (path, body) => apiRequest("POST", path, body),
  put: (path, body) => apiRequest("PUT", path, body),
  del: (path) => apiRequest("DELETE", path),
};
