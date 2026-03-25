"""Poll historical_observations for event_noaa_*.json; start master backtest when count >= 500."""
import os
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
OBS = ROOT / "tests" / "fixtures" / "historical_observations"
INTERVAL_SEC = 600


def main() -> None:
    print("Watching for noaa fixtures...", flush=True)
    while True:
        count = len(list(OBS.glob("event_noaa_*.json")))
        print(f"noaa fixtures: {count}", flush=True)
        if count >= 500:
            print("500+ fixtures ready. Starting backtest.", flush=True)
            env = {
                **os.environ,
                "GAIA_OFFLINE": "1",
                "GAIA_NO_EVIDENCE": "1",
                "GAIA_DB_PATH": "/tmp/gaia_master.db",
                "GAIA_BUS_DIR": "/tmp/gaia_master_bus",
                "PYTHONUNBUFFERED": "1",
            }
            log = open("/tmp/master_backtest.txt", "w", encoding="utf-8")
            subprocess.Popen(
                [
                    str(ROOT / ".venv" / "bin" / "python"),
                    str(ROOT / "scripts" / "run_full_backtest.py"),
                    "--event-file",
                    str(ROOT / "tests" / "fixtures" / "master_validation_corpus.json"),
                ],
                cwd=str(ROOT),
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            print("Backtest started. Check /tmp/master_backtest.txt", flush=True)
            break
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    main()
