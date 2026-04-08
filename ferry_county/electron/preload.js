const { contextBridge, ipcRenderer } = require("electron");
const fs = require("node:fs");
const path = require("node:path");

const pkgPath = path.join(__dirname, "package.json");
const pkg = JSON.parse(fs.readFileSync(pkgPath, "utf8"));

contextBridge.exposeInMainWorld("ferryShell", {
  appVersion: pkg.version ?? "0.0.0",
  isOnline: () => navigator.onLine,
  testDatabase: (url) => ipcRenderer.invoke("ferry:test-database", url),
  saveConfig: (cfg) => ipcRenderer.invoke("ferry:save-config", cfg),
  continueSetup: () => ipcRenderer.invoke("ferry:continue-setup"),
});
