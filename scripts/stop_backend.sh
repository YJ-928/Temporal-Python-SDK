#!/usr/bin/env bash

# Stop FastAPI backend using the saved PID
# Usage: ./stop_backend.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PID_FILE="$WORKSPACE_DIR/runtime/pids/backend.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping FastAPI backend (PID: $PID)..."
        kill "$PID"
        
        # Wait up to 5 seconds for it to exit
        for i in {1..5}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if kill -0 "$PID" 2>/dev/null; then
            echo "Backend didn't stop in time. Force killing..."
            kill -9 "$PID"
        fi
    else
        echo "Backend process (PID: $PID) is not running."
    fi
    rm -f "$PID_FILE"
    # Fallback to general process killing
    PIDS=$(pgrep -f "app.main:app" || true)
    if [ ! -z "$PIDS" ]; then
        for pid in $PIDS; do
            echo "Stopping running FastAPI backend (PID: $pid)..."
            kill "$pid" || true
        done
    fi

    # Foolproof check on port 8000
    PORT_PIDS=$(lsof -t -i:8000 2>/dev/null || true)
    if [ ! -z "$PORT_PIDS" ]; then
        for pid in $PORT_PIDS; do
            echo "Killing remaining process on port 8000 (PID: $pid)..."
            kill -9 "$pid" || true
        done
    fi
    echo "FastAPI backend stopped."
fi
