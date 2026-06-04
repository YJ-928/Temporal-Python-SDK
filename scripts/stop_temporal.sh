#!/usr/bin/env bash

# Stop Temporal dev server using the saved PID
# Usage: ./stop_temporal.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PID_FILE="$WORKSPACE_DIR/runtime/pids/temporal.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping Temporal dev server (PID: $PID)..."
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
            echo "Temporal didn't stop in time. Force killing..."
            kill -9 "$PID"
        fi
    else
        echo "Temporal process (PID: $PID) is not running."
    fi
    rm -f "$PID_FILE"
else
    # Fallback to general process killing if pid file is missing but it's running
    PIDS=$(pgrep -f "temporal server start-dev" || true)
    if [ ! -z "$PIDS" ]; then
        for pid in $PIDS; do
            echo "Stopping running Temporal server (PID: $pid)..."
            kill "$pid" || true
        done
    else
        echo "Temporal dev server is not running."
    fi
fi
