#!/usr/bin/env bash
# Graph App — show status of both services
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_DIR="$ROOT/data/pids"

echo "═══════════════════════════════════════════"
echo "  Graph App — Status"
echo "═══════════════════════════════════════════"

# Backend
if [ -f "$PID_DIR/backend.pid" ]; then
    PID=$(cat "$PID_DIR/backend.pid")
    if kill -0 "$PID" 2>/dev/null; then
        BACKEND_STATUS="✓ Running (PID $PID)"
    else
        BACKEND_STATUS="✗ PID $PID not alive (stale)"
    fi
else
    BACKEND_STATUS="✗ Not running"
fi

# Frontend
if [ -f "$PID_DIR/frontend.pid" ]; then
    PID=$(cat "$PID_DIR/frontend.pid")
    if kill -0 "$PID" 2>/dev/null; then
        FRONTEND_STATUS="✓ Running (PID $PID)"
    else
        FRONTEND_STATUS="✗ PID $PID not alive (stale)"
    fi
else
    FRONTEND_STATUS="✗ Not running"
fi

# Live checks
BACKEND_HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8765/api/health 2>/dev/null || echo "000")
FRONTEND_HTTP=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5173 2>/dev/null || echo "000")

echo "  Backend:  $BACKEND_STATUS  (HTTP: $BACKEND_HTTP)"
echo "  Frontend: $FRONTEND_STATUS  (HTTP: $FRONTEND_HTTP)"
echo ""
echo "  URLs:"
echo "    Frontend: http://127.0.0.1:5173"
echo "    Backend:  http://127.0.0.1:8765"
echo "═══════════════════════════════════════════"
