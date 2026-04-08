(() => {
  const titleEl = document.getElementById("phase-title");
  const subEl = document.getElementById("phase-sub");
  const logEl = document.getElementById("migration-log");
  const errPanel = document.getElementById("migration-error");
  const errText = document.getElementById("error-text");
  const retryBtn = document.getElementById("retry-btn");

  if (!window.splashApi) {
    return;
  }

  window.splashApi.onMigrationUpdate((payload) => {
    if (!payload || typeof payload !== "object") {
      return;
    }

    if (payload.phase === "starting") {
      titleEl.textContent = payload.title ?? "Ferry County";
      subEl.textContent = payload.subtitle ?? "Starting system…";
      logEl.classList.add("hidden");
      logEl.textContent = "";
      errPanel.classList.add("hidden");
      retryBtn.classList.add("hidden");
      return;
    }

    if (payload.phase === "migrating") {
      titleEl.textContent = "Setting up database…";
      if (payload.statusLine) {
        subEl.textContent = payload.statusLine;
      } else {
        subEl.textContent = "Running migrations…";
      }
      logEl.classList.remove("hidden");
      errPanel.classList.add("hidden");
      retryBtn.classList.add("hidden");
      if (payload.clearLog) {
        logEl.textContent = "";
      }
      if (payload.chunk) {
        logEl.textContent += payload.chunk;
        if (logEl.textContent.length > 32000) {
          logEl.textContent = logEl.textContent.slice(logEl.textContent.length - 32000);
        }
      }
      return;
    }

    if (payload.phase === "migration_error") {
      titleEl.textContent = "Database setup failed";
      subEl.textContent = "Fix the issue below, then click Retry.";
      logEl.classList.remove("hidden");
      errPanel.classList.remove("hidden");
      retryBtn.classList.remove("hidden");
      errText.textContent = payload.output ?? "";
    }
  });

  retryBtn.addEventListener("click", () => {
    window.splashApi.retryMigration();
  });
})();
