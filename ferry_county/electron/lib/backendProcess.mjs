/**
 * Backend lifecycle — PyInstaller bundle (production) or uvicorn via Python (dev).
 */
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

/** Parent of electron/: repo ferry_county root */
export function defaultBackendRoot() {
  return path.resolve(__dirname, "..", "..");
}

export function configPathForUserData(userDataPath) {
  return path.join(userDataPath, "ferry_config.json");
}

/**
 * @param {string} userDataPath
 * @param {object} [options]
 * @param {typeof fs.readFileSync} [options.readFileSync]
 * @param {typeof fs.existsSync} [options.existsSync]
 * @param {NodeJS.ProcessEnv} [options.env]
 */
export function readDatabaseUrlFromConfig(userDataPath, options = {}) {
  const readFileSync = options.readFileSync ?? fs.readFileSync;
  const existsSync = options.existsSync ?? fs.existsSync;
  const env = options.env ?? process.env;
  const p = configPathForUserData(userDataPath);

  try {
    if (!existsSync(p)) {
      return env.DATABASE_URL ?? null;
    }
    const raw = readFileSync(p, "utf8");
    const cfg = JSON.parse(raw);
    if (typeof cfg.database_url === "string" && cfg.database_url.length > 0) {
      return cfg.database_url;
    }
  } catch {
    /* ignore */
  }
  return env.DATABASE_URL ?? null;
}

/**
 * @param {object} options
 * @param {boolean} options.isPackaged
 * @param {string} options.resourcesPath — process.resourcesPath when packaged
 * @param {string} options.devBackendRoot — ferry_county root in development
 * @param {number} [options.port]
 * @param {string} [options.platform=process.platform]
 * @param {string} [options.pythonExe]
 */
export function resolveBackendLaunchConfig(options) {
  const {
    isPackaged,
    resourcesPath,
    devBackendRoot,
    port = 8765,
    platform = process.platform,
    pythonExe,
  } = options;

  if (isPackaged) {
    const backendDir = path.join(resourcesPath, "ferry_backend");
    const exe =
      platform === "win32"
        ? path.join(backendDir, "ferry_backend.exe")
        : path.join(backendDir, "ferry_backend");
    return {
      exe,
      args: [],
      cwd: backendDir,
      envExtra: { FERRY_PORT: String(port) },
    };
  }

  const win = platform === "win32";
  const py = pythonExe || process.env.FERRY_PYTHON || (win ? "py" : "python3");
  const usePyLauncher = py === "py" || (typeof py === "string" && py.toLowerCase().endsWith("py.exe"));
  const args = usePyLauncher
    ? ["-3", "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", String(port)]
    : ["-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", String(port)];

  return {
    exe: py,
    args,
    cwd: devBackendRoot,
    envExtra: {
      PYTHONUNBUFFERED: "1",
      PYTHONPATH: devBackendRoot,
      FERRY_PORT: String(port),
    },
  };
}

/**
 * @param {object} opts
 * @param {boolean} opts.isPackaged
 * @param {string} opts.resourcesPath
 * @param {string} opts.devBackendRoot
 * @param {number} [opts.port]
 * @param {string | null} [opts.databaseUrl]
 * @param {typeof spawn} [opts.spawnImpl]
 * @param {string} [opts.pythonExe]
 * @param {string} [opts.platform]
 */
export function startBackendProcess(opts) {
  const spawnImpl = opts.spawnImpl ?? spawn;
  const { databaseUrl, ...resolveOpts } = opts;
  const { exe, args, cwd, envExtra } = resolveBackendLaunchConfig(resolveOpts);

  const env = {
    ...process.env,
    ...envExtra,
  };
  if (databaseUrl) {
    env.DATABASE_URL = databaseUrl;
  }

  return spawnImpl(exe, args, {
    cwd,
    env,
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });
}

/** @deprecated name — use startBackendProcess; kept for tests */
export function startUvicorn(opts) {
  return startBackendProcess({
    isPackaged: false,
    resourcesPath: "",
    devBackendRoot: opts.cwd,
    port: opts.port,
    pythonExe: opts.pythonExe,
    databaseUrl: opts.databaseUrl ?? null,
    spawnImpl: opts.spawnImpl,
  });
}

/**
 * @param {string} healthUrl e.g. http://127.0.0.1:8765/health
 * @param {object} [options]
 * @param {number} [options.maxAttempts=120]
 * @param {number} [options.delayMs=500]
 * @param {typeof fetch} [options.fetchImpl=globalThis.fetch]
 */
export async function waitForHealth(healthUrl, options = {}) {
  const maxAttempts = options.maxAttempts ?? 120;
  const delayMs = options.delayMs ?? 500;
  const fetchImpl = options.fetchImpl ?? globalThis.fetch;
  let lastErr = null;
  for (let i = 0; i < maxAttempts; i++) {
    let timeoutId;
    try {
      const ac = new AbortController();
      timeoutId = setTimeout(() => ac.abort(), 8000);
      const res = await fetchImpl(healthUrl, { signal: ac.signal });
      if (res.ok) return { ok: true, attempts: i + 1 };
      lastErr = new Error(`HTTP ${res.status}`);
    } catch (e) {
      lastErr = e;
    } finally {
      clearTimeout(timeoutId);
    }
    await new Promise((r) => setTimeout(r, delayMs));
  }
  throw new Error(`Health check failed after ${maxAttempts} attempts: ${lastErr?.message || "unknown"}`);
}

/**
 * @param {import('node:child_process').ChildProcess | null} child
 * @param {number} [killAfterMs=8000]
 * @param {object} [options]
 * @param {typeof spawn} [options.spawnImpl]
 * @param {string} [options.platform=process.platform]
 */
export function stopBackend(child, killAfterMs = 8000, options = {}) {
  const spawnImpl = options.spawnImpl ?? spawn;
  const platform = options.platform ?? process.platform;

  if (!child || child.exitCode != null) return;

  if (platform === "win32" && typeof child.pid === "number") {
    try {
      spawnImpl("taskkill", ["/pid", String(child.pid), "/f", "/t"], {
        windowsHide: true,
        stdio: "ignore",
        detached: true,
      }).unref?.();
    } catch {
      /* ignore */
    }
    return;
  }

  try {
    child.kill("SIGTERM");
  } catch {
    /* ignore */
  }
  const t = setTimeout(() => {
    try {
      if (child.exitCode == null) child.kill("SIGKILL");
    } catch {
      /* ignore */
    }
  }, killAfterMs);
  t.unref?.();
}
