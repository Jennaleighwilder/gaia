import { useEffect, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { MapLibreContext } from "./MapContext.jsx";

const STYLE = "https://demotiles.maplibre.org/style.json";

/** Grant roads in SENTINEL elevated/critical show red; then treatment status palette. */
const ROAD_LINE_COLOR = [
  "case",
  [
    "all",
    ["==", ["get", "sentinel_elevated"], true],
    ["==", ["get", "is_grant_road"], true],
  ],
  "#c1121f",
  ["==", ["get", "treatment_status"], "complete"],
  "#2d6a4f",
  ["==", ["get", "treatment_status"], "partial"],
  "#e9c46a",
  [
    "all",
    ["==", ["get", "treatment_status"], "untreated"],
    ["==", ["get", "is_grant_road"], true],
  ],
  "#f77f00",
  "#868e96",
];

function setRoadsData(map, geojson) {
  const src = map.getSource("roads");
  if (src && geojson) src.setData(geojson);
}

/**
 * Ferry County Field map: MapLibre base, roads from /roads/geojson, optional track overlay.
 * Children (GPSTracker, WaypointPins, RoadSearchPanel) use useMapLibre() after load.
 * @param {number | null} [highlightRoadId] — yellow highlight for live search selection
 */
export function MapView({ roadsGeojson, trackLineGeojson, highlightRoadId = null, children }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const [mapInstance, setMapInstance] = useState(null);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: STYLE,
      center: [-118.6, 48.65],
      zoom: 10,
    });
    map.addControl(new maplibregl.NavigationControl(), "top-right");
    map.on("load", () => {
      map.addSource("roads", {
        type: "geojson",
        data: roadsGeojson || { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "roads-line",
        type: "line",
        source: "roads",
        paint: {
          "line-color": ROAD_LINE_COLOR,
          "line-width": 3,
          "line-opacity": 0.9,
        },
      });
      map.addLayer({
        id: "roads-highlight",
        type: "line",
        source: "roads",
        filter: ["==", ["get", "road_id"], -999999],
        paint: {
          "line-color": "#f0c808",
          "line-width": 6,
          "line-opacity": 0,
        },
      });
      map.addSource("track-line", {
        type: "geojson",
        data: { type: "FeatureCollection", features: [] },
      });
      map.addLayer({
        id: "field-track-line",
        type: "line",
        source: "track-line",
        paint: {
          "line-color": "#ff2d95",
          "line-width": 4,
          "line-opacity": 0.9,
        },
      });
      mapRef.current = map;
      setMapInstance(map);
    });
    return () => {
      map.remove();
      mapRef.current = null;
      setMapInstance(null);
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => setRoadsData(map, roadsGeojson);
    if (map.loaded()) apply();
    else map.once("load", apply);
  }, [roadsGeojson]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const apply = () => {
      const src = map.getSource("track-line");
      if (!src) return;
      src.setData(trackLineGeojson || { type: "FeatureCollection", features: [] });
    };
    if (map.loaded()) apply();
    else map.once("load", apply);
  }, [trackLineGeojson]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.getLayer("roads-highlight")) return;
    if (highlightRoadId == null) {
      map.setPaintProperty("roads-highlight", "line-opacity", 0);
    } else {
      map.setFilter("roads-highlight", ["==", ["get", "road_id"], highlightRoadId]);
      map.setPaintProperty("roads-highlight", "line-opacity", 0.95);
    }
  }, [highlightRoadId, mapInstance]);

  const mapLoaded = !!mapInstance;

  return (
    <MapLibreContext.Provider value={{ map: mapInstance, mapLoaded }}>
      <div className="map-wrap" ref={containerRef} />
      {mapLoaded ? children : null}
    </MapLibreContext.Provider>
  );
}
