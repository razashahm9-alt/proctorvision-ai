# Phase 8.1 — Release Cleanup

Phase 8.1 prepares the verified Phase 8 handover build for a clean public
repository and reproducible release candidate.

## Changed

- Replaced assignment-focused README wording with a project-focused summary.
- Updated application, frontend, Docker and script version labels to 0.8.1.
- Added repository line-ending rules and a root changelog.
- Ignored runtime logs, SQLite sidecar files, recordings, downloaded model
  weights and generated model formats.
- Hardened the Docker build context against local environment variants and
  development artifacts.
- Documented the final recorded OpenVINO phone acceptance observation.

## Preserved

- YOLO11s/OpenVINO runtime selection and fallback behavior
- Detection thresholds and class geometry filters
- Confidence-adaptive temporal confirmation
- Device-removal verification
- Evidence, database, history and CSV behavior
- HTTP, WebSocket and access-gate API contracts

## Verification target

- Backend: 32 tests passed
- Frontend: 8 tests passed
- Vite production build passed
- Manual phone detection, removal, evidence, history and CSV cross-check passed

This is a release-cleanup overlay. Apply it only after Phase 8 is installed.
