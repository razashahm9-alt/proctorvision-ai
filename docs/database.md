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
