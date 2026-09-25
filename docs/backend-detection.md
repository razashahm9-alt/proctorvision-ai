# Backend Detection Service

The FastAPI backend loads `yolo11s.pt` lazily, so health checks and automated
tests do not allocate the model until detection is requested.

## Endpoints

- `GET /api/health` reports API and detector state.
- `GET /api/detection/model` reports whether the configured weights exist.
- `POST /api/detection/model/load` loads and validates the model.
- `POST /api/detection/frame` accepts one JPEG, PNG, or WebP frame.

## Detection policy

The service keeps the validated standalone settings: 416-pixel inference,
CPU execution, 0.25 raw confidence, and class-specific confidence thresholds.
It adds geometry validation for laptop and TV boxes. This rejects narrow edge
regions like the false laptop boxes found in the first evidence session while
keeping normal open-laptop and widescreen-monitor shapes.

Temporal confirmation, incident creation, evidence saving, sound alerts, and
WebSocket streaming will be connected after this stateless frame endpoint is
validated.
