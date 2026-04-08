/**
 * Ferry County Field System — first-run DB wizard → splash → bundled or dev backend → fullscreen app.
 */
import { app, BrowserWindow, dialog, ipcMain } from "electron";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  defaultBackendRoot,
  readDatabaseUrlFromConfig,
  startBackendProcess,
  stopBackend,
  waitForHealth,
} from "./lib/backendProcess.mjs";
import { runAlembicUpgrade } from "./lib/migrations.mjs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const PORT = 8765;
const HEALTH_URL = `http://127.0.0.1:${PORT}/health`;
const APP_URL = `http://127.0.0.1:${PORT}/`;

let backendChild = null;
let mainWindow = null;
let splashWindow = null;
let setupWizardWindow = null;
let setupCompleteResolver = null;
let setupCompleted = false;
let migrationRetryResolve = null;

function userDataPath() {
  return app.getPath("userData");
}

function setupIsComplete() {
  const p = path.join(userDataPath(), "ferry_config.json");
  if (fs.existsSync(p)) {
    try {
      const c = JSON.parse(fs.readFileSync(p, "utf8"));
      return typeof c.database_url === "string" && c.database_url.length > 0;
    } catch {
      return false;
    }
  }
  if (!app.isPackaged && process.env.DATABASE_URL) {
    return true;
  }
  return false;
}

function databaseUrlForBackend() {
  return readDatabaseUrlFromConfig(userDataPath());
}

async function testDatabaseConnection(dbUrl) {
  try {
    const { Client } = await import("pg");
    const clientUrl = String(dbUrl).replace(/^postgresql\+psycopg2:/i, "postgresql:");
    const client = new Client({
      connectionString: clientUrl,
      connectionTimeoutMillis: 10_000,
    });
    await client.connect();
    await client.query("SELECT 1");
    await client.end();
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : String(e) };
  }
}

function registerIpcHandlers() {
  ipcMain.handle("ferry:test-database", async (_evt, url) => testDatabaseConnection(url));

  ipcMain.handle("ferry:save-config", async (_evt, cfg) => {
    const dir = userDataPath();
    fs.mkdirSync(dir, { recursive: true });
    const p = path.join(dir, "ferry_config.json");
    fs.writeFileSync(p, JSON.stringify(cfg, null, 2), "utf8");
    return { ok: true };
  });

  ipcMain.handle("ferry:continue-setup", async () => {
    setupCompleted = true;
    const done = setupCompleteResolver;
    setupCompleteResolver = null;
    done?.();
    if (setupWizardWindow && !setupWizardWindow.isDestroyed()) {
      setupWizardWindow.close();
    }
    return { ok: true };
  });

  ipcMain.on("ferry-migration-retry", () => {
    const r = migrationRetryResolve;
    migrationRetryResolve = null;
    r?.();
  });
}

function sendSplashPayload(payload) {
  if (splashWindow && !splashWindow.isDestroyed()) {
    splashWindow.webContents.send("splash-migration", payload);
  }
}

function waitForSplashReady() {
  return new Promise((resolve) => {
    if (!splashWindow || splashWindow.isDestroyed()) {
      resolve();
      return;
    }
    splashWindow.webContents.once("did-finish-load", () => resolve());
  });
}

async function waitForMigrations(dbUrl) {
  const devRoot = defaultBackendRoot();
  for (;;) {
    sendSplashPayload({
      phase: "migrating",
      statusLine: "Running Alembic upgrade…",
      clearLog: true,
    });

    const result = await runAlembicUpgrade({
      isPackaged: app.isPackaged,
      resourcesPath: process.resourcesPath,
      devBackendRoot: devRoot,
      databaseUrl: dbUrl,
      onOutputLine: (line) => {
        sendSplashPayload({
          phase: "migrating",
          statusLine: line,
          chunk: `${line}\n`,
        });
      },
    });

    if (result.ok) {
      sendSplashPayload({
        phase: "starting",
        title: "Ferry County",
        subtitle: "Starting system…",
      });
      return;
    }

    sendSplashPayload({
      phase: "migration_error",
      output: result.output || "(Alembic produced no output)",
    });

    await new Promise((resolve) => {
      migrationRetryResolve = resolve;
    });
  }
}

function createSplash() {
  splashWindow = new BrowserWindow({
    width: 520,
    height: 420,
    frame: false,
    resizable: false,
    show: true,
    center: true,
    title: "Ferry County Field System",
    webPreferences: {
      preload: path.join(__dirname, "splash-preload.cjs"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
  });
  splashWindow.loadFile(path.join(__dirname, "splash.html"));
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    show: false,
    fullscreen: true,
    autoHideMenuBar: true,
    title: "Ferry County Field System",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.setMenuBarVisibility(false);

  if (!app.isPackaged && process.env.ELECTRON_DEVTOOLS === "1") {
    mainWindow.webContents.openDevTools({ mode: "detach" });
  }

  mainWindow.loadURL(APP_URL);

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function showFirstRunWizard() {
  return new Promise((resolve) => {
    setupCompleted = false;
    setupCompleteResolver = resolve;

    setupWizardWindow = new BrowserWindow({
      width: 560,
      height: 680,
      show: true,
      center: true,
      title: "Ferry County Field System — Setup",
      webPreferences: {
        preload: path.join(__dirname, "preload.js"),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
      },
    });

    setupWizardWindow.loadFile(path.join(__dirname, "setup", "FirstRunWizard.html"));

    setupWizardWindow.on("closed", () => {
      setupWizardWindow = null;
      if (!setupCompleted) {
        app.quit();
      }
    });
  });
}

async function bootstrapBackendAndOpen() {
  const dbUrl = databaseUrlForBackend();
  if (!dbUrl) {
    throw new Error("Database is not configured. Complete first-run setup.");
  }

  const devRoot = defaultBackendRoot();
  createSplash();
  await waitForSplashReady();
  await waitForMigrations(dbUrl);

  backendChild = startBackendProcess({
    isPackaged: app.isPackaged,
    resourcesPath: process.resourcesPath,
    devBackendRoot: devRoot,
    port: PORT,
    databaseUrl: dbUrl,
  });

  backendChild.stderr?.on("data", (chunk) => {
    console.error("[backend]", chunk.toString());
  });
  backendChild.stdout?.on("data", (chunk) => {
    console.log("[backend]", chunk.toString());
  });
  backendChild.on("error", (err) => {
    console.error("[backend] process error", err);
  });

  await waitForHealth(HEALTH_URL, { maxAttempts: 120, delayMs: 500 });
  createMainWindow();
}

async function bootstrap() {
  try {
    await bootstrapBackendAndOpen();
  } catch (err) {
    console.error(err);
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close();
      splashWindow = null;
    }
    dialog.showErrorBox(
      "Ferry County Field System",
      `Could not start the application.\n\n${err instanceof Error ? err.message : String(err)}`
    );
    app.quit();
  }
}

app.whenReady().then(async () => {
  registerIpcHandlers();

  if (!setupIsComplete()) {
    await showFirstRunWizard();
  }

  await bootstrap();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  stopBackend(backendChild);
  backendChild = null;
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0 && backendChild) {
    createMainWindow();
  }
});
