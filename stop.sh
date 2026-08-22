#!/usr/bin/env bash
# Graph App — stop both backend & frontend
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$ROOT/data/pids"

stopped=0

# Try saved PIDs first
if [ -f "$PID_DIR/backend.pid" ]; then
    PID=$(cat "$PID_DIR/backend.pid")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping backend (PID $PID)…"
        kill -- -"$PID" 2>/dev/null || kill "$PID" 2>/dev/null || true
        sleep 0.5
        kill -9 "$PID" 2>/dev/null || true
        stopped=$((stopped+1))
    fi
    rm -f "$PID_DIR/backend.pid"
fi

if [ -f "$PID_DIR/frontend.pid" ]; then
    PID=$(cat "$PID_DIR/frontend.pid")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping frontend (PID $PID)…"
        kill -- -"$PID" 2>/dev/null || kill "$PID" 2>/dev/null || true
        sleep 0.5
        kill -9 "$PID" 2>/dev/null || true
        stopped=$((stopped+1))
    fi
    rm -f "$PID_DIR/frontend.pid"
fi

# Also clean up any stragglers by name (in case PID file is stale)
pkill -f "uvicorn app.main" 2>/dev/null && stopped=$((stopped+1)) || true
pkill -f "vite" 2>/dev/null && stopped=$((stopped+1)) || true

if [ $stopped -gt 0 ]; then
    echo "Done. ($stopped process group(s) stopped)"
else
    echo "No running processes found."
fi
