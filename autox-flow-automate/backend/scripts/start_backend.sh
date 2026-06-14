#!/usr/bin/env bash

# Start FastAPI backend in the background.
# Host/port are read from .env (API_HOST, API_PORT).
# Saves PID to runtime/pids/backend.pid

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Read only the two variables the script needs from .env.
# We avoid "set -a; source .env" because bash strips inner quotes from values like
# CORS_ORIGINS=["*"], turning them into [*] which is invalid JSON and causes
# pydantic_settings to crash. Pydantic_settings reads .env itself for all other vars.
if [ -f "$WORKSPACE_DIR/.env" ]; then
    API_HOST=$(grep -E "^API_HOST=" "$WORKSPACE_DIR/.env" | head -1 | cut -d'=' -f2- | tr -d '"')
    API_PORT=$(grep -E "^API_PORT=" "$WORKSPACE_DIR/.env" | head -1 | cut -d'=' -f2- | tr -d '"')
fi

# Defaults mirror settings.py so the script works even without .env
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"

mkdir -p "$WORKSPACE_DIR/runtime/pids"
mkdir -p "$WORKSPACE_DIR/resources/logs"

# Check if backend is already running
if curl -s "http://localhost:${API_PORT}/health" &>/dev/null; then
    echo "Backend is already running on port ${API_PORT}"
    exit 0
fi

echo "Starting FastAPI backend..."
cd "$WORKSPACE_DIR"
PYTHONPATH=. "$WORKSPACE_DIR/../../.venv/bin/python" -m uvicorn src.main:app \
    --host "${API_HOST}" \
    --port "${API_PORT}" > "$WORKSPACE_DIR/resources/logs/backend.log" 2>&1 &

BACKEND_PID=$!
echo $BACKEND_PID > "$WORKSPACE_DIR/runtime/pids/backend.pid"

# Poll health check for up to 10 seconds
for i in {1..10}; do
    if curl -s "http://localhost:${API_PORT}/health" &>/dev/null; then
        echo "FastAPI Backend started successfully (PID: $BACKEND_PID)"
        exit 0
    fi
    sleep 1
done

echo "Failed to start FastAPI backend. Check $WORKSPACE_DIR/resources/logs/backend.log"
exit 1
