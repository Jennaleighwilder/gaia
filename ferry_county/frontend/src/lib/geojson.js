/**
 * @param {Array<[number, number] | [number, number, number]>} pts
 * @returns {import("geojson").FeatureCollection}
 */
/**
 * Mark grant roads with SENTINEL elevated/critical for map styling.
 * @param {object|null} fc - FeatureCollection from /roads/geojson
 * @param {Array<{road_id: number, risk_level?: string}>} riskItems - from /sentinel/risks
 */
export function mergeRoadsWithSentinel(fc, riskItems) {
  if (!fc || !fc.features) return fc;
  const elevated = new Set(
    (riskItems || [])
      .filter((r) => r.risk_level === "elevated" || r.risk_level === "critical")
      .map((r) => r.road_id)
  );
  return {
    ...fc,
    features: fc.features.map((f) => {
      const rid = f.properties?.road_id ?? f.id;
      const se =
        elevated.has(rid) || elevated.has(Number(rid)) ? true : false;
      return {
        ...f,
        properties: {
          ...f.properties,
          sentinel_elevated: se,
        },
      };
    }),
  };
}

export function trackLineFeature(pts) {
  const coordinates = (pts || []).map((p) => [p[0], p[1]]);
  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: { kind: "field_track" },
        geometry: { type: "LineString", coordinates },
      },
    ],
  };
}
