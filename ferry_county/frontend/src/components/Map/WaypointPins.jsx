import { useEffect, useRef } from "react";
import { useMapLibre } from "./MapContext.jsx";

/** @param {string | null | undefined} t */
export function waypointPinColor(t) {
  switch ((t || "").toLowerCase()) {
    case "sign":
      return "#2f9e44";
    case "mile_marker":
      return "#228be6";
    case "hazard":
      return "#f03e3e";
    case "note":
      return "#868e96";
    default:
      return "#868e96";
  }
}

function waypointsToFeatureCollection(items) {
  const features = (items || [])
    .filter((w) => w.lat != null && w.lon != null)
    .map((w) => ({
      type: "Feature",
      properties: {
        id: w.id,
        waypoint_type: w.waypoint_type ?? "",
        label: w.label ?? "",
        pin_color: waypointPinColor(w.waypoint_type),
      },
      geometry: { type: "Point", coordinates: [w.lon, w.lat] },
    }));
  return { type: "FeatureCollection", features };
}

/**
 * Renders waypoints as colored circles; optional map tap to drop (lat/lon for form).
 */
export function WaypointPins({ waypoints, dropMode, onMapTap }) {
  const { map, mapLoaded } = useMapLibre();
  const onMapTapRef = useRef(onMapTap);
  onMapTapRef.current = onMapTap;

  useEffect(() => {
    if (!mapLoaded || !map) return;
    if (map.getSource("field-waypoints")) return;

    map.addSource("field-waypoints", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
    map.addLayer({
      id: "field-waypoints-circle",
      type: "circle",
      source: "field-waypoints",
      paint: {
        "circle-radius": 7,
        "circle-color": ["get", "pin_color"],
        "circle-stroke-width": 2,
        "circle-stroke-color": "#ffffff",
      },
    });
  }, [map, mapLoaded]);

  useEffect(() => {
    if (!mapLoaded || !map) return;
    const src = map.getSource("field-waypoints");
    if (!src) return;
    src.setData(waypointsToFeatureCollection(waypoints));
  }, [map, mapLoaded, waypoints]);

  useEffect(() => {
    if (!mapLoaded || !map || !dropMode) return;

    const handler = (e) => {
      const { lng, lat } = e.lngLat;
      onMapTapRef.current?.({ lat, lon: lng });
    };
    map.on("click", handler);
    map.getCanvas().style.cursor = "crosshair";
    return () => {
      map.off("click", handler);
      map.getCanvas().style.cursor = "";
    };
  }, [map, mapLoaded, dropMode]);

  return null;
}
