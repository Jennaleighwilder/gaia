import { useCallback, useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import {
  fetchPublicEvacuationZones,
  fetchPublicIncidents,
  fetchPublicRoadClosures,
  fetchPublicStatus,
  fetchPublicWeather,
  fetchRoadsGeoJson,
} from "../../api.js";

const STYLE = "https://demotiles.maplibre.org/style.json";
const REFRESH_MS = 60_000;

export default function PublicMap() {
  const mapDiv = useRef(null);
  const mapRef = useRef(null);
  const [status, setStatus] = useState(null);
  const [weather, setWeather] = useState(null);
  const [err, setErr] = useState(null);
  const [selectedClosure, setSelectedClosure] = useState(null);

  const loadData = useCallback(async () => {
    try {
      const [st, zones, closures, inc, wx, roads] = await Promise.all([
        fetchPublicStatus(),
        fetchPublicEvacuationZones(),
        fetchPublicRoadClosures(),
        fetchPublicIncidents(),
        fetchPublicWeather(),
        fetchRoadsGeoJson(),
      ]);
      setStatus(st);
      setWeather(wx);
      setErr(null);
      const map = mapRef.current;
      if (!map?.getSource?.("public-roads")) return;

      const closureByRoad = new Map((closures.items || []).map((c) => [c.road_id, c]));
      const feats = (roads.features || []).map((f) => {
        const rid = f.properties?.road_id;
        const c = closureByRoad.get(rid);
        return {
          type: "Feature",
          id: f.id,
          properties: { ...f.properties, _closed: Boolean(c), _status: c?.status || null },
          geometry: f.geometry,
        };
      });
      map.getSource("public-roads").setData({ type: "FeatureCollection", features: feats });
      map.setPaintProperty("public-roads-line", "line-color", [
        "case",
        ["==", ["get", "_status"], "caution"],
        "#e85d04",
        ["boolean", ["get", "_closed"], false],
        "#c1121f",
        "#2d6a4f",
      ]);

      map.getSource("evac-zones").setData(zones);
      map.getSource("incidents").setData(inc);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    if (!mapDiv.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: mapDiv.current,
      style: STYLE,
      center: [-118.6, 48.65],
      zoom: 9.5,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.on("load", async () => {
      const roads = await fetchRoadsGeoJson();
      const zones = await fetchPublicEvacuationZones();
      const inc = await fetchPublicIncidents();
      map.addSource("public-roads", { type: "geojson", data: roads });
      map.addLayer({
        id: "public-roads-line",
        type: "line",
        source: "public-roads",
        paint: { "line-color": "#2d6a4f", "line-width": 2.5 },
      });
      map.addSource("evac-zones", { type: "geojson", data: zones });
      map.addLayer({
        id: "evac-fill",
        type: "fill",
        source: "evac-zones",
        paint: {
          "fill-color": ["match", ["get", "level"], 3, "#c1121f", 2, "#e85d04", "#e9c46a"],
          "fill-opacity": 0.35,
        },
      });
      map.addSource("incidents", { type: "geojson", data: inc });
      map.addLayer({
        id: "incidents-point",
        type: "circle",
        source: "incidents",
        paint: { "circle-radius": 7, "circle-color": "#7209b7" },
      });
      map.addSource("detour", { type: "geojson", data: { type: "FeatureCollection", features: [] } });
      map.addLayer({
        id: "detour-line",
        type: "line",
        source: "detour",
        paint: { "line-color": "#4361ee", "line-dasharray": [2, 2], "line-width": 3 },
      });
      mapRef.current = map;
      await loadData();
    });
    const iv = setInterval(() => void loadData(), REFRESH_MS);
    return () => {
      clearInterval(iv);
      map.remove();
      mapRef.current = null;
    };
  }, [loadData]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.getSource?.("detour")) return;
    if (selectedClosure?.detour_route) {
      map.getSource("detour").setData({
        type: "Feature",
        properties: {},
        geometry: selectedClosure.detour_route,
      });
    } else {
      map.getSource("detour").setData({ type: "FeatureCollection", features: [] });
    }
  }, [selectedClosure]);

  const alertZones = status?.active_evacuation_zones || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {alertZones.length > 0 && (
        <div
          style={{
            padding: "12px 16px",
            background: alertZones.some((z) => z.properties?.level >= 3) ? "#7f1d1d" : "#9a3412",
            color: "#fff",
            fontWeight: 700,
          }}
        >
          EVACUATION ORDER IN EFFECT — Level{" "}
          {Math.max(...alertZones.map((z) => z.properties?.level || 0))} —{" "}
          {alertZones.map((z) => z.properties?.zone_name).filter(Boolean).join(", ")}
        </div>
      )}
      <header
        style={{
          padding: "10px 14px",
          background: "#0f172a",
          color: "#e2e8f0",
          display: "flex",
          flexWrap: "wrap",
          gap: "12px",
          alignItems: "center",
        }}
      >
        <strong>Ferry County Emergency Information</strong>
        <span style={{ fontSize: "0.85rem", opacity: 0.85 }}>Last updated: {status?.last_updated || "—"}</span>
      </header>
      <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
        <aside
          style={{
            width: 260,
            background: "#1e293b",
            color: "#e2e8f0",
            padding: 12,
            overflow: "auto",
            fontSize: "0.9rem",
          }}
        >
          {weather?.red_flag_warning && (
            <div style={{ background: "#7f1d1d", padding: 8, marginBottom: 10, borderRadius: 6 }}>
              Red Flag Warning — exercise extreme caution.
            </div>
          )}
          {weather && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontWeight: 600 }}>Current conditions</div>
              <div>{weather.conditions || "—"}</div>
              <div>
                {weather.temp_f != null ? `${weather.temp_f}°F` : ""}
                {weather.wind_mph != null ? ` · Wind ${weather.wind_mph} mph` : ""}
              </div>
              <div style={{ fontSize: "0.75rem", opacity: 0.75, marginTop: 6 }}>
                Source: {weather.source} (NOAA when GAIA unavailable)
              </div>
            </div>
          )}
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Closures</div>
          <ul style={{ paddingLeft: 18, margin: 0 }}>
            {(status?.road_closures_summary || []).map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  style={{ background: "none", border: "none", color: "#93c5fd", cursor: "pointer", padding: 0 }}
                  onClick={async () => {
                    try {
                      const cl = await fetchPublicRoadClosures();
                      setSelectedClosure((cl.items || []).find((x) => x.id === c.id) || null);
                    } catch {
                      setSelectedClosure(null);
                    }
                  }}
                >
                  {c.road_name}
                </button>
              </li>
            ))}
          </ul>
          {selectedClosure && (
            <div style={{ marginTop: 10, padding: 8, background: "#334155", borderRadius: 6 }}>
              <strong>{selectedClosure.road_name}</strong>
              <div>{selectedClosure.closure_reason}</div>
              <div style={{ fontSize: "0.8rem" }}>{selectedClosure.detour_notes}</div>
            </div>
          )}
        </aside>
        <div ref={mapDiv} style={{ flex: 1, position: "relative" }} />
      </div>
      {err && <div style={{ background: "#fecaca", padding: 8, fontSize: "0.85rem" }}>{err}</div>}
    </div>
  );
}
