import { useState } from "react";

import StatusBadge from "./components/StatusBadge.jsx";
import AccessGate from "./components/AccessGate.jsx";
import DetectionOverlay from "./components/DetectionOverlay.jsx";
import SessionHistory from "./components/SessionHistory.jsx";
import { useDemoAccess } from "./hooks/useDemoAccess.js";
import { useProctorMonitoring } from "./hooks/useProctorMonitoring.js";
import { isDelayedAnalysis } from "./utils/analysisTiming.js";

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <svg viewBox="0 0 48 48" role="img">
        <path d="M24 4 41 10v12c0 10.4-6.9 18.6-17 22C13.9 40.6 7 32.4 7 22V10L24 4Z" />
        <path d="M14 24c2.8-4.4 6.1-6.6 10-6.6s7.2 2.2 10 6.6c-2.8 4.4-6.1 6.6-10 6.6S16.8 28.4 14 24Z" />
        <circle cx="24" cy="24" r="3.7" />
      </svg>
    </span>
  );
}

function MetricCard({ label, value, detail, accent = false }) {
  return (
    <article className={`metric-card${accent ? " metric-card--accent" : ""}`}>
      <p>{label}</p>
      <strong>{value}</strong>
      <span>{detail}</span>
    </article>
  );
}

function DeviceIcon({ type }) {
  const symbol = type === "cell phone" ? "▯" : type === "laptop" ? "▰" : "▣";
  return <span className="device-icon" aria-hidden="true">{symbol}</span>;
}

function EmptyActivity() {
  return (
    <div className="empty-state">
      <span className="empty-state__ring" aria-hidden="true">✓</span>
      <strong>No incidents recorded</strong>
      <p>Confirmed device events will appear here during this session.</p>
    </div>
  );
}

export default function App() {
  const [activeView, setActiveView] = useState("monitor");
  const access = useDemoAccess();
  const monitoring = useProctorMonitoring();
  const activeNames = monitoring.activeIncidents
    .map((incident) => incident.device_name)
    .join(", ");
  const canStart = ["idle", "error"].includes(monitoring.status);
  const modelLabel = monitoring.modelName.replace(/^yolo/i, "YOLO");

  if (access.state !== "unlocked") {
    return <AccessGate access={access} />;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="ProctorVision AI home">
          <BrandMark />
          <span>
            <strong>ProctorVision</strong>
            <small>AI monitoring</small>
          </span>
        </a>
        <nav className="view-navigation" aria-label="Application sections">
          <button
            className={activeView === "monitor" ? "is-active" : ""}
            type="button"
            onClick={() => setActiveView("monitor")}
          >
            Live monitor
          </button>
          <button
            className={activeView === "history" ? "is-active" : ""}
            type="button"
            onClick={() => setActiveView("history")}
            disabled={monitoring.isActive}
            title={
              monitoring.isActive
                ? "Stop monitoring before opening session history."
                : "Review saved sessions"
            }
          >
            Session history
          </button>
        </nav>
        <div className="topbar__right">
          <span className="privacy-pill">Human-reviewed alerts</span>
          <StatusBadge status={monitoring.status} />
        </div>
      </header>

      <main id="top" className="page-content">
        {activeView === "monitor" ? (
          <>
        <section className="intro">
          <div>
            <span className="eyebrow">Live proctoring workspace</span>
            <h1>Device Monitoring Console</h1>
            <p>
              Detect prohibited electronics in real time with temporal
              confirmation and auditable incident evidence.
            </p>
          </div>
          <div className="session-chip" title={monitoring.sessionId || "No active session"}>
            <span>Session</span>
            <strong>{monitoring.sessionId || "Not started"}</strong>
          </div>
        </section>

        <section className="metrics" aria-label="Monitoring metrics">
          <MetricCard
            label="Confirmed incidents"
            value={monitoring.incidentCount}
            detail="Current session"
            accent={monitoring.incidentCount > 0}
          />
          <MetricCard
            label="Visible devices"
            value={monitoring.visibleDeviceCount}
            detail="Latest analyzed frame"
          />
          <MetricCard
            label="Analysis latency"
            value={monitoring.roundTripMs === null ? "—" : `${Math.round(monitoring.roundTripMs)} ms`}
            detail={
              monitoring.inferenceMs === null
                ? `${modelLabel} · ${monitoring.runtime}`
                : `${Math.round(monitoring.inferenceMs)} ms model · ${monitoring.runtime}`
            }
            accent={isDelayedAnalysis(monitoring.roundTripMs)}
          />
          <MetricCard
            label="Evidence policy"
            value="Enabled"
            detail="One image per incident"
          />
        </section>

        {monitoring.error && (
          <div className="error-banner" role="alert">
            <strong>Monitoring notice</strong>
            <span>{monitoring.error}</span>
          </div>
        )}

        <section className="workspace-grid">
          <article className="camera-card">
            <div className="panel-heading">
              <div>
                <span className="panel-kicker">Camera 01</span>
                <h2>Live webcam</h2>
              </div>
              <span className={`live-indicator${monitoring.status === "monitoring" ? " is-live" : ""}`}>
                <span />
                {monitoring.status === "monitoring" ? "Live" : "Offline"}
              </span>
            </div>

            <div className={`camera-stage${monitoring.isBlocking ? " is-blocked" : ""}`}>
              <video
                ref={monitoring.videoRef}
                className="camera-media camera-video"
                autoPlay
                muted
                playsInline
                aria-label="Live webcam preview"
              />
              {monitoring.analyzedFrameUrl && (
                <img
                  className="camera-media camera-analyzed-frame"
                  src={monitoring.analyzedFrameUrl}
                  alt=""
                  aria-hidden="true"
                />
              )}
              <canvas ref={monitoring.canvasRef} className="capture-canvas" />
              <DetectionOverlay
                detections={monitoring.detections}
                imageWidth={monitoring.detectionFrameSize.width}
                imageHeight={monitoring.detectionFrameSize.height}
              />
              {monitoring.analyzedFrameUrl && (
                <span className="analyzed-frame-badge">Matched analyzed frame</span>
              )}

              {!monitoring.isActive && (
                <div className="camera-placeholder">
                  <span className="camera-placeholder__icon" aria-hidden="true">●</span>
                  <strong>Camera is ready</strong>
                  <p>Start monitoring to request webcam access.</p>
                </div>
              )}

              {["requesting-camera", "connecting"].includes(monitoring.status) && (
                <div className="camera-loading">
                  <span className="spinner" aria-hidden="true" />
                  <strong>
                    {monitoring.status === "requesting-camera"
                      ? "Requesting camera access"
                      : "Connecting to AI service"}
                  </strong>
                </div>
              )}

              {monitoring.isBlocking && (
                <div className="violation-overlay" role="alert">
                  <span className="violation-overlay__icon" aria-hidden="true">!</span>
                  <span className="violation-overlay__eyebrow">Prohibited device detected</span>
                  <strong>{activeNames}</strong>
                  <p>Remove the device to continue monitoring.</p>
                </div>
              )}
            </div>

            <div className="camera-controls">
              <div className="control-copy">
                <strong>Automatic evidence capture</strong>
                <span>Frames are sent only while monitoring is active.</span>
              </div>
              {canStart ? (
                <button className="button button--primary" onClick={monitoring.startMonitoring}>
                  <span aria-hidden="true">▶</span>
                  Start monitoring
                </button>
              ) : (
                <button
                  className="button button--danger"
                  onClick={monitoring.stopMonitoring}
                  disabled={monitoring.status === "stopping"}
                >
                  <span aria-hidden="true">■</span>
                  {monitoring.status === "stopping" ? "Finishing…" : "Stop monitoring"}
                </button>
              )}
            </div>
          </article>

          <aside className="side-column">
            <article className="panel active-panel">
              <div className="panel-heading panel-heading--compact">
                <div>
                  <span className="panel-kicker">Current state</span>
                  <h2>Active alerts</h2>
                </div>
                <span className="count-badge">{monitoring.activeIncidents.length}</span>
              </div>
              <div className="alert-list">
                {monitoring.activeIncidents.length === 0 ? (
                  <div className="all-clear">
                    <span aria-hidden="true">✓</span>
                    <div>
                      <strong>All clear</strong>
                      <p>No confirmed prohibited devices.</p>
                    </div>
                  </div>
                ) : (
                  monitoring.activeIncidents.map((incident) => (
                    <div className="device-alert" key={incident.incident_id}>
                      <DeviceIcon type={incident.device_key} />
                      <div>
                        <strong>{incident.device_name}</strong>
                        <span>
                          {Math.round(incident.confidence * 100)}% confidence
                          {incident.count > 1 ? ` · ${incident.count} visible` : ""}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </article>

            <article className="panel activity-panel">
              <div className="panel-heading panel-heading--compact">
                <div>
                  <span className="panel-kicker">Audit trail</span>
                  <h2>Recent activity</h2>
                </div>
              </div>
              {monitoring.recentEvents.length === 0 ? (
                <EmptyActivity />
              ) : (
                <ol className="event-list">
                  {monitoring.recentEvents.map((event, index) => (
                    <li key={`${event.incident_id}-${event.event_type}-${index}`}>
                      <span className={`event-dot event-dot--${event.event_type}`} />
                      <div>
                        <strong>{event.alert_message}</strong>
                        <span>{event.receivedAt}</span>
                      </div>
                    </li>
                  ))}
                </ol>
              )}
            </article>
          </aside>
        </section>

        <section className="assurance-strip">
          <div><strong>Adaptive</strong><span>1–3 frame confirmation</span></div>
          <div><strong>2 seconds</strong><span>Removal verification</span></div>
          <div><strong>HTTPS-ready</strong><span>Secure WebSocket transport</span></div>
          <div><strong>SQLite</strong><span>Persistent audit data</span></div>
        </section>
          </>
        ) : (
          <SessionHistory />
        )}
      </main>

      <footer>
        <span>ProctorVision AI</span>
        <span>Computer vision monitoring · Version 0.8.1</span>
      </footer>
    </div>
  );
}
