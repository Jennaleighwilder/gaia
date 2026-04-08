import { describe, it, expect, vi, afterEach } from "vitest";
import {
  waitForHealth,
  startUvicorn,
  startBackendProcess,
  stopBackend,
  defaultBackendRoot,
  resolveBackendLaunchConfig,
  readDatabaseUrlFromConfig,
} from "../lib/backendProcess.mjs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

describe("waitForHealth", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("retries fetch until 200", async () => {
    let n = 0;
    const fetchImpl = vi.fn(() => {
      n += 1;
      if (n < 3) {
        return Promise.reject(new Error("ECONNREFUSED"));
      }
      return Promise.resolve({ ok: true, status: 200 });
    });

    const result = await waitForHealth("http://127.0.0.1/health", {
      maxAttempts: 10,
      delayMs: 5,
      fetchImpl,
    });

    expect(result).toEqual({ ok: true, attempts: 3 });
    expect(fetchImpl).toHaveBeenCalledTimes(3);
  });

  it("throws after max attempts when never healthy", async () => {
    const fetchImpl = vi.fn(() => Promise.resolve({ ok: false, status: 503 }));

    await expect(
      waitForHealth("http://127.0.0.1/health", {
        maxAttempts: 4,
        delayMs: 2,
        fetchImpl,
      })
    ).rejects.toThrow(/Health check failed after 4 attempts/);

    expect(fetchImpl).toHaveBeenCalledTimes(4);
  });
});

describe("resolveBackendLaunchConfig", () => {
  it("uses bundled exe when packaged on Windows", () => {
    const cfg = resolveBackendLaunchConfig({
      isPackaged: true,
      resourcesPath: "/app/resources",
      devBackendRoot: "",
      port: 8765,
      platform: "win32",
    });
    expect(cfg.exe).toBe(path.join("/app/resources", "ferry_backend", "ferry_backend.exe"));
    expect(cfg.args).toEqual([]);
    expect(cfg.cwd).toBe(path.join("/app/resources", "ferry_backend"));
    expect(cfg.envExtra.FERRY_PORT).toBe("8765");
  });

  it("uses python + uvicorn in development mode", () => {
    const cfg = resolveBackendLaunchConfig({
      isPackaged: false,
      resourcesPath: "",
      devBackendRoot: "/tmp/ferry_county",
      port: 8765,
      platform: "linux",
      pythonExe: "python3",
    });
    expect(cfg.exe).toBe("python3");
    expect(cfg.args[0]).toBe("-m");
    expect(cfg.args[1]).toBe("uvicorn");
    expect(cfg.args).toContain("backend.main:app");
    expect(cfg.cwd).toBe("/tmp/ferry_county");
    expect(cfg.envExtra.PYTHONPATH).toBe("/tmp/ferry_county");
  });
});

describe("readDatabaseUrlFromConfig", () => {
  it("reads database_url from user config file", () => {
    const url = "postgresql+psycopg2://u:p@localhost:5432/db";
    const readFileSync = vi.fn(() => JSON.stringify({ database_url: url }));
    const existsSync = vi.fn(() => true);

    const got = readDatabaseUrlFromConfig("/fake/userData", { readFileSync, existsSync, env: {} });
    expect(got).toBe(url);
  });
});

describe("startUvicorn", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("invokes spawn with uvicorn and PYTHONPATH for backend root", () => {
    const spawnImpl = vi.fn(() => ({
      stderr: null,
      stdout: null,
      on: vi.fn(),
      kill: vi.fn(),
      exitCode: null,
    }));

    const cwd = "/tmp/ferry_county";
    startUvicorn({ cwd, port: 8765, pythonExe: "python3", spawnImpl });

    expect(spawnImpl).toHaveBeenCalledTimes(1);
    const [exe, args, opts] = spawnImpl.mock.calls[0];
    expect(exe).toBe("python3");
    expect(args).toEqual([
      "-m",
      "uvicorn",
      "backend.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      "8765",
    ]);
    expect(opts.cwd).toBe(cwd);
    expect(opts.env.PYTHONPATH).toBe(cwd);
    expect(opts.env.FERRY_PORT).toBe("8765");
  });

  it("spawn packaged backend omits uvicorn argv", () => {
    const spawnImpl = vi.fn(() => ({
      stderr: null,
      stdout: null,
      on: vi.fn(),
      kill: vi.fn(),
      exitCode: null,
    }));

    startBackendProcess({
      isPackaged: true,
      resourcesPath: "R:/res",
      devBackendRoot: "/noop",
      port: 8765,
      databaseUrl: "postgresql+psycopg2://x:y@localhost/z",
      platform: "win32",
      spawnImpl,
    });

    const [exe, args] = spawnImpl.mock.calls[0];
    expect(exe).toContain("ferry_backend.exe");
    expect(args).toEqual([]);
  });
});

describe("defaultBackendRoot", () => {
  it("resolves ferry_county root from lib/ location", () => {
    const root = defaultBackendRoot();
    expect(root).toBe(path.resolve(__dirname, "..", ".."));
    expect(path.basename(root)).toBe("ferry_county");
  });
});

describe("stopBackend", () => {
  it("sends SIGTERM on non-Windows", () => {
    const kill = vi.fn();
    const child = { exitCode: null, pid: 42, kill };

    stopBackend(child, 5000, { platform: "darwin" });

    expect(kill).toHaveBeenCalledWith("SIGTERM");
  });

  it("uses taskkill on Windows when pid is present", () => {
    const unref = vi.fn();
    const proc = { unref };
    const spawnImpl = vi.fn(() => proc);
    const child = { exitCode: null, pid: 999, kill: vi.fn() };

    stopBackend(child, 5000, { platform: "win32", spawnImpl });

    expect(spawnImpl).toHaveBeenCalledWith(
      "taskkill",
      ["/pid", "999", "/f", "/t"],
      expect.objectContaining({ windowsHide: true })
    );
    expect(unref).toHaveBeenCalled();
  });

  it("no-ops when child is null", () => {
    expect(() => stopBackend(null)).not.toThrow();
  });
});
