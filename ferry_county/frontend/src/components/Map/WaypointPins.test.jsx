import { describe, it, expect } from "vitest";
import { waypointPinColor } from "./WaypointPins.jsx";

describe("waypointPinColor", () => {
  it("maps sign / mile_marker / hazard / note", () => {
    expect(waypointPinColor("sign")).toBe("#2f9e44");
    expect(waypointPinColor("mile_marker")).toBe("#228be6");
    expect(waypointPinColor("hazard")).toBe("#f03e3e");
    expect(waypointPinColor("note")).toBe("#868e96");
  });

  it("defaults unknown types to grey", () => {
    expect(waypointPinColor("material_site")).toBe("#868e96");
    expect(waypointPinColor(null)).toBe("#868e96");
  });
});
