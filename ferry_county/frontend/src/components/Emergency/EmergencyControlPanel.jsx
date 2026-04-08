import { useCallback, useEffect, useState } from "react";
import {
  fetchEmergencyEvacuationZones,
  fetchPublicStatus,
  patchEmergencyEvacZone,
  postEmergencyEvacZone,
  postEmergencyRoadClosure,
  searchEmergencyRoads,
} from "../../api.js";

export function EmergencyControlPanel({ actor }) {
  const [status, setStatus] = useState(null);
  const [zones, setZones] = useState([]);
  const [roadQ, setRoadQ] = useState("");
  const [roadHits, setRoadHits] = useState([]);
  const [roadId, setRoadId] = useState("");
  const [zoneName, setZoneName] = useState("Zone A");
  const [zoneLevel, setZoneLevel] = useState(2);
  const [wkt, setWkt] = useState(
    "POLYGON ((-118.7 48.5, -118.4 48.5, -118.4 48.8, -118.7 48.8, -118.7 48.5))"
  );
  const [reason, setReason] = useState("");
  const [msg, setMsg] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const st = await fetchPublicStatus();
      setStatus(st);
    } catch {
      setStatus(null);
    }
    try {
      const z = await fetchEmergencyEvacuationZones(actor);
      setZones(z.items || []);
    } catch {
      setZones([]);
    }
  }, [actor]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <section
      className="emergency-panel"
      style={{ border: "1px solid #334155", borderRadius: 8, padding: 12, marginTop: 8 }}
    >
      <h3 style={{ margin: "0 0 8px" }}>Emergency — public feed</h3>
      <p style={{ fontSize: "0.85rem", margin: "0 0 8px" }}>
        Evac zones (active): {status?.evacuation_zone_count ?? "—"} · Closures: {status?.road_closure_count ?? "—"}
      </p>

      <div style={{ marginBottom: 12 }}>
        <strong>New evacuation zone</strong>
        <label className="row" style={{ display: "block", marginTop: 6 }}>
          Name
          <input value={zoneName} onChange={(e) => setZoneName(e.target.value)} style={{ width: "100%" }} />
        </label>
        <label className="row" style={{ display: "block" }}>
          Level
          <select value={zoneLevel} onChange={(e) => setZoneLevel(Number(e.target.value))}>
            <option value={1}>1</option>
            <option value={2}>2</option>
            <option value={3}>3</option>
          </select>
        </label>
        <label className="row" style={{ display: "block" }}>
          WKT polygon (EPSG:4326)
          <textarea value={wkt} onChange={(e) => setWkt(e.target.value)} rows={3} style={{ width: "100%" }} />
        </label>
        <button
          type="button"
          className="btn small primary"
          onClick={async () => {
            try {
              await postEmergencyEvacZone({ zone_name: zoneName, level: zoneLevel, wkt_polygon: wkt }, actor);
              setMsg("Zone created");
              await refresh();
            } catch (e) {
              setMsg(String(e.message || e));
            }
          }}
        >
          Create &amp; activate
        </button>
      </div>

      <div style={{ marginBottom: 12 }}>
        <strong>Active zones</strong>
        <ul style={{ paddingLeft: 18, fontSize: "0.85rem" }}>
          {zones
            .filter((z) => z.active)
            .map((z) => (
              <li key={z.id}>
                {z.zone_name} (L{z.level}){" "}
                <button
                  type="button"
                  className="btn tiny"
                  onClick={async () => {
                    await patchEmergencyEvacZone(z.id, { active: false }, actor);
                    await refresh();
                  }}
                >
                  Deactivate
                </button>
              </li>
            ))}
        </ul>
      </div>

      <div>
        <strong>Road closure</strong>
        <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
          <input
            placeholder="Search road…"
            value={roadQ}
            onChange={(e) => setRoadQ(e.target.value)}
            style={{ flex: 1 }}
          />
          <button
            type="button"
            className="btn small"
            onClick={async () => {
              const r = await searchEmergencyRoads(roadQ, actor);
              setRoadHits(r.items || []);
            }}
          >
            Search
          </button>
        </div>
        <select value={roadId} onChange={(e) => setRoadId(e.target.value)} style={{ width: "100%", marginTop: 6 }}>
          <option value="">Select road…</option>
          {roadHits.map((r) => (
            <option key={r.id} value={String(r.id)}>
              {r.road_name}
            </option>
          ))}
        </select>
        <label className="row" style={{ display: "block", marginTop: 6 }}>
          Reason
          <input value={reason} onChange={(e) => setReason(e.target.value)} style={{ width: "100%" }} />
        </label>
        <button
          type="button"
          className="btn small"
          onClick={async () => {
            if (!roadId) return;
            try {
              await postEmergencyRoadClosure(
                { road_id: Number(roadId), closure_reason: reason, closure_type: "maintenance" },
                actor
              );
              setMsg("Closure posted");
              await refresh();
            } catch (e) {
              setMsg(String(e.message || e));
            }
          }}
        >
          Publish closure
        </button>
      </div>
      {msg && <p style={{ fontSize: "0.85rem", marginTop: 8 }}>{msg}</p>}
    </section>
  );
}
