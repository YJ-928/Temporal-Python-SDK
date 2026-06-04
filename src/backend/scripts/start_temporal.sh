#!/usr/bin/env bash

# Start Temporal dev server in the background
# Saves PID to runtime/pids/temporal.pid

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$WORKSPACE_DIR/runtime/pids"

# Check if Temporal is already running
if temporal operator namespace list --address localhost:7233 &>/dev/null; then
    echo "Temporal is already running on port 7233"
    exit 0
fi

echo "Starting Temporal dev server..."
temporal server start-dev \
    --ui-port 8233 \
    --db-filename "$WORKSPACE_DIR/runtime/temporal-dev.db" \
    --namespace default > "$WORKSPACE_DIR/runtime/temporal.log" 2>&1 &

TEMPORAL_PID=$!
echo $TEMPORAL_PID > "$WORKSPACE_DIR/runtime/pids/temporal.pid"

# Wait for Temporal to start (up to 10 seconds)
for i in {1..10}; do
    if temporal operator namespace list --address localhost:7233 &>/dev/null; then
        echo "Temporal started successfully (PID: $TEMPORAL_PID)"
        exit 0
    fi
    sleep 1
done

echo "Failed to start Temporal dev server. Check $WORKSPACE_DIR/runtime/temporal.log"
exit 1
