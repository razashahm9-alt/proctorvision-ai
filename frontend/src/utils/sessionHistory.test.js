import test from "node:test";
import assert from "node:assert/strict";

import {
  buildApiEndpoint,
  buildServerAssetUrl,
  formatConfidence,
  formatDuration,
} from "./sessionHistory.js";

test("builds backend history and evidence URLs safely", () => {
  const base = "http://127.0.0.1:8000/api/";
  assert.equal(
    buildApiEndpoint("/history/sessions", base),
    "http://127.0.0.1:8000/api/history/sessions",
  );
  assert.equal(
    buildServerAssetUrl("/api/history/incidents/EVT-1/evidence", base),
    "http://127.0.0.1:8000/api/history/incidents/EVT-1/evidence",
  );
  assert.equal(
    buildApiEndpoint("history/sessions", "/api"),
    "/api/history/sessions",
  );
});

test("formats audit durations and confidence for the review UI", () => {
  assert.equal(formatDuration(5.4), "5s");
  assert.equal(formatDuration(125), "2m 5s");
  assert.equal(formatDuration(null), "In progress");
  assert.equal(formatConfidence(0.864), "86%");
});
