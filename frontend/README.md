# ProctorVision AI Frontend

React and Vite monitoring console for the ProctorVision AI backend.

Version 0.8.1 includes two workspaces:

- **Live monitor** displays detections on the exact analyzed webcam frame and
  shows both end-to-end analysis latency and the active backend runtime.
- **Session history** reviews persisted sessions, annotated evidence images,
  incident timing, confidence, and downloadable CSV audit logs.

## Development

Keep the FastAPI server running on port 8000. In a second terminal:

```powershell
cd E:\ProctorVision_AI\frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173` and allow camera access when prompted.

Vite proxies `/api` HTTP and WebSocket traffic to port 8000. A production build
automatically uses the page origin and upgrades `https` to `wss`, so deployment
does not require hard-coded URLs. Copy `.env.example` only when the API is hosted
on a different origin.

When `PROCTORVISION_ACCESS_TOKEN` is configured on the backend, the frontend
shows a private supervisor access screen before mounting the monitoring console.

## Production verification

```powershell
npm test
npm run build
```

The generated `dist` directory is ignored by Git and can be regenerated.
