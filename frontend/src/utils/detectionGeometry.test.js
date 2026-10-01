import assert from "node:assert/strict";
import test from "node:test";

import { mirrorDetectionBox } from "./detectionGeometry.js";

test("mirrors backend coordinates to match the mirrored webcam preview", () => {
  assert.deepEqual(
    mirrorDetectionBox({ x1: 100, y1: 80, x2: 260, y2: 350 }, 640, 480),
    { x: 380, y: 80, width: 160, height: 270 },
  );
});

test("clamps malformed coordinates to the analyzed frame", () => {
  assert.deepEqual(
    mirrorDetectionBox({ x1: -20, y1: -5, x2: 700, y2: 500 }, 640, 480),
    { x: 0, y: 0, width: 640, height: 480 },
  );
});
