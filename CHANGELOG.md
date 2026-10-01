# Changelog

All notable release-level changes to ProctorVision AI are recorded here.

## [0.8.1] - 2026-10-01

### Changed

- Reframed the root README around the product and verified engineering work.
- Added final OpenVINO phone-acceptance observations without presenting model
  confidence as accuracy.
- Aligned backend, frontend, Docker and startup metadata to version 0.8.1.
- Added consistent repository line-ending rules.

### Repository hygiene

- Excluded runtime logs, database sidecar files and local recordings.
- Excluded downloaded YOLO weights and generated model formats.
- Prevented local environment variants and model assets from entering the
  Docker build context.
- Added a Phase 8.1 release-cleanup record and installation guidance.

### Compatibility

- No detection thresholds, temporal confirmation rules, evidence behavior,
  database schema or API contracts changed in this release.

## [0.8.0] - 2026-09-30

- Added same-origin production frontend/API/WebSocket delivery.
- Added optional private supervisor access, readiness checks and security
  headers.
- Added Docker and Windows handover workflows.
- Added deployment, security, privacy, evaluation and third-party notices.
- Verified 32 backend tests, 8 frontend tests and the Vite production build.
