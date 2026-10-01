# SQLite Monitoring Database

ProctorVision AI stores monitoring sessions and violation incidents in
`data/proctorvision.db`. The database file is runtime data and is excluded from
Git by the existing `*.db` rule.

## Monitoring sessions

Each session stores a unique ID, start and end times, lifecycle status, and the
number of incidents created during the session.

## Incidents

Each incident belongs to one monitoring session and stores the device key,
display name, maximum confidence, maximum simultaneous count, detection and
clear times, duration, evidence path, and final status.

Foreign-key enforcement is enabled for SQLite. Deleting a session therefore
also removes its associated incidents. On normal shutdown, any incident that
is still active is closed with the `Stopped` status.

The database tables are created safely when FastAPI starts. Existing records
are preserved because initialization uses SQLAlchemy `create_all` rather than
dropping or recreating tables.

## Session-review API

Version 0.7.0 exposes the stored data without revealing local filesystem paths:

- `GET /api/history/sessions` lists newest sessions first.
- `GET /api/history/sessions/{session_id}` returns a complete incident timeline.
- `GET /api/history/incidents/{incident_id}/evidence` serves an annotated image.
- `GET /api/history/sessions/{session_id}/export.csv` downloads an Excel-friendly
  UTF-8 CSV audit log.

Evidence responses are restricted to files inside the configured evidence
directory. Missing legacy evidence is reported in the UI without preventing
the rest of the session from loading.
