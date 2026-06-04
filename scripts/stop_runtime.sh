#!/usr/bin/env bash

# Stop Zigflow Runtime Daemon using saved PID
# Usage: ./stop_runtime.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PID_FILE="$WORKSPACE_DIR/runtime/pids/zigflow.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping Zigflow Runtime Daemon (PID: $PID)..."
        kill "$PID"
        
        # Wait up to 5 seconds
        for i in {1..5}; do
            if ! kill -0 "$PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done
        
        if kill -0 "$PID" 2>/dev/null; then
            echo "Zigflow Daemon didn't stop in time. Force killing..."
            kill -9 "$PID"
        fi
    else
        echo "Zigflow Daemon process (PID: $PID) is not running."
    fi
    rm -f "$PID_FILE"
else
    # Fallback to general process killing
    PID=$(pgrep -f "zigflow run" || true)
    if [ ! -z "$PID" ]; then
        echo "Stopping running Zigflow Daemon (PID: $PID)..."
        kill "$PID"
    else
        echo "Zigflow Runtime Daemon is not running."
    fi
fi

# Fallback check on port 3005 and 9095
for port in 3005 9095; do
    PID=$(lsof -t -i:$port 2>/dev/null || true)
    if [ ! -z "$PID" ]; then
        echo "Killing remaining process on port $port (PID: $PID)..."
        kill -9 "$PID"
    fi
done
echo "Zigflow Runtime Daemon stopped."
