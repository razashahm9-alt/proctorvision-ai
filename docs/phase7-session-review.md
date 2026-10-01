# Phase 7 — Session History, Evidence Gallery, and CSV Export

Phase 7 adds the post-session review workflow while preserving the tested
OpenVINO detector, WebSocket transport, incident thresholds, SQLite database,
and existing evidence folders.

## Delivered features

- New **Session history** workspace in the React interface.
- Newest-first list of completed and active monitoring sessions.
- Full incident details: device, status, timestamps, duration, maximum
  confidence, and maximum simultaneous count.
- Annotated evidence gallery backed by the existing per-session JPEG files.
- One-click, Excel-friendly CSV export for every session.
- Safe handling of sessions that have no incidents or older incidents whose
  evidence files are unavailable.
- Responsive desktop, tablet, and mobile layouts.

## Backend endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/history/sessions` | Paginated session summaries |
| `GET /api/history/sessions/{session_id}` | Session and incident detail |
| `GET /api/history/incidents/{incident_id}/evidence` | Annotated evidence JPEG |
| `GET /api/history/sessions/{session_id}/export.csv` | Downloadable CSV audit log |

## Data safety

The update does not delete or migrate `data/proctorvision.db`. Existing session
records remain available. Evidence is read from the existing `evidence`
directory, and absolute evidence paths are never returned to the browser.

## Verification

```powershell
python -m pytest .\backend\tests -v
cd .\frontend
npm ci
npm test
npm run build
```

Expected results for the packaged release:

- Backend: `28 passed` (the existing Starlette deprecation warning is harmless).
- Frontend: `6 passed`.
- Vite production build completes successfully.
