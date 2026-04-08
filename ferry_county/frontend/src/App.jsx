import { useCallback, useEffect, useMemo, useState } from "react";
import { MapView } from "./components/Map/MapView.jsx";
import { GPSTracker } from "./components/Map/GPSTracker.jsx";
import { WaypointPins } from "./components/Map/WaypointPins.jsx";
import { TrackRecorder } from "./components/Map/TrackRecorder.jsx";
import { RoadSelector } from "./components/Field/RoadSelector.jsx";
import { TreatmentForm } from "./components/Field/TreatmentForm.jsx";
import { WaypointForm } from "./components/Field/WaypointForm.jsx";
import { AttachmentPanel } from "./components/Field/AttachmentPanel.jsx";
import { ComplianceCard } from "./components/Compliance/ComplianceCard.jsx";
import { SentinelCard } from "./components/Sentinel/SentinelCard.jsx";
import { EmergencyControlPanel } from "./components/Emergency/EmergencyControlPanel.jsx";
import { SyncStatus } from "./components/Offline/SyncStatus.jsx";
import { useOfflineSync } from "./hooks/useOfflineSync.js";
import { fetchRoads, fetchRoadsGeoJson, fetchSentinelRisks, fetchWaypoints, postTreatment } from "./api.js";
import { mergeRoadsWithSentinel, trackLineFeature } from "./lib/geojson.js";
import { getCachedRoadsGeojson, getCachedWaypoints, setCachedRoadsGeojson, setCachedWaypoints } from "./lib/mapCache.js";

const ACTOR_KEY = "ferry_cwdg_actor";

export default function App() {
  const [roads, setRoads] = useState([]);
  const [roadsGeojson, setRoadsGeojson] = useState(null);
  const [waypoints, setWaypoints] = useState([]);
  const [roadId, setRoadId] = useState(null);
  const [loadErr, setLoadErr] = useState(null);
  const [follow, setFollow] = useState(false);
  const [gpsActive, setGpsActive] = useState(false);
  const [liveGps, setLiveGps] = useState(null);
  const [pinDropMode, setPinDropMode] = useState(false);
  const [tapCoords, setTapCoords] = useState(null);
  const [actor, setActor] = useState(() => localStorage.getItem(ACTOR_KEY) || "david");
  const [online, setOnline] = useState(() => navigator.onLine);
  const [recordingLine, setRecordingLine] = useState(null);
  const [lastTrackId, setLastTrackId] = useState(null);
  const [lastTrackClientOpId, setLastTrackClientOpId] = useState(null);
  const [lastTreatmentId, setLastTreatmentId] = useState(null);
  const [lastWaypointId, setLastWaypointId] = useState(null);
  const [sentinelRisks, setSentinelRisks] = useState([]);

  const { pending, lastError, flushing, flush, queueSync } = useOfflineSync(actor);

  const loadSentinelRisks = useCallback(async () => {
    try {
      const r = await fetchSentinelRisks(400);
      setSentinelRisks(r.items || []);
    } catch {
      /* offline / API down */
    }
  }, []);

  const roadsGeojsonForMap = useMemo(
    () => mergeRoadsWithSentinel(roadsGeojson, sentinelRisks),
    [roadsGeojson, sentinelRisks]
  );

  useEffect(() => {
    localStorage.setItem(ACTOR_KEY, actor);
  }, [actor]);

  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener("online", up);
    window.addEventListener("offline", down);
    return () => {
      window.removeEventListener("online", up);
      window.removeEventListener("offline", down);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await fetchRoads(800);
        if (!cancelled) setRoads(r.items || []);
      } catch {
        if (!cancelled) setRoads([]);
      }
      try {
        const g = await fetchRoadsGeoJson();
        if (!cancelled) {
          setRoadsGeojson(g);
          await setCachedRoadsGeojson(g);
        }
      } catch {
        const gCached = await getCachedRoadsGeojson();
        if (!cancelled) {
          if (gCached) setRoadsGeojson(gCached);
          else setLoadErr("No road map data (offline with empty cache). Open online once.");
        }
      }
      try {
        const w = await fetchWaypoints(200);
        if (!cancelled) {
          setWaypoints(w.items || []);
          await setCachedWaypoints(w.items || []);
        }
      } catch {
        const wCached = await getCachedWaypoints();
        if (!cancelled && wCached?.length) setWaypoints(wCached);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    void loadSentinelRisks();
  }, [loadSentinelRisks, roadsGeojson]);

  const refreshWaypoints = useCallback(async () => {
    try {
      const w = await fetchWaypoints(200);
      setWaypoints(w.items || []);
      await setCachedWaypoints(w.items || []);
    } catch {
      /* keep list + cache */
    }
  }, []);

  const onSave = useCallback(
    async (rid, body) => {
      if (navigator.onLine) {
        try {
          const res = await postTreatment(rid, body, actor);
          setLastTreatmentId(res.treatment_id);
          setLastTrackId(null);
          setLastTrackClientOpId(null);
          return;
        } catch {
          /* fall through to queue */
        }
      }
      const opId = crypto.randomUUID();
      const payload = { road_id: rid, ...body };
      await queueSync("treatment", "create", payload, opId);
      setLastTrackId(null);
      setLastTrackClientOpId(null);
    },
    [actor, queueSync]
  );

  return (
    <div className="app">
      <header className="app-header">
        <h1>Ferry CWDG — Field</h1>
        <div className="header-tools">
          <label className="actor-label">
            Actor
            <input
              className="actor-input"
              value={actor}
              onChange={(e) => setActor(e.target.value)}
              aria-label="Actor name for audit log"
            />
          </label>
          <label className="row">
            <input type="checkbox" checked={follow} onChange={(e) => setFollow(e.target.checked)} disabled={!gpsActive} />{" "}
            Follow GPS
          </label>
          <button type="button" className="btn small" onClick={() => setGpsActive((v) => !v)}>
            {gpsActive ? "Stop GPS" : "Start GPS"}
          </button>
          <button
            type="button"
            className={`btn small ${pinDropMode ? "primary" : ""}`}
            onClick={() => setPinDropMode((v) => !v)}
            disabled={!roadsGeojson}
          >
            {pinDropMode ? "Cancel drop" : "Drop waypoint"}
          </button>
        </div>
      </header>
      {loadErr && <div className="banner error">{loadErr}</div>}
      <div className="compliance-strip">
        <SentinelCard
          actor={actor}
          onAfterScan={loadSentinelRisks}
          onSelectRoadName={(name, id) => {
            if (id != null) {
              setRoadId(id);
              return;
            }
            const m = roads.find((x) => x.road_name === name);
            if (m) setRoadId(m.id);
          }}
        />
        <ComplianceCard />
      </div>
      <div className="app-body">
        <div className="map-pane">
          <MapView roadsGeojson={roadsGeojsonForMap} trackLineGeojson={recordingLine}>
            <WaypointPins
              waypoints={waypoints}
              dropMode={pinDropMode}
              onMapTap={(c) => {
                setTapCoords(c);
                setPinDropMode(false);
              }}
            />
            <GPSTracker active={gpsActive} followGps={follow && gpsActive} onPosition={setLiveGps} />
          </MapView>
        </div>
        <aside className="side-pane">
          {liveGps && gpsActive && (
            <p className="coords">
              {liveGps.lat.toFixed(5)}, {liveGps.lon.toFixed(5)}
              {liveGps.accuracy != null && <span> ±{Math.round(liveGps.accuracy)}m</span>}
            </p>
          )}
          <RoadSelector roads={roads} value={roadId} onChange={setRoadId} disabled={roads.length === 0} />
          <TreatmentForm
            roadId={roadId}
            disabled={roads.length === 0}
            actor={actor}
            onSave={onSave}
            lastTrackId={lastTrackId}
            lastTrackClientOpId={lastTrackClientOpId}
            onClearTrack={() => {
              setLastTrackId(null);
              setLastTrackClientOpId(null);
            }}
          />
          <TrackRecorder
            roadId={roadId}
            actor={actor}
            queueSync={queueSync}
            onTrackUploaded={(id) => {
              setLastTrackId(id);
              setLastTrackClientOpId(null);
            }}
            onTrackQueued={(opId) => {
              setLastTrackClientOpId(opId);
              setLastTrackId(null);
            }}
            onLineChange={(pts) => setRecordingLine(pts && pts.length >= 2 ? trackLineFeature(pts) : null)}
          />
          <WaypointForm
            roadId={roadId}
            disabled={roads.length === 0}
            actor={actor}
            gpsPosition={liveGps}
            tapCoords={tapCoords}
            onTapCoordsConsumed={() => setTapCoords(null)}
            queueSync={queueSync}
            online={online}
            onSaved={(id) => {
              setLastWaypointId(id);
              void refreshWaypoints();
            }}
          />
          <AttachmentPanel
            actor={actor}
            online={online}
            lastTreatmentId={lastTreatmentId}
            lastWaypointId={lastWaypointId}
          />
          <SyncStatus pending={pending} flushing={flushing} lastError={lastError} onFlush={flush} online={online} />
          <EmergencyControlPanel actor={actor} />
          <p style={{ fontSize: "0.8rem", marginTop: 8 }}>
            <a href="/public" target="_blank" rel="noreferrer">
              Open public portal (residents)
            </a>
          </p>
        </aside>
      </div>
    </div>
  );
}
