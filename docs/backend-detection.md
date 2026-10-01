# Backend Detection Service

The FastAPI backend now preloads and warms the selected YOLO11s runtime during
application startup. This moves one-time model initialization out of the first
live monitoring frame.

If `yolo11s_openvino_model` contains a complete `.xml`/`.bin` export, the app
uses OpenVINO CPU inference automatically. Otherwise it safely falls back to
`yolo11s.pt` through PyTorch. The model status endpoint reports the selected
path, runtime, warm-up time, and whether fallback is active.

## Endpoints

- `GET /api/health` reports API and detector state.
- `GET /api/detection/model` reports whether the configured weights exist.
- `POST /api/detection/model/load` loads and validates the model.
- `POST /api/detection/frame` accepts one JPEG, PNG, or WebP frame.

## Intel CPU preparation

From the project root with the virtual environment active:

```powershell
python -m pip install -r .\backend\requirements-openvino.txt
python .\backend\scripts\prepare_openvino.py
python .\backend\scripts\benchmark_detector.py --runs 5
```

The export is FP32 at 416 pixels, preserving YOLO11s weights and avoiding an
INT8 accuracy tradeoff.

## Detection policy

The service keeps the validated standalone settings: 416-pixel inference,
CPU execution, 0.25 raw confidence, and class-specific confidence thresholds.
It adds geometry validation for laptop and TV boxes. This rejects narrow edge
regions like the false laptop boxes found in the first evidence session while
keeping normal open-laptop and widescreen-monitor shapes.

Temporal confirmation, incident creation, evidence saving, sound alerts, and
WebSocket streaming use this shared preloaded detector.
