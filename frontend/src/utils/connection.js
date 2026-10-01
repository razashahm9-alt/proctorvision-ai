const LOCAL_WEBSOCKET_FALLBACK = "ws://127.0.0.1:8000/api/ws/monitoring";


export function buildWebSocketUrl(explicitUrl = "", locationLike = null) {
  if (explicitUrl) return String(explicitUrl);

  const location = locationLike || globalThis?.location;
  if (!location?.host) return LOCAL_WEBSOCKET_FALLBACK;
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${location.host}/api/ws/monitoring`;
}


export function monitoringWebSocketUrl() {
  return buildWebSocketUrl(import.meta.env?.VITE_WS_URL || "");
}
