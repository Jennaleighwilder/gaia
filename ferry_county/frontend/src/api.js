/**
 * API base: production build uses same-origin `/api` (nginx proxy).
 * Local dev: `npm run dev` proxies /api → FastAPI, so leave empty or use `/api`.
 */
export function apiBase() {
  const v = import.meta.env.VITE_API_BASE;
  if (v === undefined || v === "") return "/api";
  return v.replace(/\/$/, "");
}

export async function apiFetch(path, options = {}) {
  const base = apiBase();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;
  const headers = { ...options.headers };
  if (options.body && typeof options.body === "string" && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

export function fetchRoads(limit = 500) {
  return apiFetch(`/roads?limit=${limit}`);
}

export function fetchGeoJson() {
  return apiFetch("/gis/export/geojson");
}

/** Field map layer: roads + treatment_status + is_grant_road */
export function fetchRoadsGeoJson() {
  return apiFetch("/roads/geojson");
}

export function fetchComplianceMatchRatio() {
  return apiFetch("/compliance/match-ratio");
}

export function fetchSentinelStatus() {
  return apiFetch("/sentinel/status");
}

/** Public portal — no auth */
export function fetchPublicStatus() {
  return apiFetch("/public/status");
}

export function fetchPublicEvacuationZones() {
  return apiFetch("/public/evacuation-zones");
}

export function fetchPublicRoadClosures() {
  return apiFetch("/public/road-closures");
}

export function fetchPublicIncidents() {
  return apiFetch("/public/incidents");
}

export function fetchPublicWeather() {
  return apiFetch("/public/weather");
}

export function postEmergencyEvacZone(body, actor) {
  return apiFetch("/emergency/evacuation-zones", {
    method: "POST",
    body: JSON.stringify(body),
    headers: { "X-Actor": actor || "steve", "Content-Type": "application/json" },
  });
}

export function patchEmergencyEvacZone(id, body, actor) {
  return apiFetch(`/emergency/evacuation-zones/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
    headers: { "X-Actor": actor || "steve", "Content-Type": "application/json" },
  });
}

export function postEmergencyRoadClosure(body, actor) {
  return apiFetch("/emergency/road-closures", {
    method: "POST",
    body: JSON.stringify(body),
    headers: { "X-Actor": actor || "steve", "Content-Type": "application/json" },
  });
}

export function searchEmergencyRoads(q, actor) {
  return apiFetch(`/emergency/roads-search?q=${encodeURIComponent(q)}`, {
    headers: actor ? { "X-Actor": actor } : {},
  });
}

export function fetchEmergencyEvacuationZones(actor) {
  return apiFetch("/emergency/evacuation-zones", {
    headers: actor ? { "X-Actor": actor } : {},
  });
}

export function fetchSentinelRisks(limit = 200) {
  return apiFetch(`/sentinel/risks?limit=${limit}`);
}

export function postSentinelScan(actor) {
  return apiFetch("/sentinel/scan", {
    method: "POST",
    headers: actor ? { "X-Actor": actor } : {},
  });
}

export function postTreatment(roadId, body, actor) {
  return apiFetch(`/treatments/roads/${roadId}`, {
    method: "POST",
    body: JSON.stringify(body),
    headers: actor ? { "X-Actor": actor } : {},
  });
}

export function postSyncOperation(body, actor) {
  return apiFetch("/sync/operations", {
    method: "POST",
    body: JSON.stringify(body),
    headers: actor ? { "X-Actor": actor } : {},
  });
}

export function postTrack(body, actor) {
  return apiFetch("/tracks", {
    method: "POST",
    body: JSON.stringify(body),
    headers: actor ? { "X-Actor": actor } : {},
  });
}

export function fetchTracks(limit = 25, roadId) {
  const q = roadId != null ? `?limit=${limit}&road_id=${roadId}` : `?limit=${limit}`;
  return apiFetch(`/tracks${q}`);
}

export function postWaypoint(body, actor) {
  return apiFetch("/waypoints", {
    method: "POST",
    body: JSON.stringify(body),
    headers: actor ? { "X-Actor": actor } : {},
  });
}

export function fetchWaypoints(limit = 50, roadId) {
  const q = roadId != null ? `?limit=${limit}&road_id=${roadId}` : `?limit=${limit}`;
  return apiFetch(`/waypoints${q}`);
}

/**
 * Multipart upload; links to treatment and/or waypoint metadata rows.
 */
export function uploadAttachment(file, { kind, treatmentId, waypointId, quarterlyId }, actor) {
  const fd = new FormData();
  fd.append("file", file);
  fd.append("kind", kind);
  if (treatmentId != null) fd.append("treatment_id", String(treatmentId));
  if (waypointId != null) fd.append("waypoint_id", String(waypointId));
  if (quarterlyId != null) fd.append("quarterly_financial_report_id", String(quarterlyId));
  return apiFetch("/attachments/upload", {
    method: "POST",
    body: fd,
    headers: actor ? { "X-Actor": actor } : {},
  });
}

export function attachmentDownloadUrl(attachmentId) {
  return `${apiBase()}/attachments/${attachmentId}/file`;
}
