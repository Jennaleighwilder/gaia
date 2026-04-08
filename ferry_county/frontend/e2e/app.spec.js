import { test, expect } from "@playwright/test";

/**
 * Mock all /api traffic so the field shell does not depend on a backend or Vite proxy.
 * (CI runs Vite only; proxy to :8090 would fail with ECONNREFUSED.)
 */
test.beforeEach(async ({ page }) => {
  await page.route("**/api/**", async (route) => {
    const url = route.request().url();

    if (url.includes("/roads/geojson")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ type: "FeatureCollection", features: [] }),
      });
    }
    if (url.includes("/roads/search")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      });
    }
    if (url.includes("/roads")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      });
    }
    if (url.includes("/waypoints")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      });
    }
    if (url.includes("/sentinel/risks")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      });
    }
    if (url.includes("/sentinel/status")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          latest_scan: null,
          healthy: false,
          top_risk_roads: [],
        }),
      });
    }
    if (url.includes("/public/weather")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          temp_f: 55,
          humidity_pct: 40,
          wind_mph: 5,
          wind_direction: "",
          conditions: "Mock",
          fire_weather_watch: false,
          red_flag_warning: false,
          forecast_summary: "",
          alerts: [],
          fire_weather_index: 30,
          source: "mock",
          updated_at: "2026-01-01T00:00:00Z",
        }),
      });
    }
    if (url.includes("/public/status")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          last_updated: "2026-01-01T00:00:00Z",
          evacuation_zone_count: 0,
          road_closure_count: 0,
          active_incident_count: 0,
          active_evacuation_zones: [],
          road_closures_summary: [],
          incidents_summary: [],
        }),
      });
    }
    if (url.includes("/emergency/")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: [] }),
      });
    }
    if (url.includes("/compliance/match-ratio")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          compliant: true,
          ratio_percent: 30,
          federal_spend_total: 1000,
          match_documented_total: 500,
          match_ratio_required_percent: 25,
        }),
      });
    }

    return route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });
});

test("field shell loads with mocked API", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Ferry CWDG/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /sync/i })).toBeVisible();
});
