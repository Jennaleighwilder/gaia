import { useEffect, useState } from "react";
import { postWaypoint } from "../../api.js";

const TYPES = ["sign", "mile_marker", "hazard", "note", "material_site", "staging", "access", "other"];

/**
 * Material / vendor / Buy America waypoint — REST or offline sync queue.
 * Optional tapCoords from map tap (consumed after applying to lat/lon fields).
 */
export function WaypointForm({ roadId, disabled, actor, gpsPosition, tapCoords, onTapCoordsConsumed, queueSync, online, onSaved }) {
  const [waypointType, setWaypointType] = useState("material_site");
  const [label, setLabel] = useState("");
  const [notes, setNotes] = useState("");
  const [matCost, setMatCost] = useState("");
  const [vendor, setVendor] = useState("");
  const [buyAmerica, setBuyAmerica] = useState(false);
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);

  useEffect(() => {
    if (!tapCoords) return;
    setLat(String(tapCoords.lat));
    setLon(String(tapCoords.lon));
    onTapCoordsConsumed?.();
  }, [tapCoords, onTapCoordsConsumed]);

  function useGpsCoords() {
    if (!gpsPosition) {
      setMsg("Start GPS in the header first.");
      return;
    }
    setLat(String(gpsPosition.lat));
    setLon(String(gpsPosition.lon));
  }

  async function handle(e) {
    e.preventDefault();
    if (lat === "" || lon === "") {
      setMsg("Set lat/lon (or Use GPS).");
      return;
    }
    const body = {
      road_id: roadId ?? null,
      lat: Number(lat),
      lon: Number(lon),
      waypoint_type: waypointType,
      label: label || null,
      notes: notes || null,
      buy_america_certified: buyAmerica,
      material_cost: matCost === "" ? null : Number(matCost),
      vendor: vendor || null,
    };
    setBusy(true);
    setMsg(null);
    try {
      if (online) {
        try {
          const res = await postWaypoint(body, actor);
          onSaved?.(res.id);
          setMsg(`Waypoint #${res.id} saved.`);
          return;
        } catch {
          /* queue */
        }
      }
      const opId = crypto.randomUUID();
      await queueSync("waypoint", "create", body, opId);
      setMsg("Waypoint queued for sync.");
    } catch (err) {
      setMsg(String(err.message || err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="treatment-form" onSubmit={handle}>
      <h3>Waypoint (material / Buy America)</h3>
      {roadId != null && (
        <p className="track-hint">Linked road id: {roadId}</p>
      )}
      <label className="field-label">
        Type
        <select className="field-input" value={waypointType} onChange={(e) => setWaypointType(e.target.value)}>
          {TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </label>
      <label className="field-label">
        Label
        <input className="field-input" value={label} onChange={(e) => setLabel(e.target.value)} placeholder="e.g. gravel pile" />
      </label>
      <label className="field-label row">
        <input type="checkbox" checked={buyAmerica} onChange={(e) => setBuyAmerica(e.target.checked)} /> Buy America certified
      </label>
      <label className="field-label">
        Material cost $
        <input className="field-input" inputMode="decimal" value={matCost} onChange={(e) => setMatCost(e.target.value)} />
      </label>
      <label className="field-label">
        Vendor
        <input className="field-input" value={vendor} onChange={(e) => setVendor(e.target.value)} />
      </label>
      <label className="field-label">
        Lat
        <input className="field-input" inputMode="decimal" value={lat} onChange={(e) => setLat(e.target.value)} />
      </label>
      <label className="field-label">
        Lon
        <input className="field-input" inputMode="decimal" value={lon} onChange={(e) => setLon(e.target.value)} />
      </label>
      <button type="button" className="btn small" onClick={useGpsCoords}>
        Use current GPS
      </button>
      <label className="field-label">
        Notes
        <textarea className="field-input" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
      </label>
      <button type="submit" className="btn primary" disabled={disabled || busy}>
        {busy ? "…" : "Save waypoint"}
      </button>
      {msg && <p className="form-msg">{msg}</p>}
    </form>
  );
}
