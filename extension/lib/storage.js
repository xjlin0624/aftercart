const DEFAULTS = {
  enablePriceAlerts: true,
  enableDeliveryAlerts: true,
  enableSubscriptionAlerts: true,
  checkIntervalMinutes: 60,
};

async function getPreferences() {
  const { preferences } = await chrome.storage.sync.get("preferences");
  return { ...DEFAULTS, ...preferences };
}

async function setPreferences(updates) {
  const current = await getPreferences();
  const merged = { ...current, ...updates };
  await chrome.storage.sync.set({ preferences: merged });
  return merged;
}
