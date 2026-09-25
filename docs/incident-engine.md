# Incident Management Engine

Phase 4 converts individual YOLO frame results into stable monitoring events.

## Lifecycle

1. A monitoring session is created in SQLite.
2. Each supported device class has an independent five-frame history.
3. A device becomes a confirmed incident after appearing in at least three of
   the five most recent frames.
4. One annotated JPEG is saved when the incident starts.
5. Repeated detections update peak confidence and maximum simultaneous count
   without creating duplicate incidents.
6. The incident remains active during brief missed detections.
7. It resolves only after the device has remained absent for two seconds.
8. Ending monitoring safely marks any remaining active incidents as stopped.

## Frontend control state

`MonitoringFrameState` supplies the values needed by the future WebSocket UI:

- `should_block_preview`: blur/block the webcam preview while any incident is active.
- `play_alert_sound`: play one beep only when a new incident is confirmed.
- `active_incident_ids`: all currently active device incidents.
- `active_incidents`: device names, alert text, confidence, count, and evidence.
- `events`: incident transitions created by the current frame.

Phone, laptop, and TV/monitor states are independent. If a phone and laptop
appear together, the database records two incidents under the same monitoring
session.
