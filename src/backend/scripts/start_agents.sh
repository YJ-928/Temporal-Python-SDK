#!/usr/bin/env bash

# Start all mock agents in the background
# Saves PIDs to runtime/pids/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

mkdir -p "$WORKSPACE_DIR/runtime/pids"

# Check if ports are already occupied
if curl -s http://localhost:11000/docs &>/dev/null && \
   curl -s http://localhost:11001/docs &>/dev/null && \
   curl -s http://localhost:11002/docs &>/dev/null; then
    echo "Mock agents are already running"
    exit 0
fi

echo "Starting Mock Agent Services..."
cd "$WORKSPACE_DIR/app/agents"

# Start Weather Agent (Port 11000)
"$WORKSPACE_DIR/../../.venv/bin/python" weather_agent.py > "$WORKSPACE_DIR/runtime/logs/agent_weather.log" 2>&1 &
WEATHER_PID=$!
echo $WEATHER_PID > "$WORKSPACE_DIR/runtime/pids/agent_weather.pid"

# Start Email Validator Agent (Port 11001)
"$WORKSPACE_DIR/../../.venv/bin/python" email_validator_agent.py > "$WORKSPACE_DIR/runtime/logs/agent_email_validator.log" 2>&1 &
VALIDATOR_PID=$!
echo $VALIDATOR_PID > "$WORKSPACE_DIR/runtime/pids/agent_email_validator.pid"

# Start Email Sender Agent (Port 11002)
"$WORKSPACE_DIR/../../.venv/bin/python" email_sender_agent.py > "$WORKSPACE_DIR/runtime/logs/agent_email_sender.log" 2>&1 &
SENDER_PID=$!
echo $SENDER_PID > "$WORKSPACE_DIR/runtime/pids/agent_email_sender.pid"

# Poll health for up to 10 seconds
for i in {1..10}; do
    WEATHER_OK=false
    VALIDATOR_OK=false
    SENDER_OK=false
    
    if curl -s http://localhost:11000/docs &>/dev/null; then WEATHER_OK=true; fi
    if curl -s http://localhost:11001/docs &>/dev/null; then VALIDATOR_OK=true; fi
    if curl -s http://localhost:11002/docs &>/dev/null; then SENDER_OK=true; fi
    
    if [ "$WEATHER_OK" = true ] && [ "$VALIDATOR_OK" = true ] && [ "$SENDER_OK" = true ]; then
        echo "All mock agents started successfully (Weather: $WEATHER_PID, Validator: $VALIDATOR_PID, Sender: $SENDER_PID)"
        exit 0
    fi
    sleep 1
done

echo "Failed to start one or more mock agents. Check log files under $WORKSPACE_DIR/runtime/logs/"
exit 1
