import { useCallback, useEffect, useState } from "react";
import { fetchPublicWeather, fetchSentinelStatus, postSentinelScan } from "../../api.js";

/**
 * SENTINEL corridor risk summary for the Field / EOC dashboard.
 * Red Flag bumps visual emphasis; top roads link to selector by name (manual pick).
 */
export function SentinelCard({ actor, onSelectRoadName, onAfterScan }) {
  const [status, setStatus] = useState(null);
  const [weather, setWeather] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const [s, w] = await Promise.all([fetchSentinelStatus(), fetchPublicWeather()]);
      setStatus(s);
      setWeather(w);
      setErr(null);
    } catch (e) {
      setErr(String(e.message || e));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const redFlag = status?.latest_scan?.red_flag_active === true;
  const top = status?.top_risk_roads || [];

  return (
    <div className={`sentinel-card ${redFlag ? "sentinel-card--alert" : ""}`}>
      <h3 className="sentinel-card-title">{redFlag ? "SENTINEL — Red Flag in area" : "SENTINEL — Corridor risk"}</h3>
      <p className="sentinel-card-meta">
        {status?.latest_scan?.scan_time
          ? `Last scan: ${status.latest_scan.scan_time}`
          : "No scan yet — run one when online."}
        {status?.latest_scan?.atmosphere_fwi != null && (
          <span> · Fire-weather index ~{Math.round(status.latest_scan.atmosphere_fwi)}</span>
        )}
        {weather?.temp_f != null && (
          <span>
            {" "}
            · Live wx NWS/GAIA: {Math.round(weather.temp_f)}°F, wind ~{weather.wind_mph ?? "—"} mph
            {weather.red_flag_warning ? " — Red Flag (area)" : ""}
          </span>
        )}
      </p>
      {top.length > 0 && (
        <ul className="sentinel-top-list">
          {top.map((r) => (
            <li key={r.road_id}>
              <button
                type="button"
                className="sentinel-road-link"
                onClick={() => onSelectRoadName?.(r.road_name, r.road_id)}
              >
                {r.road_name || `Road #${r.road_id}`}
              </button>
              <span className={`sentinel-badge sentinel-badge--${r.risk_level || "low"}`}>
                {r.risk_level || "—"}
              </span>
            </li>
          ))}
        </ul>
      )}
      <div className="sentinel-actions">
        <button type="button" className="btn small" onClick={() => void load()} disabled={busy}>
          Refresh
        </button>
        <button
          type="button"
          className="btn small primary"
          onClick={async () => {
            setBusy(true);
            try {
              await postSentinelScan(actor);
              await load();
              await onAfterScan?.();
              setErr(null);
            } catch (e) {
              setErr(String(e.message || e));
            } finally {
              setBusy(false);
            }
          }}
          disabled={busy}
        >
          {busy ? "…" : "Run scan"}
        </button>
      </div>
      {err && <p className="form-msg">{err}</p>}
    </div>
  );
}
