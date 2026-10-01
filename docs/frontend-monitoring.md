# React Monitoring Console

Phase 6.2 adds a responsive React/Vite monitoring interface with frame-aligned
detection boxes and measured end-to-end analysis latency.

## User flow

1. The user presses **Start monitoring**.
2. The browser requests webcam permission and opens the live preview.
3. The client connects to the FastAPI WebSocket endpoint.
4. A 416-pixel-wide JPEG frame is considered every 250 ms, with backpressure so a
   new frame is never queued while the previous frame is still processing.
5. Accepted detections display the exact analyzed JPEG with mirrored, labeled
   bounding boxes, so delayed results cannot drift over the live preview.
6. Confirmed incidents blur and block the preview, show the detected device,
   play a short generated beep, and update the activity timeline.
7. **Stop monitoring** sends the server's stop control message, releases the
   webcam, and completes the database session.

## Performance decisions

- Frames are resized to YOLO's configured 416-pixel input width before
  transmission, avoiding an unnecessary larger JPEG and second resize.
- JPEG quality is 72%, balancing detector detail and payload size.
- Only one frame can be awaiting a server response at a time.
- The 250 ms capture check reduces idle time between completed CPU inferences
  without creating a server-side frame backlog.
- The browser sends the JPEG Blob directly, avoiding an extra ArrayBuffer copy.
- Bounding boxes use the backend's exact analyzed JPEG and an SVG `slice`
  transform that matches the camera's `object-fit: cover` layout.
- The dashboard separates end-to-end analysis latency from model inference and
  displays the backend runtime (`OpenVINO CPU` or `PyTorch CPU`).
- Alert audio is generated with the Web Audio API, so no external sound file is
  required.
- Browser and WebSocket resources are released on stop, disconnect, or page
  unmount.

## Environment

The optional `VITE_WS_URL` variable overrides the local WebSocket address.
For an HTTPS deployment, use a secure `wss://` endpoint.
