import { useCallback, useEffect, useRef, useState } from "react";
import { postTrack } from "../../api.js";
import { pathLengthMiles } from "../../lib/haversine.js";
import { clearTrackDraft, loadTrackDraft, saveTrackDraft } from "../../lib/trackDrafts.js";

const SAMPLE_MS = 5000;

/**
 * Records GPS every 5s (getCurrentPosition), Haversine miles on device, POST /tracks or offline queue.
 */
export function TrackRecorder({ roadId, actor, queueSync, onTrackUploaded, onTrackQueued, onLineChange }) {
  const [active, setActive] = useState(false);
  const [points, setPoints] = useState([]);
  const [startedAt, setStartedAt] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [draftLoaded, setDraftLoaded] = useState(false);
  const intervalRef = useRef(null);
  const startMsRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const d = await loadTrackDraft();
      if (cancelled || !d?.points?.length) return;
      const tuples = d.points.map((p) => [p.lon, p.lat, ...(p.accuracy_m != null ? [p.accuracy_m] : [])]);
      setPoints(tuples);
      setStartedAt(d.startedAt || Date.now());
      startMsRef.current = d.startedAt || Date.now();
      setDraftLoaded(true);
      setMsg("Restored draft track from device storage.");
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    onLineChange?.(points);
  }, [points, onLineChange]);

  const persist = useCallback(
    async (nextPoints, startMs) => {
      const payload = {
        roadId: roadId ?? null,
        points: nextPoints.map((p) => {
          const o = { lon: p[0], lat: p[1] };
          if (p.length >= 3) o.accuracy_m = p[2];
          return o;
        }),
        startedAt: startMs,
      };
      await saveTrackDraft(payload);
    },
    [roadId]
  );

  const clearTimer = useCallback(() => {
    if (intervalRef.current != null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const sampleOnce = useCallback(() => {
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const row = [pos.coords.longitude, pos.coords.latitude, pos.coords.accuracy];
        setPoints((prev) => {
          const next = [...prev, row];
          if (next.length % 2 === 0 || next.length === 1) {
            void persist(next, startMsRef.current);
          }
          return next;
        });
      },
      (err) => setMsg(err.message),
      { enableHighAccuracy: true, maximumAge: 0, timeout: 20000 }
    );
  }, [persist]);

  const start = useCallback(() => {
    if (!navigator.geolocation) {
      setMsg("Geolocation not available.");
      return;
    }
    setMsg(null);
    const startMs = Date.now();
    startMsRef.current = startMs;
    setStartedAt(startMs);
    setActive(true);
    sampleOnce();
    intervalRef.current = window.setInterval(sampleOnce, SAMPLE_MS);
  }, [sampleOnce]);

  const stop = useCallback(() => {
    clearTimer();
    setActive(false);
    setPoints((prev) => {
      if (prev.length) void persist(prev, startMsRef.current);
      return prev;
    });
  }, [clearTimer, persist]);

  const discardDraft = useCallback(async () => {
    await clearTrackDraft();
    setPoints([]);
    setStartedAt(null);
    startMsRef.current = 0;
    setDraftLoaded(false);
    setMsg("Draft cleared.");
  }, []);

  const upload = useCallback(async () => {
    if (points.length < 2) {
      setMsg("Need at least 2 points.");
      return;
    }
    setBusy(true);
    setMsg(null);
    const body = {
      road_id: roadId ?? null,
      points: points.map((p) => {
        const o = { lon: p[0], lat: p[1] };
        if (p.length >= 3) o.accuracy_m = p[2];
        return o;
      }),
      start_time: new Date(startedAt || startMsRef.current || Date.now()).toISOString(),
      end_time: new Date().toISOString(),
    };
    try {
      if (navigator.onLine) {
        try {
          const res = await postTrack(body, actor);
          await clearTrackDraft();
          setPoints([]);
          setStartedAt(null);
          startMsRef.current = 0;
          onTrackUploaded?.(res.id);
          setMsg(`Track #${res.id} saved (${res.vertex_count} pts, ${res.calculated_miles?.toFixed?.(2) ?? "?"} mi).`);
          return;
        } catch {
          /* queue */
        }
      }
      const opId = crypto.randomUUID();
      await queueSync("track", "create", body, opId);
      onTrackQueued?.(opId);
      await clearTrackDraft();
      setPoints([]);
      setStartedAt(null);
      startMsRef.current = 0;
      setMsg("Track queued for sync.");
    } catch (e) {
      setMsg(String(e.message || e));
    } finally {
      setBusy(false);
    }
  }, [actor, onTrackQueued, points, queueSync, roadId, startedAt, onTrackUploaded]);

  useEffect(() => () => clearTimer(), [clearTimer]);

  const miles = pathLengthMiles(points);

  return (
    <div className="track-panel">
      <h3>Track</h3>
      <p className="track-hint">Samples every 5s (device GPS only). Saved on device while recording; upload when online.</p>
      {draftLoaded && points.length > 0 && !active && <p className="form-msg">Draft on device: {points.length} points.</p>}
      {!active ? (
        <button type="button" className="btn" onClick={start} disabled={busy}>
          Start recording
        </button>
      ) : (
        <button type="button" className="btn danger" onClick={stop}>
          Stop ({points.length} pts, {miles.toFixed(2)} mi)
        </button>
      )}
      {active && <p className="coords">Distance: {miles.toFixed(2)} mi</p>}
      {points.length >= 2 && !active && (
        <button type="button" className="btn primary small" onClick={upload} disabled={busy}>
          {busy ? "…" : "Upload track"}
        </button>
      )}
      {points.length > 0 && !active && (
        <button type="button" className="btn small" onClick={discardDraft}>
          Discard draft
        </button>
      )}
      {msg && <p className="form-msg">{msg}</p>}
    </div>
  );
}
