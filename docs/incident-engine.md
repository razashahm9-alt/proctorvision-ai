# Incident Management Engine

Phase 6.2 converts individual YOLO frame results into stable monitoring events
with confidence-aware confirmation.

## Lifecycle

1. A monitoring session is created in SQLite.
2. Each supported device class has an independent five-frame confidence history.
3. Confirmation adapts to detection strength:
   - Confidence of 80% or higher: confirm on the current frame.
   - Confidence of 55% or higher: require two strong detections in three frames.
   - Other accepted detections: retain the original three-of-five rule.
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

The adaptive paths do not lower YOLO's class thresholds or bypass the existing
geometry validation filters. The 55% path covers the 55–67% phone detections
measured in live recordings while still requiring two matching frames.
