import { describe, it, expect, beforeEach } from "vitest";
import { clearAllQueued, enqueueSync, listQueued } from "./offlineQueue.js";

describe("offlineQueue", () => {
  beforeEach(async () => {
    await clearAllQueued();
  });

  it("enqueueSync stores track create for later flush", async () => {
    const body = {
      client_operation_id: "550e8400-e29b-41d4-a716-446655440000",
      entity_type: "track",
      operation: "create",
      payload: { road_id: null, points: [{ lon: -118, lat: 48 }, { lon: -118.01, lat: 48.01 }] },
    };
    await enqueueSync(body);
    const rows = await listQueued();
    expect(rows.length).toBe(1);
    expect(rows[0].body.entity_type).toBe("track");
    expect(rows[0].body.payload.points).toHaveLength(2);
  });
});
