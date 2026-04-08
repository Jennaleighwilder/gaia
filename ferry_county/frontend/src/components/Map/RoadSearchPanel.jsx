import { useCallback, useEffect, useRef, useState } from "react";
import { searchRoads } from "../../api.js";
import { useMapLibre } from "./MapContext.jsx";

const DEBOUNCE_MS = 300;

/**
 * Live road name search: type → pick → flyTo + yellow highlight (MapView highlightRoadId).
 */
export function RoadSearchPanel({ onPick, onHighlightClear }) {
  const { map } = useMapLibre();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);
  const debounceRef = useRef(null);

  const runSearch = useCallback(
    async (q) => {
      const qq = q.trim();
      if (!qq) {
        setResults([]);
        setErr(null);
        return;
      }
      if (!navigator.onLine) {
        setErr("Search requires network");
        setResults([]);
        return;
      }
      setBusy(true);
      setErr(null);
      try {
        const data = await searchRoads(qq);
        setResults(data.items || []);
        setOpen(true);
      } catch (e) {
        setErr(String(e.message || e));
        setResults([]);
      } finally {
        setBusy(false);
      }
    },
    []
  );

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      void runSearch(query);
    }, DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query, runSearch]);

  const handlePick = useCallback(
    (road) => {
      setOpen(false);
      setQuery(road.road_name || "");
      onPick?.(road);
      if (map && road.center_lon != null && road.center_lat != null) {
        map.flyTo({
          center: [road.center_lon, road.center_lat],
          zoom: 14,
          duration: 1500,
        });
      }
    },
    [map, onPick]
  );

  return (
    <div className="road-search-panel">
      <label className="road-search-label" htmlFor="road-search-input">
        Find road
      </label>
      <input
        id="road-search-input"
        type="search"
        className="road-search-input"
        placeholder="Type a road name…"
        autoComplete="off"
        aria-label="Search roads by name"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          onHighlightClear?.();
        }}
        onFocus={() => results.length > 0 && setOpen(true)}
      />
      {!navigator.onLine && <p className="road-search-hint">Offline — search needs a connection.</p>}
      {err && <p className="road-search-err">{err}</p>}
      {busy && query.trim() && <p className="road-search-hint">Searching…</p>}
      {open && results.length > 0 && (
        <ul className="road-search-results" role="listbox">
          {results.map((r) => (
            <li key={r.id}>
              <button type="button" className="road-search-hit" onClick={() => handlePick(r)}>
                <span className="road-search-name">{r.road_name}</span>
                {r.road_number && <span className="road-search-num"> #{r.road_number}</span>}
                {r.cemp_miles != null && Number(r.cemp_miles) > 0 && (
                  <span className="road-search-grant"> Grant</span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
      {open && query.trim() && !busy && results.length === 0 && navigator.onLine && (
        <p className="road-search-hint">No matches.</p>
      )}
    </div>
  );
}
