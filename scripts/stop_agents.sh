#!/usr/bin/env bash

# Stop all mock agents using saved PIDs
# Usage: ./stop_agents.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PIDS_DIR="$WORKSPACE_DIR/runtime/pids"

stop_agent() {
    local pid_file="$1"
    local name="$2"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping $name (PID: $pid)..."
            kill "$pid"
        else
            echo "$name process (PID: $pid) is not running."
        fi
        rm -f "$pid_file"
    fi
}

stop_agent "$PIDS_DIR/agent_weather.pid" "Weather Agent"
stop_agent "$PIDS_DIR/agent_email_validator.pid" "Email Validator Agent"
stop_agent "$PIDS_DIR/agent_email_sender.pid" "Email Sender Agent"

# Fallback clean up for any remaining python agents on their ports
for port in 11000 11001 11002; do
    PID=$(lsof -t -i:$port 2>/dev/null || true)
    if [ ! -z "$PID" ]; then
        echo "Killing remaining agent process on port $port (PID: $PID)..."
        kill -9 "$PID"
    fi
done
echo "All mock agents stopped."
