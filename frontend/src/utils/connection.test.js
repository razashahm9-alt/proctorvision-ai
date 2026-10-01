import assert from "node:assert/strict";
import test from "node:test";

import { buildWebSocketUrl } from "./connection.js";


test("builds secure same-origin WebSocket URLs for deployment", () => {
  assert.equal(
    buildWebSocketUrl("", { protocol: "https:", host: "demo.example.com" }),
    "wss://demo.example.com/api/ws/monitoring",
  );
  assert.equal(
    buildWebSocketUrl("", { protocol: "http:", host: "127.0.0.1:5173" }),
    "ws://127.0.0.1:5173/api/ws/monitoring",
  );
});


test("honors an explicit WebSocket endpoint", () => {
  assert.equal(
    buildWebSocketUrl("wss://api.example.com/live", null),
    "wss://api.example.com/live",
  );
});
