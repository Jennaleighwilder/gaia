export function SyncStatus({ pending, flushing, lastError, onFlush, online }) {
  return (
    <div className="sync-panel">
      <h3>Sync</h3>
      <p className="sync-line">
        Network: <strong>{online ? "online" : "offline"}</strong>
      </p>
      <p className="sync-line">
        Pending queue: <strong>{pending}</strong>
      </p>
      <button type="button" className="btn" onClick={onFlush} disabled={flushing || pending === 0 || !online}>
        {flushing ? "Syncing…" : "Sync now"}
      </button>
      {lastError && <p className="form-msg error">{lastError}</p>}
    </div>
  );
}
