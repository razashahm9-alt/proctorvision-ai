# Deployment Guide

This guide deploys ProctorVision AI as one container containing the production
React build, FastAPI, OpenVINO detector, SQLite database and evidence service.

## Recommended demonstration topology

Use one x86-64 host with:

- 4 vCPU and 8 GB RAM preferred
- 2 dedicated vCPU and 4 GB RAM as a budget starting point
- At least 10 GB persistent storage
- A deployment region close to the reviewer
- HTTPS termination with WebSocket support
- One application instance and one Uvicorn worker

The exact instance must be benchmarked. Shared/free compute can be slower than
the development laptop even when its advertised CPU generation is newer.

## Why one worker

The current baseline keeps the loaded model in process memory and uses SQLite
plus per-WebSocket incident state. Multiple Uvicorn workers would each load a
separate model and maintain separate state. Keep one worker for the supervisor
demo. Multi-user scaling requires shared storage/state and an explicit inference
queue.

## Build locally

```powershell
Copy-Item .env.example .env
# Edit .env and set a long PROCTORVISION_ACCESS_TOKEN.
docker compose build
docker compose up
```

Confirm:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/ready
```

`/api/health` reports process liveness. `/api/ready` returns HTTP 200 only after
the database is reachable and the detector has loaded; it returns 503 otherwise.

## Hosting-platform configuration

Build using the repository `Dockerfile` and expose container port `8000`.
Configure:

```dotenv
PROCTORVISION_ENVIRONMENT=production
PROCTORVISION_ACCESS_TOKEN=<long-random-temporary-secret>
PROCTORVISION_SECURE_COOKIES=true
PROCTORVISION_PRELOAD_MODEL=true
PROCTORVISION_PREFER_OPENVINO=true
PROCTORVISION_DATABASE_PATH=/app/storage/data/proctorvision.db
PROCTORVISION_EVIDENCE_DIRECTORY=/app/storage/evidence
```

Attach persistent storage at `/app/storage`. Without it, session history and
evidence can disappear after a restart or redeployment.

Set the liveness path to `/api/health` and allow at least 90 seconds for first
startup because model preparation/loading and warm-up take longer than normal
HTTP startup.

## HTTPS and WebSockets

The browser derives its API and WebSocket endpoints from the page origin:

- `https://demo.example.com/api/...`
- `wss://demo.example.com/api/ws/monitoring`

The hosting proxy must preserve WebSocket upgrade headers and forward the
original scheme/host. The Docker command enables Uvicorn proxy headers.

Camera access on a public domain requires HTTPS. Plain HTTP is appropriate only
for loopback development such as `http://127.0.0.1`.

## Pre-demonstration validation

1. Load `/api/health` and `/api/ready`.
2. Sign in through the access screen.
3. Confirm **OpenVINO CPU** after starting monitoring.
4. Run an empty-scene test for at least 20 seconds.
5. Run one phone detection and removal cycle.
6. Stop the session and confirm evidence/history/CSV.
7. Restart the container and confirm that the earlier session still exists.
8. Measure latency from the supervisor's actual network.

## Backup

Back up both resources together while the application is stopped:

- `/app/storage/data/proctorvision.db`
- `/app/storage/evidence/`

The database stores evidence paths, so restoring only one resource creates an
incomplete audit archive.

## Scaling beyond the demonstration

Before supporting simultaneous exam candidates:

- Replace SQLite with PostgreSQL.
- Store evidence in private object storage.
- Move incident/session state to a shared service.
- Add user identity and role-based authorization.
- Add an inference queue with latest-frame prioritization.
- Load-test WebSocket concurrency and CPU saturation.
- Define retention, deletion, encryption and backup policies.
