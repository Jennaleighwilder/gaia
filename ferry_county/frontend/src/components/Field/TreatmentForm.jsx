import { useState } from "react";

const today = () => new Date().toISOString().slice(0, 10);

/**
 * Log treatment — online POST or offline queue via onSave.
 */
export function TreatmentForm({
  roadId,
  disabled,
  actor,
  onSave,
  lastTrackId,
  lastTrackClientOpId,
  onClearTrack,
}) {
  const [treatmentDate, setTreatmentDate] = useState(today());
  const [miles, setMiles] = useState("0.1");
  const [type, setType] = useState("brush_clear");
  const [matchDoc, setMatchDoc] = useState(true);
  const [fed, setFed] = useState("75");
  const [match, setMatch] = useState("25");
  const [dba, setDba] = useState(true);
  const [inv, setInv] = useState("100");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const [useTrack, setUseTrack] = useState(true);

  async function handle(e) {
    e.preventDefault();
    if (!roadId) {
      setMsg("Select a road first.");
      return;
    }
    setBusy(true);
    setMsg(null);
    const body = {
      treatment_date: treatmentDate,
      miles_treated: Number(miles),
      treatment_type: type,
      match_documented: matchDoc,
      amount_federal: fed === "" ? null : Number(fed),
      amount_match: match === "" ? null : Number(match),
      davis_bacon_certified: dba,
      contractor_invoice_amount: inv === "" ? null : Number(inv),
      contractor: "Field entry",
      track_id: useTrack && lastTrackId ? lastTrackId : null,
      client_track_operation_id:
        useTrack && !lastTrackId && lastTrackClientOpId ? lastTrackClientOpId : null,
    };
    try {
      await onSave(roadId, body);
      setMsg(navigator.onLine ? "Saved." : "Queued for sync.");
    } catch (err) {
      setMsg(String(err.message || err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="treatment-form" onSubmit={handle}>
      <h3>Log treatment</h3>
      <label className="field-label">
        Date
        <input className="field-input" type="date" value={treatmentDate} onChange={(e) => setTreatmentDate(e.target.value)} />
      </label>
      <label className="field-label">
        Miles treated
        <input className="field-input" inputMode="decimal" value={miles} onChange={(e) => setMiles(e.target.value)} />
      </label>
      {(lastTrackId != null || lastTrackClientOpId != null) && (
        <label className="field-label row">
          <input type="checkbox" checked={useTrack} onChange={(e) => setUseTrack(e.target.checked)} />
          {lastTrackId != null ? (
            <>Attach GPS track (#{lastTrackId})</>
          ) : (
            <>Attach queued track sync ({String(lastTrackClientOpId).slice(0, 8)}…)</>
          )}
          <button type="button" className="btn small" onClick={() => onClearTrack?.()}>
            Clear
          </button>
        </label>
      )}
      <label className="field-label">
        Type
        <select className="field-input" value={type} onChange={(e) => setType(e.target.value)}>
          <option value="brush_clear">brush_clear</option>
          <option value="mowing">mowing</option>
          <option value="hand_cut">hand_cut</option>
        </select>
      </label>
      <label className="field-label row">
        <input type="checkbox" checked={matchDoc} onChange={(e) => setMatchDoc(e.target.checked)} /> Match documented
      </label>
      <label className="field-label">
        Federal $
        <input className="field-input" inputMode="decimal" value={fed} onChange={(e) => setFed(e.target.value)} />
      </label>
      <label className="field-label">
        Match $
        <input className="field-input" inputMode="decimal" value={match} onChange={(e) => setMatch(e.target.value)} />
      </label>
      <label className="field-label row">
        <input type="checkbox" checked={dba} onChange={(e) => setDba(e.target.checked)} /> Davis-Bacon certified
      </label>
      <label className="field-label">
        Contractor invoice $
        <input className="field-input" inputMode="decimal" value={inv} onChange={(e) => setInv(e.target.value)} />
      </label>
      <label className="field-label">
        Actor (audit)
        <input className="field-input" value={actor} readOnly title="Set in header" />
      </label>
      <button type="submit" className="btn primary" disabled={disabled || busy}>
        {busy ? "…" : "Save"}
      </button>
      {msg && <p className="form-msg">{msg}</p>}
    </form>
  );
}
