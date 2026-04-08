import { openFieldDB } from "./fieldDb.js";

const KEY_ROADS = "roads_geojson";
const KEY_WAYPOINTS = "waypoints_items";

/**
 * @param {object} data — FeatureCollection
 */
export async function setCachedRoadsGeojson(data) {
  const db = await openFieldDB();
  await db.put("cache", { key: KEY_ROADS, savedAt: Date.now(), value: data });
}

/** @returns {Promise<object | null>} */
export async function getCachedRoadsGeojson() {
  const db = await openFieldDB();
  const row = await db.get("cache", KEY_ROADS);
  return row?.value ?? null;
}

/** @param {object[]} items */
export async function setCachedWaypoints(items) {
  const db = await openFieldDB();
  await db.put("cache", { key: KEY_WAYPOINTS, savedAt: Date.now(), value: items });
}

/** @returns {Promise<object[] | null>} */
export async function getCachedWaypoints() {
  const db = await openFieldDB();
  const row = await db.get("cache", KEY_WAYPOINTS);
  return row?.value ?? null;
}
