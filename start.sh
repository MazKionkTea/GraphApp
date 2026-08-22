#!/usr/bin/env bash
# Graph App — start both backend & frontend (with proper detachment + error handling)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

DATA_DIR="$ROOT/data"
LOGS_DIR="$DATA_DIR/logs"
BACKEND_LOG="$LOGS_DIR/backend.log"
FRONTEND_LOG="$LOGS_DIR/frontend.log"
PID_DIR="$DATA_DIR/pids"

mkdir -p "$DATA_DIR" "$LOGS_DIR" "$PID_DIR"

# ============================================================
# Helper: check if port is in use
# ============================================================
check_port() {
    local port=$1
    if ss -tlnp 2>/dev/null | grep -q ":$port " || netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        return 0  # in use
    fi
    return 1  # free
}

# ============================================================
# Backend
# ============================================================
echo "→ Setting up backend (FastAPI on :8765)…"
cd "$ROOT/server"

# Create venv if missing
if [ ! -d "venv" ]; then
    echo "  Creating venv (this can take a minute)…"
    if ! python3 -m venv venv; then
        echo ""
        echo "  ✗ Failed to create venv."
        echo "    Fix: install python3-venv —"
        echo "      sudo pacman -S python-virtualenv  (Arch)"
        echo "      sudo apt install python3-venv      (Debian/Ubuntu)"
        echo ""
        exit 1
    fi
fi

# shellcheck disable=SC1091
source venv/bin/activate

# Upgrade pip first to ensure wheel selection is correct
echo "  Upgrading pip…"
./venv/bin/pip install --quiet --upgrade pip wheel 2>&1 | tail -2 || true

# Install requirements — try wheel-only first, fall back to source
echo "  Installing Python dependencies…"
PIP_LOG="$LOGS_DIR/pip-install.log"
if ! ./venv/bin/pip install --only-binary=:all: -r requirements.txt > "$PIP_LOG" 2>&1; then
    echo "  ⚠ Wheel-only install failed. Trying with source build…"
    if ! ./venv/bin/pip install -r requirements.txt > "$PIP_LOG" 2>&1; then
        echo ""
        echo "  ✗ pip install failed. Last log lines:"
        echo "  ─────────────────────────────"
        tail -20 "$PIP_LOG" | sed 's/^/    /'
        echo "  ─────────────────────────────"
        echo ""
        echo "  Common causes:"
        echo "    1. Rust toolchain missing (pydantic-core needs it to build)"
        echo "       → Install:  sudo pacman -S base-devel rust  (Arch)"
        echo "                  sudo apt install build-essential rustc  (Debian)"
        echo "    2. Network/proxy issue"
        echo "    3. Python version too new for pinned packages"
        echo "       → Check:  python3 --version"
        echo ""
        echo "  Full log: $PIP_LOG"
        echo ""
        exit 1
    fi
fi

# Init DB if needed
if [ ! -f "$DATA_DIR/app.db" ]; then
    echo "  Initializing database…"
    ./venv/bin/python ../scripts/init_db.py
fi

# Check port
if check_port 8765; then
    echo "  ⚠ Port 8765 already in use — backend may fail to start."
    echo "    Check:  lsof -i :8765  or  ss -tlnp | grep 8765"
fi

# Start backend — use setsid to fully detach from controlling terminal
echo "  Starting backend…"
setsid ./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8765 \
    < /dev/null > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
disown $BACKEND_PID 2>/dev/null || true
echo $BACKEND_PID > "$PID_DIR/backend.pid"
echo "  Backend PID: $BACKEND_PID"
cd "$ROOT"

# Wait for backend
READY=0
for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -s http://127.0.0.1:8765/api/health > /dev/null 2>&1; then
        echo "  ✓ Backend ready"
        READY=1
        break
    fi
    sleep 1
done
if [ $READY -eq 0 ]; then
    echo "  ✗ Backend did not become ready in 10s."
    echo "    Last log lines:"
    tail -15 "$BACKEND_LOG" | sed 's/^/    /'
    echo ""
    echo "    Full log: $BACKEND_LOG"
    exit 1
fi

# ============================================================
# Frontend
# ============================================================
echo "→ Setting up frontend (Vite on :5173)…"
cd "$ROOT/client"

if [ ! -d "node_modules" ]; then
    echo "  Installing npm dependencies (this can take a minute)…"
    if ! npm install > "$LOGS_DIR/npm-install.log" 2>&1; then
        echo ""
        echo "  ✗ npm install failed. Last log lines:"
        tail -15 "$LOGS_DIR/npm-install.log" | sed 's/^/    /'
        echo ""
        echo "  Common causes:"
        echo "    1. Node version too old (need 20+)"
        echo "       → Check:  node --version"
        echo "    2. Network/proxy issue"
        echo ""
        exit 1
    fi
fi

# Check port
if check_port 5173; then
    echo "  ⚠ Port 5173 already in use — frontend may fail to start."
fi

# Start frontend — setsid for true detachment
echo "  Starting frontend…"
setsid npm run dev < /dev/null > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
disown $FRONTEND_PID 2>/dev/null || true
echo $FRONTEND_PID > "$PID_DIR/frontend.pid"
echo "  Frontend PID: $FRONTEND_PID"
cd "$ROOT"

# Wait for frontend
READY=0
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15; do
    if curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5173 | grep -q "200"; then
        echo "  ✓ Frontend ready"
        READY=1
        break
    fi
    sleep 1
done
if [ $READY -eq 0 ]; then
    echo "  ✗ Frontend did not become ready in 15s."
    echo "    Last log lines:"
    tail -15 "$FRONTEND_LOG" | sed 's/^/    /'
    echo ""
    echo "    Full log: $FRONTEND_LOG"
    exit 1
fi

# ============================================================
# Done
# ============================================================
echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  ✓ Graph App running"
echo ""
echo "    Frontend:   http://127.0.0.1:5173"
echo "    Backend:    http://127.0.0.1:8765"
echo "    API docs:   http://127.0.0.1:8765/docs"
echo ""
echo "  PIDs:"
echo "    Backend:  $(cat $PID_DIR/backend.pid)  (saved to $PID_DIR/backend.pid)"
echo "    Frontend: $(cat $PID_DIR/frontend.pid)  (saved to $PID_DIR/frontend.pid)"
echo ""
echo "  Logs:"
echo "    tail -f $BACKEND_LOG"
echo "    tail -f $FRONTEND_LOG"
echo ""
echo "  Stop:   ./stop.sh"
echo "  Status: ./status.sh"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  Note: processes are detached (setsid) — closing the terminal"
echo "  will NOT kill them. Use ./stop.sh to stop."
echo "═══════════════════════════════════════════════════════════"
