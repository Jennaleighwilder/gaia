import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { clearAllQueued, enqueueSync } from "../lib/offlineQueue.js";

vi.mock("../api.js", () => ({
  postSyncOperation: vi.fn(),
}));

import { postSyncOperation } from "../api.js";
import { useOfflineSync } from "./useOfflineSync.js";

const T1 = "550e8400-e29b-41d4-a716-446655440001";
const T2 = "550e8400-e29b-41d4-a716-446655440002";
const T3 = "550e8400-e29b-41d4-a716-446655440003";

describe("useOfflineSync", () => {
  beforeEach(async () => {
    await clearAllQueued();
    vi.clearAllMocks();
    postSyncOperation.mockResolvedValue({ status: "applied" });
    Object.defineProperty(navigator, "onLine", { value: true, configurable: true, writable: true });
  });

  it("flush sends track → treatment → waypoint regardless of enqueue order", async () => {
    Object.defineProperty(navigator, "onLine", { value: false, configurable: true, writable: true });
    const order = [];
    postSyncOperation.mockImplementation(async (body) => {
      order.push(body.entity_type);
      return { ok: true };
    });

    const { result } = renderHook(() => useOfflineSync("steve"));

    await act(async () => {
      await result.current.queueSync("waypoint", "create", { lat: 1, lon: -1 }, T1);
      await result.current.queueSync("treatment", "create", { road_id: 1, treatment_date: "2026-01-01", miles_treated: 0.1 }, T2);
      await result.current.queueSync("track", "create", { points: [{ lon: -118, lat: 48 }, { lon: -118.01, lat: 48 }] }, T3);
    });

    expect(order).toHaveLength(0);

    Object.defineProperty(navigator, "onLine", { value: true, configurable: true, writable: true });

    await act(async () => {
      await result.current.flush();
    });

    expect(order).toEqual(["track", "treatment", "waypoint"]);
    expect(result.current.pending).toBe(0);
  });

  it("503 stops flush without dequeue so the next flush can retry", async () => {
    await enqueueSync({
      client_operation_id: T1,
      entity_type: "treatment",
      operation: "create",
      payload: { road_id: 1, treatment_date: "2026-01-01", miles_treated: 0.1 },
    });

    postSyncOperation.mockRejectedValueOnce(new Error("503 Service Unavailable: upstream"));

    const { result } = renderHook(() => useOfflineSync("steve"));

    await act(async () => {
      await result.current.refresh();
    });
    expect(result.current.pending).toBe(1);

    await act(async () => {
      await result.current.flush();
    });

    expect(postSyncOperation).toHaveBeenCalledTimes(1);
    expect(result.current.pending).toBe(1);
    expect(result.current.lastError).toContain("503");

    postSyncOperation.mockResolvedValueOnce({ status: "applied" });

    await act(async () => {
      await result.current.flush();
    });

    expect(postSyncOperation).toHaveBeenCalledTimes(2);
    expect(result.current.pending).toBe(0);
    expect(result.current.lastError).toBeNull();
  });

  it("422 removes the bad op and continues with remaining queue", async () => {
    await enqueueSync({
      client_operation_id: T3,
      entity_type: "track",
      operation: "create",
      payload: { points: [{ lon: -118, lat: 48 }, { lon: -118.01, lat: 48 }] },
    });
    await enqueueSync({
      client_operation_id: T2,
      entity_type: "treatment",
      operation: "create",
      payload: { road_id: 1, treatment_date: "2026-01-01", miles_treated: 0.1 },
    });

    postSyncOperation
      .mockRejectedValueOnce(new Error("422 Unprocessable Entity: invalid track"))
      .mockResolvedValueOnce({ status: "applied" });

    const { result } = renderHook(() => useOfflineSync("steve"));

    await act(async () => {
      await result.current.refresh();
    });
    expect(result.current.pending).toBe(2);

    await act(async () => {
      await result.current.flush();
    });

    expect(postSyncOperation).toHaveBeenCalledTimes(2);
    expect(result.current.pending).toBe(0);
    const types = postSyncOperation.mock.calls.map((c) => c[0].entity_type);
    expect(types).toEqual(["track", "treatment"]);
  });
});
