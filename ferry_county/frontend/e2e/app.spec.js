import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.route("**/api/roads*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [] }),
    })
  );
  await page.route("**/api/gis/export/geojson*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ type: "FeatureCollection", features: [] }),
    })
  );
});

test("field shell loads with mocked API", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /Ferry CWDG/ })).toBeVisible();
  await expect(page.getByRole("heading", { name: /sync/i })).toBeVisible();
});
