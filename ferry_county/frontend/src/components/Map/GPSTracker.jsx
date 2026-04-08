import { useEffect, useRef } from "react";
import { useMapLibre } from "./MapContext.jsx";
import { accuracyRingGeoJSON } from "../../lib/geoAccuracy.js";

const THROTTLE_MS = 3000;

/**
 * Live device GPS on the map (watchPosition). Throttles position updates to ~3s.
 * Accuracy polygon + dot; optional map follow. Works offline (no network).
 */
export function GPSTracker({ active, followGps, onPosition }) {
  const { map, mapLoaded } = useMapLibre();
  const watchId = useRef(null);
  const lastEmitMs = useRef(0);
  const onPositionRef = useRef(onPosition);
  onPositionRef.current = onPosition;

  useEffect(() => {
    if (!mapLoaded || !map) return;
    if (map.getSource("field-gps-accuracy")) return;

    map.addSource("field-gps-accuracy", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
    map.addLayer({
      id: "field-gps-accuracy-fill",
      type: "fill",
      source: "field-gps-accuracy",
      paint: {
        "fill-color": "#00f5d4",
        "fill-opacity": 0.12,
      },
    });
    map.addSource("field-gps-dot", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });
    map.addLayer({
      id: "field-gps-dot-circle",
      type: "circle",
      source: "field-gps-dot",
      paint: {
        "circle-radius": 8,
        "circle-color": "#00f5d4",
        "circle-stroke-width": 2,
        "circle-stroke-color": "#0f1410",
      },
    });
  }, [map, mapLoaded]);

  useEffect(() => {
    if (!mapLoaded || !map || !active) return;
    if (!navigator.geolocation) return;
    if (!map.getSource("field-gps-accuracy")) return;

    const applyToMap = (lat, lon, accuracyM) => {
      const accSrc = map.getSource("field-gps-accuracy");
      const dotSrc = map.getSource("field-gps-dot");
      if (!accSrc || !dotSrc) return;
      const ring = accuracyRingGeoJSON(lat, lon, accuracyM);
      accSrc.setData({
        type: "FeatureCollection",
        features: ring ? [ring] : [],
      });
      dotSrc.setData({
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            properties: {},
            geometry: { type: "Point", coordinates: [lon, lat] },
          },
        ],
      });
      if (followGps) {
        map.easeTo({ center: [lon, lat], duration: 500 });
      }
    };

    const onFix = (pos) => {
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;
      const acc = pos.coords.accuracy ?? 0;
      const now = Date.now();
      const first = lastEmitMs.current === 0;
      if (!first && now - lastEmitMs.current < THROTTLE_MS) return;
      lastEmitMs.current = now;
      applyToMap(lat, lon, acc);
      onPositionRef.current?.({ lat, lon, accuracy: acc });
    };

    watchId.current = navigator.geolocation.watchPosition(onFix, () => {}, {
      enableHighAccuracy: true,
      maximumAge: 0,
      timeout: 20000,
    });

    return () => {
      if (watchId.current != null) {
        navigator.geolocation.clearWatch(watchId.current);
        watchId.current = null;
      }
      lastEmitMs.current = 0;
      const accSrc = map.getSource("field-gps-accuracy");
      const dotSrc = map.getSource("field-gps-dot");
      if (accSrc) accSrc.setData({ type: "FeatureCollection", features: [] });
      if (dotSrc) dotSrc.setData({ type: "FeatureCollection", features: [] });
    };
  }, [map, mapLoaded, active, followGps]);

  return null;
}
