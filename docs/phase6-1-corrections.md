# Phase 6.1 Corrections

Phase 6.1 responds to the first complete browser recordings of the monitoring
console.

## Observed problems

- The React preview did not render the bounding boxes returned by the backend.
- CPU inference reached 2.4–3.4 seconds while screen recording was active.
- A fixed three-of-five confirmation rule multiplied that delay and sometimes
  produced an alert after the device had already left the camera.
- Sending 640-pixel JPEGs added work even though YOLO analyzes a 416-pixel input.

## Corrections

- Render live SVG boxes and confidence labels from the backend coordinates.
- Mirror the horizontal coordinates so boxes align with the mirrored preview.
- Use `preserveAspectRatio="xMidYMid slice"` to match `object-fit: cover`.
- Send 416-pixel-wide JPEGs and check for the next frame every 250 ms.
- Keep one frame in flight at a time so slow inference cannot create a backlog.
- Add confidence-aware confirmation without lowering detector thresholds:
  - 80% or higher: current-frame confirmation.
  - 65% or higher: two strong detections within three frames.
  - Lower accepted confidence: original three detections within five frames.
- Preserve the two-second device-removal verification and all evidence/database
  behavior.

## Validation

- 20 backend tests cover detection filters, SQLite lifecycle, evidence writing,
  adaptive confirmation, WebSocket cleanup, and API health.
- 2 frontend tests verify mirrored and clamped box geometry.
- The Vite production build completes successfully.

Actual inference time still depends on the laptop CPU. Measure the corrected
build once without screen recording and once with recording enabled; the latter
can substantially increase CPU latency on older processors.
