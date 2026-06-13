#!/usr/bin/env bash

# Start Zigflow daemon worker in the background
# Saves PID to runtime/pids/zigflow.pid

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$WORKSPACE_DIR/runtime/pids"
mkdir -p "$WORKSPACE_DIR/runtime/logs"
mkdir -p "$WORKSPACE_DIR/runtime/compiled/active"

# Count existing JSON workflows
JSON_COUNT=$(find "$WORKSPACE_DIR/runtime/compiled/active" -name "*.json" 2>/dev/null | wc -l)

if [ "$JSON_COUNT" -eq 0 ]; then
    echo "No compiled workflows found. Creating System Bootstrap Workflow..."
    cat <<EOF > "$WORKSPACE_DIR/runtime/compiled/active/bootstrap_workflow.json"
{
  "document": {
    "dsl": "1.0.0",
    "taskQueue": "system-bootstrap-queue",
    "workflowType": "system-bootstrap",
    "version": "1.0.0",
    "summary": "Hidden system bootstrap workflow to satisfy Zigflow startup check"
  },
  "do": [
    {
      "init_system": {
        "set": {
          "status": "ready"
        },
        "then": "end"
      }
    }
  ]
}
EOF
fi

# Check if Zigflow health endpoint is already responsive
if curl -s http://localhost:3005/health &>/dev/null; then
    echo "Zigflow Runtime Daemon is already running on port 3005"
    exit 0
fi

echo "Starting Zigflow Runtime Daemon..."
zigflow run \
    --dir "$WORKSPACE_DIR/runtime/compiled/active" \
    --glob "*.json" \
    --watch \
    --metrics-listen-address 127.0.0.1:9095 \
    --health-listen-address 127.0.0.1:3005 > "$WORKSPACE_DIR/runtime/logs/zigflow.log" 2>&1 &

ZIGFLOW_PID=$!
echo $ZIGFLOW_PID > "$WORKSPACE_DIR/runtime/pids/zigflow.pid"

# Poll health for up to 10 seconds
for i in {1..10}; do
    if curl -s http://localhost:3005/health &>/dev/null; then
        echo "Zigflow Runtime Daemon started successfully (PID: $ZIGFLOW_PID)"
        exit 0
    fi
    sleep 1
done

echo "Failed to start Zigflow Runtime Daemon. Check $WORKSPACE_DIR/runtime/logs/zigflow.log"
exit 1
