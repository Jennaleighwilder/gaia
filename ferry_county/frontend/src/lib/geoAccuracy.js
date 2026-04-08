const R_EARTH_M = 6371000;

/**
 * Rough local tangent-plane ring (good enough for sub-km accuracy circles on the map).
 * @returns {import("geojson").Feature<import("geojson").Polygon> | null}
 */
export function accuracyRingGeoJSON(lat, lon, radiusM, steps = 40) {
  if (radiusM == null || !Number.isFinite(radiusM) || radiusM <= 0) return null;
  const latRad = (lat * Math.PI) / 180;
  const dLat = radiusM / R_EARTH_M;
  const cosLat = Math.cos(latRad);
  const dLon = radiusM / (R_EARTH_M * (Math.abs(cosLat) < 1e-6 ? 1e-6 : cosLat));
  const ring = [];
  for (let i = 0; i <= steps; i++) {
    const t = (i / steps) * 2 * Math.PI;
    ring.push([lon + dLon * Math.cos(t), lat + dLat * Math.sin(t)]);
  }
  return {
    type: "Feature",
    properties: {},
    geometry: { type: "Polygon", coordinates: [ring] },
  };
}
