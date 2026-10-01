export const DEFAULT_API_BASE_URL = "/api";

export function normalizeApiBaseUrl(value = DEFAULT_API_BASE_URL) {
  return String(value || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

export function buildApiEndpoint(path, baseUrl = DEFAULT_API_BASE_URL) {
  const base = normalizeApiBaseUrl(baseUrl);
  return `${base}/${String(path).replace(/^\/+/, "")}`;
}

export function buildServerAssetUrl(path, baseUrl = DEFAULT_API_BASE_URL) {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  const normalizedBase = normalizeApiBaseUrl(baseUrl);
  const fallbackOrigin = "http://127.0.0.1:8000";
  const browserOrigin = globalThis?.location?.origin || fallbackOrigin;
  const origin = /^https?:\/\//i.test(normalizedBase)
    ? new URL(normalizedBase).origin
    : browserOrigin;
  return new URL(path, `${origin}/`).toString();
}

export function formatDuration(totalSeconds) {
  if (totalSeconds === null || totalSeconds === undefined) return "In progress";
  const seconds = Math.max(0, Math.round(Number(totalSeconds) || 0));
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const remainder = seconds % 60;
  if (hours) return `${hours}h ${minutes}m ${remainder}s`;
  if (minutes) return `${minutes}m ${remainder}s`;
  return `${remainder}s`;
}

export function formatConfidence(value) {
  return `${Math.round(Math.max(0, Math.min(1, Number(value) || 0)) * 100)}%`;
}
