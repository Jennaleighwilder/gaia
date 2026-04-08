import { describe, it, expect } from "vitest";
import { haversineMiles, pathLengthMiles } from "./haversine.js";

describe("haversineMiles", () => {
  it("one degree latitude ≈ 69 statute miles at mid-lat (sanity)", () => {
    const d = haversineMiles(40, -100, 41, -100);
    expect(d).toBeGreaterThan(68);
    expect(d).toBeLessThan(70);
  });
});

describe("pathLengthMiles", () => {
  it("~1 mile north-south segment is 1.0 ± 0.01 mi", () => {
    const lat = 48.65;
    const lon = -118.6;
    const deltaLat = 1 / 69; // ~1 statute mile
    const mi = pathLengthMiles([
      [lon, lat],
      [lon, lat + deltaLat],
    ]);
    expect(mi).toBeGreaterThan(0.99);
    expect(mi).toBeLessThan(1.01);
  });
});
