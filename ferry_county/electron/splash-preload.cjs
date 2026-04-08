const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("splashApi", {
  onMigrationUpdate: (fn) => {
    const handler = (_evt, payload) => fn(payload);
    ipcRenderer.on("splash-migration", handler);
    return () => ipcRenderer.removeListener("splash-migration", handler);
  },
  retryMigration: () => ipcRenderer.send("ferry-migration-retry"),
});
