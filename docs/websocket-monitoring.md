# Real-Time WebSocket Monitoring

Phase 5 exposes the monitoring pipeline at:

```text
ws://127.0.0.1:8000/api/ws/monitoring
```

Swagger does not list WebSocket routes, so the React client will connect to
this address directly.

## Protocol

1. The server accepts the connection, creates an isolated database session,
   starts a monitoring session, and sends `session_started`.
2. The browser sends compressed webcam frames as binary JPEG data.
3. The server decodes the frame, runs YOLO in a worker thread, and passes the
   result through the temporal incident engine.
4. The server replies with `frame_result`, containing raw detections,
   frontend-ready monitoring state, an increasing `sequence`, and measured
   `server_processing_ms`.
5. The browser sends `{"type":"stop"}` when monitoring ends.
6. The server sends `session_finished`, closes the socket, and safely releases
   database resources.

The server also accepts `{"type":"ping"}` and replies with `pong`.

## Frontend behavior fields

- `monitoring.should_block_preview`: apply the blocked/blurred camera overlay.
- `monitoring.play_alert_sound`: play one beep for a newly confirmed incident.
- `monitoring.active_incidents`: render device-specific alert messages.
- `monitoring.events`: update the incident counter and evidence gallery.

Each raw detection also contains the analyzed frame size, bounding-box
coordinates, model name, runtime, and model inference time. The React client
keeps the sent JPEG until its response arrives. When detections exist, that
exact analyzed JPEG is displayed below the mirrored boxes, preventing slow
results from being drawn over a newer live frame.

## Reliability and safety

- Maximum compressed frame size: 3 MB.
- Invalid frames and invalid control messages produce recoverable JSON errors.
- Missing model/runtime failures produce a non-recoverable error and code 1011.
- Browser disconnects automatically finish the database monitoring session.
- Every WebSocket connection receives independent temporal state and a separate
  SQLAlchemy session.
