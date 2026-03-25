#!/usr/bin/env bash
# Fetch ASOS observations for all events in a corpus JSON.
# Uses --skip-existing to avoid re-downloading already-built fixtures.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

EVENT_FILE="${1:-tests/fixtures/master_validation_corpus.json}"
LOG=/tmp/asos_fetch_all_events.log
export PYTHONUNBUFFERED=1
{
  echo "==== $(date -Iseconds) start — $EVENT_FILE ===="
  .venv/bin/python scripts/fetch_asos_full_backtest.py \
    --event-file "$EVENT_FILE" \
    --obs-dir tests/fixtures/historical_observations \
    --batch-size 50 \
    --delay 0.5 \
    --skip-existing
  echo "==== $(date -Iseconds) exit $? ===="
} >>"$LOG" 2>&1 &
echo "ASOS fetch PID $! — watch: tail -f $LOG"
echo "Fixtures: find tests/fixtures/historical_observations -name 'event_noaa_*.json' | wc -l"
