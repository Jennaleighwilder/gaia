# Cursor prompt — Live road search (Field app)

**Status:** Implemented in-repo: **`GET /roads/search`**, **`RoadSearchPanel`**, **`MapView` highlight layer** — keep this doc as the contract / regression reference.

**Goal:** David and Steve type a **road name** (partial match) and see that road on the **map** immediately — **live, interactive**, backed by the database, **not** a static KMZ browse.

---

## Backend

1. Add **`GET /roads/search`** on the **roads** router (same prefix as `/roads/geojson` — public read for field operators).

   **Query params:**
   - **`q`** (required): non-empty after trim; max length **200** (reject longer with **400**).
   - If `q` is missing or empty/whitespace → **400** with detail `"q required"` or similar.

2. **Matching:** `ILIKE` on `roads.road_name` with pattern `%{q}%`, **exclude** `deleted_at IS NOT NULL`.

3. **Limit:** **10** results max, ordered by `road_name` ascending.

4. **Response:** `200` with `{"items": [...]}`.

   Each item must include at least:
   - `id` (int)
   - `road_name` (string)
   - `road_number` (string or null)
   - `cemp_miles` (number or null) — for “grant road” badge in UI
   - **`center_lat`**, **`center_lon`** — from PostGIS **`ST_Y(ST_Centroid(geometry))`** and **`ST_X(ST_Centroid(geometry))`** (EPSG:4326)

5. **No** `500` on normal “no match” — return **`200`** with `items: []`.

6. **Security:** Parameterized query only (SQLAlchemy); no raw string concatenation of `q`.

7. **Optional:** Keep **`GET /emergency/roads-search`** for EOC compatibility or delegate to shared service — avoid duplicating logic.

---

## Frontend (`ferry_county/frontend`)

1. **`api.js`:** `searchRoads(q)` → `GET /api/roads/search?q=...` (use `apiFetch`).

2. **Component:** `RoadSearchPanel.jsx` (or overlay) **inside** `MapView` children so **`useMapLibre()`** works.

   - Text input with **debounced** search (300ms).
   - While typing: show dropdown of matches (name + road number + grant badge if `cemp_miles > 0`).
   - **Offline:** if `!navigator.onLine`, show message “Search requires network” and do not call API.

3. **Map behavior** on select:
   - **`map.flyTo({ center: [center_lon, center_lat], zoom: 14, duration: 1500 })`**
   - Set **highlight** on that road id (see MapView).

4. **`MapView.jsx`:**
   - Prop **`highlightRoadId`** (number | null).
   - Add **second line layer** `roads-search-highlight` (or filter) — **yellow** `#f0c808`, width **6**, above base roads — filter `["==", ["get", "road_id"], highlightRoadId]`.
   - Clear highlight when search clears or new search.

5. **`App.jsx`:** State `highlightRoadId` + render `RoadSearchPanel` **inside** `<MapView>...</MapView>` (floating **top-left** over map with `position: absolute` + z-index).

6. **Accessibility:** Input has `aria-label="Search roads by name"`.

---

## Tests

- **pytest:** `tests/test_roads_search.py` — empty `q` → 400; nonsense `q` → 200 `[]`; known substring returns `<= 10` with `center_lat/lon` numeric.
- **api.test.js** (optional): mock `fetch` for `/roads/search`.

---

## Acceptance checklist

- [ ] `curl` empty `q` → **400**  
- [ ] `curl` valid `q` with no matches → **200** `[]`  
- [ ] UI: type → list → pick → **fly** + **yellow** line  
- [ ] Grant road shows badge when `cemp_miles > 0`  
- [ ] Offline shows friendly message  
- [ ] `ferry_county/README.md` not overwritten by handoff docs  

---

*After implementation, run the **Gauntlet** section 3 in `FERRY_COUNTY_GAUNTLET.md`.*
