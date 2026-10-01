import { useState } from "react";


function AccessBrand() {
  return (
    <span className="access-brand__mark" aria-hidden="true">
      <svg viewBox="0 0 48 48">
        <path d="M24 4 41 10v12c0 10.4-6.9 18.6-17 22C13.9 40.6 7 32.4 7 22V10L24 4Z" />
        <path d="M14 24c2.8-4.4 6.1-6.6 10-6.6s7.2 2.2 10 6.6c-2.8 4.4-6.1 6.6-10 6.6S16.8 28.4 14 24Z" />
        <circle cx="24" cy="24" r="3.7" />
      </svg>
    </span>
  );
}


export default function AccessGate({ access }) {
  const [token, setToken] = useState("");
  const checking = access.state === "checking";
  const unavailable = access.state === "error";

  const submit = async (event) => {
    event.preventDefault();
    if (!token.trim() || checking) return;
    const accepted = await access.login(token);
    if (!accepted) setToken("");
  };

  return (
    <main className="access-screen">
      <section className="access-card" aria-live="polite">
        <div className="access-brand">
          <AccessBrand />
          <div><strong>ProctorVision</strong><span>AI monitoring</span></div>
        </div>

        {checking ? (
          <div className="access-state">
            <span className="spinner" aria-hidden="true" />
            <h1>Connecting securely</h1>
            <p>Checking the monitoring service and supervisor access.</p>
          </div>
        ) : unavailable ? (
          <div className="access-state">
            <span className="access-state__icon" aria-hidden="true">!</span>
            <h1>Service unavailable</h1>
            <p>{access.error}</p>
            <button className="button button--primary" type="button" onClick={access.check}>
              Try again
            </button>
          </div>
        ) : (
          <form className="access-form" onSubmit={submit}>
            <span className="eyebrow">Private demonstration</span>
            <h1>Supervisor access</h1>
            <p>Enter the temporary access token supplied with this demonstration.</p>
            <label htmlFor="demo-access-token">Access token</label>
            <input
              id="demo-access-token"
              autoComplete="current-password"
              autoFocus
              onChange={(event) => setToken(event.target.value)}
              placeholder="Enter access token"
              type="password"
              value={token}
            />
            {access.error && <span className="access-form__error" role="alert">{access.error}</span>}
            <button className="button button--primary" disabled={!token.trim()} type="submit">
              Open monitoring console
            </button>
            <small>Camera access is requested only after monitoring is started.</small>
          </form>
        )}
      </section>
    </main>
  );
}
