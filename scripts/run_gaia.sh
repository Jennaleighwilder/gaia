#!/bin/bash
# Start GAIA daemon + dashboard. Run from project root.
# GAIA_NO_PROXY=1 bypasses corporate proxy for NOAA/USGS fetches.

cd "$(dirname "$0")/.."
export GAIA_NO_PROXY="${GAIA_NO_PROXY:-1}"
# Writable matplotlib cache (avoids ~/.matplotlib permission issues).
export MPLCONFIGDIR="${MPLCONFIGDIR:-$(pwd)/runs/logs/mpl}"
mkdir -p "$MPLCONFIGDIR"

echo "Starting GAIA daemon (GAIA_NO_PROXY=$GAIA_NO_PROXY)..."
.venv/bin/python -m runtime.gaia_daemon &
DAEMON_PID=$!
sleep 3

echo "Starting dashboard on http://127.0.0.1:5001 ..."
.venv/bin/python -m runtime.dashboard.app &
DASH_PID=$!
sleep 3

echo ""
echo "GAIA running:"
echo "  Daemon PID: $DAEMON_PID"
echo "  Dashboard PID: $DASH_PID"
echo "  Dashboard: http://127.0.0.1:5001"
echo ""
echo "Ctrl+C to stop both."

wait
