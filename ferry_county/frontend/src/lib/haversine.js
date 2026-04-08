/** Mean Earth radius in statute miles (WGS84). */
const R_MI = 3958.7613;

function toRad(d) {
  return (d * Math.PI) / 180;
}

/**
 * Great-circle distance in miles between two WGS84 points.
 */
export function haversineMiles(lat1, lon1, lat2, lon2) {
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * R_MI * Math.asin(Math.min(1, Math.sqrt(a)));
}

/**
 * @param {Array<[number, number] | [number, number, number]>} points — [lon, lat] or [lon, lat, accuracy]
 * @returns {number} cumulative path length in miles
 */
export function pathLengthMiles(points) {
  if (!points || points.length < 2) return 0;
  let total = 0;
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1];
    const b = points[i];
    total += haversineMiles(a[1], a[0], b[1], b[0]);
  }
  return total;
}
