import { describe, it, expect, vi } from "vitest";
import { runAlembicUpgrade } from "../lib/migrations.mjs";

function mockSpawnForExit(exitCode) {
  return vi.fn(() => {
    let closeHandler;
    const child = {
      stdout: { on: vi.fn() },
      stderr: { on: vi.fn() },
      on(ev, fn) {
        if (ev === "close") closeHandler = fn;
      },
    };
    queueMicrotask(() => closeHandler?.(exitCode));
    return child;
  });
}

describe("runAlembicUpgrade", () => {
  it("treats exit code 0 as success and non-zero as failure", async () => {
    const spawnOk = mockSpawnForExit(0);
    const ok = await runAlembicUpgrade({
      isPackaged: false,
      resourcesPath: "",
      devBackendRoot: "/tmp/ferry_county",
      databaseUrl: "postgresql+psycopg2://u:p@localhost/db",
      platform: "linux",
      pythonExe: "python3",
      spawnImpl: spawnOk,
    });
    expect(ok.ok).toBe(true);
    expect(ok.exitCode).toBe(0);

    const spawnBad = mockSpawnForExit(1);
    const bad = await runAlembicUpgrade({
      isPackaged: false,
      resourcesPath: "",
      devBackendRoot: "/tmp/ferry_county",
      databaseUrl: "postgresql+psycopg2://u:p@localhost/db",
      platform: "linux",
      pythonExe: "python3",
      spawnImpl: spawnBad,
    });
    expect(bad.ok).toBe(false);
    expect(bad.exitCode).toBe(1);
  });
});
