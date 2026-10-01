# Phase 6.2 CPU Acceleration

Phase 6.2 addresses the delays measured in three browser recordings on an Intel
Core i5-6300U system with CPU-only PyTorch.

## What the recordings established

- Without screen recording, typical inference was roughly 400–800 ms.
- During recording, isolated predictions reached 3–4 seconds and one earlier
  run reached 16 seconds.
- YOLO classified the phone correctly once a result arrived; the main problem
  was CPU contention plus multi-frame confirmation latency.
- A delayed result was sometimes drawn over a newer live frame, making the box
  look stale even though its coordinates matched the analyzed JPEG.

## Corrections

- Prefer an FP32 OpenVINO export of the same YOLO11s model on Intel CPUs.
- Fall back automatically to the existing PyTorch model if a complete export
  is not present.
- Preload and warm the model during FastAPI startup instead of charging model
  initialization to the first monitoring frame.
- Report runtime, model, warm-up time, model inference, server processing, and
  browser round-trip latency.
- Send JPEG Blobs directly and keep one frame in flight.
- Draw detections over the exact returned frame rather than a newer live image.
- Confirm detections at 55% or higher on two of three frames; detections below
  55% still require three of five frames, while 80% remains instant.

## Installation on Windows

Keep both servers stopped, then run these commands from the activated virtual
environment:

```powershell
cd E:\ProctorVision_AI
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ProctorVision_AI_Phase6_2_CPU_Acceleration.zip" -DestinationPath "E:\ProctorVision_AI" -Force
python -m pip install -r .\backend\requirements-openvino.txt
python .\backend\scripts\prepare_openvino.py
python .\backend\scripts\benchmark_detector.py --runs 5
python -m pytest .\backend\tests -v
```

Then verify the frontend:

```powershell
cd E:\ProctorVision_AI\frontend
npm ci
npm test
npm run build
```

## Runtime verification

Start the backend from the project root. Startup completes after model warm-up:

```powershell
cd E:\ProctorVision_AI
python -m uvicorn app.main:app --app-dir backend --reload
```

In the other terminal, start Vite from the frontend directory:

```powershell
cd E:\ProctorVision_AI\frontend
npm run dev
```

Open `http://127.0.0.1:8000/api/detection/model`. The important fields are:

```text
runtime: OpenVINO CPU
using_fallback: false
loaded: true
```

For the final live check, start monitoring first and then start Game Bar
recording. When a box is visible, the camera panel should show **Matched
analyzed frame**. This confirms the box and image came from the same capture.

Do not commit Phase 6.2 until this accelerated live check passes.

## Safe fallback

If export is unavailable, the backend still runs with `yolo11s.pt`; the status
endpoint reports `PyTorch CPU` and `using_fallback: true`. To force that path in
one PowerShell terminal, set:

```powershell
$env:PROCTORVISION_PREFER_OPENVINO="false"
```

Restart the backend after changing the setting.

## Validation included in the package

- 24 backend tests cover configuration, runtime selection, safe fallback,
  warm-up arguments, geometry filters, incident lifecycle, evidence,
  WebSockets, and health.
- 4 frontend tests cover timing classification and box geometry.
- The Vite production build completes successfully.
