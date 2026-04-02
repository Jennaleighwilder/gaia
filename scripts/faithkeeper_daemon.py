#!/usr/bin/env python3
"""
Faithkeeper daemon runner.

Keeps one living Avalon process breathing over time so the Faithkeeper's
daemon thread has a process to inhabit. This is the durable overnight
surface the kingdom needs; the in-process daemon alone dies when the
calling shell exits.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.chdir(ROOT)

from avalon.avalon import Avalon  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Avalon Faithkeeper overnight.")
    parser.add_argument("--interval", type=float, default=300.0, help="Seconds between ceremonies.")
    parser.add_argument("--seed", type=int, default=3, help="Manual ceremonies to perform before daemon mode.")
    parser.add_argument(
        "--status-file",
        default=str(ROOT / "runs" / "faithkeeper_status.json"),
        help="Path to the runtime status file.",
    )
    return parser.parse_args()


class FaithkeeperDaemon:
    def __init__(self, interval: float, seed: int, status_file: Path):
        self.interval = interval
        self.seed = seed
        self.status_file = status_file
        self.stop_event = threading.Event()
        self.avalon = Avalon()
        self.avalon.found_kingdom()

    def _write_status(self, phase: str):
        self.status_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "phase": phase,
            "pid": os.getpid(),
            "updated_at": time.time(),
            "faithkeeper": self.avalon.faithkeeper.status,
        }

        try:
            payload["latest_journal_entry"] = self._latest_journal_entry()
        except Exception:
            payload["latest_journal_entry"] = None

        with self.status_file.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)

    def _latest_journal_entry(self):
        log_path = ROOT / "memory" / "faithkeeper_log.jsonl"
        if not log_path.exists():
            return None

        last = None
        with log_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    last = line
        return json.loads(last) if last else None

    def _graceful_stop(self, signum, _frame):
        self._write_status(f"stopping:{signum}")
        self.stop_event.set()

    def run(self) -> int:
        signal.signal(signal.SIGINT, self._graceful_stop)
        signal.signal(signal.SIGTERM, self._graceful_stop)

        print(f"[Faithkeeper] Kingdom waking at {ROOT}")
        print(f"[Faithkeeper] Seeding {self.seed} manual ceremonies")
        for idx in range(self.seed):
            if self.stop_event.is_set():
                break
            record = self.avalon.faithkeeper.perform_ceremony()
            print(
                "[Faithkeeper] Seed ceremony "
                f"{idx + 1}/{self.seed} -> #{record.number} "
                f"alive {record.thanksgiving.get('alive_count', 0)}/"
                f"{record.thanksgiving.get('total_systems', 0)} "
                f"lessons {record.lessons_learned}"
            )
            self._write_status("seeding")

        if not self.stop_event.is_set():
            print(f"[Faithkeeper] Starting living rhythm every {self.interval:.0f}s")
            self.avalon.start_breathing(self.interval)
            self._write_status("breathing")

        while not self.stop_event.is_set():
            self._write_status("breathing")
            time.sleep(5)

        print("[Faithkeeper] Resting the kingdom")
        self.avalon.stop_breathing()
        self._write_status("resting")
        return 0


def main() -> int:
    args = parse_args()
    daemon = FaithkeeperDaemon(
        interval=args.interval,
        seed=max(args.seed, 0),
        status_file=Path(args.status_file),
    )
    return daemon.run()


if __name__ == "__main__":
    raise SystemExit(main())
