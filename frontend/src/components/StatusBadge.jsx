const STATUS_COPY = {
  idle: { label: "Ready", tone: "neutral" },
  "requesting-camera": { label: "Camera permission", tone: "pending" },
  connecting: { label: "Connecting", tone: "pending" },
  monitoring: { label: "Monitoring live", tone: "success" },
  stopping: { label: "Finishing session", tone: "pending" },
  error: { label: "Attention needed", tone: "danger" },
};

export default function StatusBadge({ status }) {
  const current = STATUS_COPY[status] ?? STATUS_COPY.idle;
  return (
    <span className={`status-badge status-badge--${current.tone}`}>
      <span className="status-badge__dot" aria-hidden="true" />
      {current.label}
    </span>
  );
}
