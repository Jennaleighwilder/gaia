/**
 * Run Alembic migrations using the same executable stack as the backend:
 * - Packaged: ferry_backend.exe with FERRY_ALEMBIC_UPGRADE=1
 * - Dev: python -m alembic upgrade head (or py launcher on Windows)
 */
import { spawn } from "node:child_process";
import path from "node:path";

const MAX_LOG_CHARS = 48_000;

/**
 * @param {object} opts
 * @param {boolean} opts.isPackaged
 * @param {string} opts.resourcesPath
 * @param {string} opts.devBackendRoot
 * @param {string} opts.databaseUrl
 * @param {string} [opts.platform=process.platform]
 * @param {string} [opts.pythonExe]
 * @param {typeof spawn} [opts.spawnImpl]
 * @param {(line: string) => void} [opts.onOutputLine]
 */
export function runAlembicUpgrade(opts) {
  const spawnImpl = opts.spawnImpl ?? spawn;
  const platform = opts.platform ?? process.platform;
  const { isPackaged, resourcesPath, devBackendRoot, databaseUrl, pythonExe, onOutputLine } = opts;

  return new Promise((resolve) => {
    let output = "";
    const append = (chunk) => {
      let s = chunk.toString();
      output += s;
      if (output.length > MAX_LOG_CHARS) {
        output = output.slice(output.length - MAX_LOG_CHARS);
      }
      if (onOutputLine) {
        const lines = s.split(/\r?\n/);
        for (const line of lines) {
          if (line.trim()) onOutputLine(line.trim());
        }
      }
    };

    let child;
    if (isPackaged) {
      const backendDir = path.join(resourcesPath, "ferry_backend");
      const exe =
        platform === "win32"
          ? path.join(backendDir, "ferry_backend.exe")
          : path.join(backendDir, "ferry_backend");
      child = spawnImpl(exe, [], {
        cwd: backendDir,
        env: {
          ...process.env,
          DATABASE_URL: databaseUrl,
          FERRY_ALEMBIC_UPGRADE: "1",
        },
        stdio: ["ignore", "pipe", "pipe"],
        windowsHide: true,
      });
    } else {
      const win = platform === "win32";
      const py = pythonExe || process.env.FERRY_PYTHON || (win ? "py" : "python3");
      const usePyLauncher = py === "py" || (typeof py === "string" && py.toLowerCase().endsWith("py.exe"));
      const args = usePyLauncher
        ? ["-3", "-m", "alembic", "upgrade", "head"]
        : ["-m", "alembic", "upgrade", "head"];
      child = spawnImpl(py, args, {
        cwd: devBackendRoot,
        env: {
          ...process.env,
          DATABASE_URL: databaseUrl,
          PYTHONPATH: devBackendRoot,
          PYTHONUNBUFFERED: "1",
        },
        stdio: ["ignore", "pipe", "pipe"],
        windowsHide: true,
      });
    }

    child.stdout?.on("data", append);
    child.stderr?.on("data", append);
    child.on("error", (err) => {
      output += `\n[spawn error] ${err.message}\n`;
      resolve({ ok: false, exitCode: -1, output: output.trim() });
    });
    child.on("close", (exitCode) => {
      const code = exitCode === null ? -1 : exitCode;
      resolve({ ok: code === 0, exitCode: code, output: output.trim() });
    });
  });
}
