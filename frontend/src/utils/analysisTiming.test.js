import assert from "node:assert/strict";
import test from "node:test";

import {
  calculateRoundTripMs,
  isDelayedAnalysis,
} from "./analysisTiming.js";

test("calculates client round-trip latency without allowing negative values", () => {
  assert.equal(calculateRoundTripMs(100, 725.5), 625.5);
  assert.equal(calculateRoundTripMs(900, 850), 0);
  assert.equal(calculateRoundTripMs(undefined, 850), null);
});

test("marks only analysis above the warning threshold as delayed", () => {
  assert.equal(isDelayedAnalysis(2000), false);
  assert.equal(isDelayedAnalysis(2001), true);
  assert.equal(isDelayedAnalysis(null), false);
});
