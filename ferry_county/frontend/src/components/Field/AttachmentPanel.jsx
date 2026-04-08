import { useState } from "react";
import { attachmentDownloadUrl, uploadAttachment } from "../../api.js";

const KINDS = [
  "photo",
  "invoice",
  "match_backup",
  "davis_bacon_wage",
  "buy_america_cert",
  "other",
];

/**
 * Multipart upload to server disk (content-addressed); requires network.
 */
export function AttachmentPanel({ actor, online, lastTreatmentId, lastWaypointId }) {
  const [kind, setKind] = useState("photo");
  const [treatmentId, setTreatmentId] = useState("");
  const [waypointId, setWaypointId] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [lastUploadId, setLastUploadId] = useState(null);

  async function onSubmit(e) {
    e.preventDefault();
    const input = e.currentTarget.querySelector('input[type="file"]');
    const file = input?.files?.[0];
    if (!file) {
      setMsg("Choose a file.");
      return;
    }
    const tid = treatmentId.trim() === "" ? lastTreatmentId ?? null : Number(treatmentId);
    const wid = waypointId.trim() === "" ? lastWaypointId ?? null : Number(waypointId);
    if (tid == null && wid == null) {
      setMsg("Save a treatment or waypoint first, or enter ids.");
      return;
    }
    if (!online) {
      setMsg("File upload needs a network connection.");
      return;
    }
    setBusy(true);
    setMsg(null);
    try {
      const res = await uploadAttachment(
        file,
        { kind, treatmentId: tid, waypointId: wid },
        actor
      );
      setLastUploadId(res.id);
      setMsg(`Uploaded attachment #${res.id} (${res.sha256_hex?.slice(0, 12)}…).`);
    } catch (err) {
      setMsg(String(err.message || err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="track-panel">
      <h3>Attachments</h3>
      <p className="track-hint">Files stored on the API host (content-addressed). Link to a treatment and/or waypoint row.</p>
      <form onSubmit={onSubmit}>
        <label className="field-label">
          Kind
          <select className="field-input" value={kind} onChange={(e) => setKind(e.target.value)}>
            {KINDS.map((k) => (
              <option key={k} value={k}>
                {k}
              </option>
            ))}
          </select>
        </label>
        <label className="field-label">
          Treatment id (optional)
          <input
            className="field-input"
            inputMode="numeric"
            placeholder={lastTreatmentId != null ? `default ${lastTreatmentId}` : ""}
            value={treatmentId}
            onChange={(e) => setTreatmentId(e.target.value)}
          />
        </label>
        <label className="field-label">
          Waypoint id (optional)
          <input
            className="field-input"
            inputMode="numeric"
            placeholder={lastWaypointId != null ? `default ${lastWaypointId}` : ""}
            value={waypointId}
            onChange={(e) => setWaypointId(e.target.value)}
          />
        </label>
        <label className="field-label">
          File
          <input className="field-input" type="file" name="file" />
        </label>
        <button type="submit" className="btn primary" disabled={busy || !online}>
          {busy ? "…" : "Upload"}
        </button>
      </form>
      {msg && <p className="form-msg">{msg}</p>}
      {lastUploadId != null && online && (
        <p className="sync-line">
          <a href={attachmentDownloadUrl(lastUploadId)} target="_blank" rel="noreferrer">
            Open last upload
          </a>
        </p>
      )}
    </div>
  );
}
