# Phase 8 — Production Hardening and Handover

Phase 8 turns the verified v0.7 monitoring/history MVP into a reproducible v0.8
supervisor demonstration package.

## Added

- Same-origin HTTP and WebSocket endpoint discovery
- Vite development proxy for `/api`
- FastAPI serving of the production React build
- Optional temporary supervisor access token and HTTP-only cookie
- WebSocket cookie and origin checks
- Security-oriented response headers
- Liveness and detector/database readiness endpoints
- Docker multi-stage build and persistent Compose volume
- Windows setup, verification and single-terminal start scripts
- Root environment template and repository cleanup rules
- Root project-facing README
- Deployment, privacy, security and evaluation documentation
- Additional backend and frontend tests

## Preserved

- YOLO11s/OpenVINO model selection and warm-up
- Class thresholds and geometry filters
- Confidence-adaptive incident confirmation
- Two-second removal verification
- Evidence capture policy
- SQLite schema and existing session history
- CSV field names and timestamp behavior

## Validation baseline

- Backend: 32 tests passed
- Frontend: 8 tests passed
- Vite production build passed
- FastAPI tests passed with and without an existing frontend build

## Required manual acceptance

After installing the overlay, run `scripts\verify.ps1`, then perform one complete
live phone cycle using `scripts\start.ps1`. Confirm OpenVINO CPU, evidence,
resolution, history and CSV before tagging the repository.
