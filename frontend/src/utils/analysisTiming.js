export function calculateRoundTripMs(sentAt, receivedAt) {
  if (!Number.isFinite(sentAt) || !Number.isFinite(receivedAt)) return null;
  return Math.max(0, receivedAt - sentAt);
}

export function isDelayedAnalysis(roundTripMs, thresholdMs = 2000) {
  return Number.isFinite(roundTripMs) && roundTripMs > thresholdMs;
}
