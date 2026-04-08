import { describe, it, expect, vi, afterEach } from "vitest";

describe("apiBase", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("returns /api when VITE_API_BASE is empty", async () => {
    vi.stubEnv("VITE_API_BASE", "");
    vi.resetModules();
    const { apiBase } = await import("./api.js");
    expect(apiBase()).toBe("/api");
  });

  it("strips trailing slash from VITE_API_BASE", async () => {
    vi.stubEnv("VITE_API_BASE", "https://example.com/api/");
    vi.resetModules();
    const { apiBase } = await import("./api.js");
    expect(apiBase()).toBe("https://example.com/api");
  });
});
