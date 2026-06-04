#!/usr/bin/env bash

# Start FastAPI backend in the background
# Saves PID to runtime/pids/backend.pid

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$WORKSPACE_DIR/runtime/pids"

# Check if backend is already running
if curl -s http://localhost:8000/health &>/dev/null; then
    echo "Backend is already running on port 8000"
    exit 0
fi

echo "Starting FastAPI backend..."
cd "$WORKSPACE_DIR/src/backend"
PYTHONPATH=. "$WORKSPACE_DIR/.venv/bin/python" -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 > "$WORKSPACE_DIR/runtime/backend.log" 2>&1 &

BACKEND_PID=$!
echo $BACKEND_PID > "$WORKSPACE_DIR/runtime/pids/backend.pid"

# Poll health check for up to 10 seconds
for i in {1..10}; do
    if curl -s http://localhost:8000/health &>/dev/null; then
        echo "FastAPI Backend started successfully (PID: $BACKEND_PID)"
        exit 0
    fi
    sleep 1
done

echo "Failed to start FastAPI backend. Check $WORKSPACE_DIR/runtime/backend.log"
exit 1
