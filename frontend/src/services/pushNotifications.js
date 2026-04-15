import { initializeApp, getApps } from "firebase/app";
import { getMessaging, getToken, isSupported } from "firebase/messaging";

const PUSH_TOKEN_KEY = "aftercart_push_token";

function getFirebaseConfig() {
  const config = {
    apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
    authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
    projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
    storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
    messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
    appId: import.meta.env.VITE_FIREBASE_APP_ID,
  };

  const requiredKeys = ["apiKey", "projectId", "messagingSenderId", "appId"];
  const hasAllRequired = requiredKeys.every((key) => Boolean(config[key]));
  return hasAllRequired ? config : null;
}

function detectBrowserName() {
  const userAgent = navigator.userAgent;
  if (userAgent.includes("Edg")) return "Edge";
  if (userAgent.includes("Chrome")) return "Chrome";
  if (userAgent.includes("Firefox")) return "Firefox";
  if (userAgent.includes("Safari")) return "Safari";
  return "Unknown";
}

function buildServiceWorkerUrl(config) {
  const url = new URL("/firebase-messaging-sw.js", window.location.origin);
  Object.entries(config).forEach(([key, value]) => {
    if (value) {
      url.searchParams.set(key, value);
    }
  });
  return url.toString();
}

export function getStoredPushToken() {
  return localStorage.getItem(PUSH_TOKEN_KEY);
}

export async function enableBrowserPush() {
  if (!(await isSupported())) {
    return { status: "unsupported", reason: "messaging-not-supported" };
  }

  const firebaseConfig = getFirebaseConfig();
  if (!firebaseConfig) {
    return { status: "unsupported", reason: "missing-firebase-config" };
  }

  if (!("Notification" in window) || !("serviceWorker" in navigator)) {
    return { status: "unsupported", reason: "browser-notification-api-missing" };
  }

  const permission = await Notification.requestPermission();
  if (permission !== "granted") {
    return { status: "blocked", reason: "notification-permission-denied" };
  }

  const serviceWorkerRegistration = await navigator.serviceWorker.register(
    buildServiceWorkerUrl(firebaseConfig),
  );
  const app = getApps().length > 0 ? getApps()[0] : initializeApp(firebaseConfig);
  const messaging = getMessaging(app);
  const token = await getToken(messaging, {
    vapidKey: import.meta.env.VITE_FIREBASE_VAPID_KEY,
    serviceWorkerRegistration,
  });

  if (!token) {
    return { status: "unsupported", reason: "token-unavailable" };
  }

  localStorage.setItem(PUSH_TOKEN_KEY, token);
  return {
    status: "enabled",
    token,
    platform: "web",
    browser: detectBrowserName(),
  };
}

export async function disableBrowserPush(unregisterFn) {
  const token = getStoredPushToken();
  if (token) {
    await unregisterFn(token);
    localStorage.removeItem(PUSH_TOKEN_KEY);
  }
  return { status: token ? "disabled" : "noop" };
}
