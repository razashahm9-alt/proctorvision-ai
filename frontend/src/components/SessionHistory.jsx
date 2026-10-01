import { useSessionHistory } from "../hooks/useSessionHistory.js";
import {
  buildServerAssetUrl,
  formatConfidence,
  formatDuration,
} from "../utils/sessionHistory.js";


function formatDateTime(value) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "—";
  return parsed.toLocaleString([], {
    dateStyle: "medium",
    timeStyle: "medium",
  });
}


function SessionStatus({ status }) {
  const normalized = String(status || "unknown").toLowerCase();
  return (
    <span className={`archive-status archive-status--${normalized}`}>
      <span aria-hidden="true" />
      {status || "Unknown"}
    </span>
  );
}


function ArchiveEmpty({
  title = "No monitoring sessions yet",
  message = "Complete a live monitoring session and it will appear here.",
}) {
  return (
    <div className="archive-empty">
      <span aria-hidden="true">◇</span>
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  );
}


function IncidentCard({ incident, apiBaseUrl }) {
  const evidenceUrl = buildServerAssetUrl(incident.evidence_url, apiBaseUrl);
  return (
    <article className="incident-card">
      <div className="incident-card__evidence">
        {evidenceUrl ? (
          <img src={evidenceUrl} alt={`${incident.device_name} incident evidence`} />
        ) : (
          <div className="evidence-missing">
            <span aria-hidden="true">□</span>
            <strong>Evidence unavailable</strong>
          </div>
        )}
        <span className="incident-card__confidence">
          {formatConfidence(incident.maximum_confidence)} peak
        </span>
      </div>
      <div className="incident-card__body">
        <div className="incident-card__title">
          <div>
            <span className="panel-kicker">Detected device</span>
            <h3>{incident.device_name}</h3>
          </div>
          <SessionStatus status={incident.status} />
        </div>
        <dl className="incident-facts">
          <div><dt>Detected</dt><dd>{formatDateTime(incident.detected_at)}</dd></div>
          <div><dt>Cleared</dt><dd>{formatDateTime(incident.cleared_at)}</dd></div>
          <div><dt>Duration</dt><dd>{formatDuration(incident.duration_seconds)}</dd></div>
          <div><dt>Maximum count</dt><dd>{incident.maximum_count}</dd></div>
        </dl>
        <code className="incident-id" title={incident.id}>{incident.id}</code>
      </div>
    </article>
  );
}


export default function SessionHistory() {
  const archive = useSessionHistory();
  const selected = archive.selectedSession;
  const exportUrl = selected
    ? buildServerAssetUrl(selected.csv_url, archive.apiBaseUrl)
    : "";

  return (
    <section className="history-view" aria-labelledby="history-title">
      <div className="history-heading">
        <div>
          <span className="eyebrow">Persistent audit archive</span>
          <h1 id="history-title">Session History & Evidence</h1>
          <p>Review completed monitoring sessions, inspect saved incident frames, and export audit-ready CSV logs.</p>
        </div>
        <button
          className="button button--secondary"
          type="button"
          onClick={archive.refresh}
          disabled={archive.loading}
        >
          <span aria-hidden="true">↻</span>
          {archive.loading ? "Refreshing…" : "Refresh archive"}
        </button>
      </div>

      {archive.error && (
        <div className="error-banner" role="alert">
          <strong>Archive notice</strong>
          <span>{archive.error}</span>
        </div>
      )}

      <div className="history-layout">
        <aside className="panel session-browser">
          <div className="panel-heading panel-heading--compact">
            <div>
              <span className="panel-kicker">Persistent archive</span>
              <h2>Monitoring sessions</h2>
            </div>
            <span className="count-badge">{archive.sessions.length}</span>
          </div>

          {archive.loading && archive.sessions.length === 0 ? (
            <div className="archive-loading"><span className="spinner" /><span>Loading archive</span></div>
          ) : archive.sessions.length === 0 ? (
            <ArchiveEmpty />
          ) : (
            <div className="session-list">
              {archive.sessions.map((session) => (
                <button
                  className={`session-row${archive.selectedSessionId === session.id ? " is-selected" : ""}`}
                  type="button"
                  key={session.id}
                  onClick={() => archive.loadSession(session.id)}
                >
                  <span className="session-row__top">
                    <strong>{formatDateTime(session.started_at)}</strong>
                    <SessionStatus status={session.status} />
                  </span>
                  <span className="session-row__meta">
                    <span>{session.total_incidents} incident{session.total_incidents === 1 ? "" : "s"}</span>
                    <span>{formatDuration(session.duration_seconds)}</span>
                  </span>
                  <code>{session.id}</code>
                </button>
              ))}
            </div>
          )}
        </aside>

        <article className="session-review">
          {archive.detailLoading && !selected ? (
            <div className="panel archive-loading archive-loading--large">
              <span className="spinner" />
              <span>Loading session details</span>
            </div>
          ) : !selected ? (
            <div className="panel"><ArchiveEmpty /></div>
          ) : (
            <>
              <div className="panel review-summary">
                <div className="review-summary__heading">
                  <div>
                    <span className="panel-kicker">Selected audit record</span>
                    <h2>{formatDateTime(selected.started_at)}</h2>
                    <code>{selected.id}</code>
                  </div>
                  <div className="review-summary__actions">
                    <SessionStatus status={selected.status} />
                    <a className="button button--primary" href={exportUrl} download>
                      <span aria-hidden="true">↓</span>
                      Download CSV
                    </a>
                  </div>
                </div>
                <div className="archive-metrics">
                  <div><span>Confirmed incidents</span><strong>{selected.total_incidents}</strong></div>
                  <div><span>Session duration</span><strong>{formatDuration(selected.duration_seconds)}</strong></div>
                  <div><span>Started</span><strong>{formatDateTime(selected.started_at)}</strong></div>
                  <div><span>Ended</span><strong>{formatDateTime(selected.ended_at)}</strong></div>
                </div>
              </div>

              <div className="incident-section-heading">
                <div>
                  <span className="panel-kicker">Incident evidence</span>
                  <h2>Recorded violations</h2>
                </div>
                <span>{selected.incidents.length} record{selected.incidents.length === 1 ? "" : "s"}</span>
              </div>

              {selected.incidents.length === 0 ? (
                <div className="panel">
                  <ArchiveEmpty
                    title="No incidents in this session"
                    message="The session completed without a confirmed prohibited device."
                  />
                </div>
              ) : (
                <div className="incident-grid">
                  {selected.incidents.map((incident) => (
                    <IncidentCard
                      incident={incident}
                      apiBaseUrl={archive.apiBaseUrl}
                      key={incident.id}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </article>
      </div>
    </section>
  );
}
