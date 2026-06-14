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
   curl -s http://localhost:11002/docs &>/dev/null && \
   curl -s http://localhost:11003/docs &>/dev/null; then
    echo "Mock agents are already running"
    exit 0
fi

echo "Starting Mock Agent Services..."
cd "$WORKSPACE_DIR/src/agent"
PYTHON="$WORKSPACE_DIR/../../.venv/bin/python"

# Start Weather Agent (Port 11000)
PYTHONPATH="$WORKSPACE_DIR" "$PYTHON" weather_agent.py > "$WORKSPACE_DIR/resources/logs/agent_weather.log" 2>&1 &
WEATHER_PID=$!
echo $WEATHER_PID > "$WORKSPACE_DIR/runtime/pids/agent_weather.pid"

# Start Email Validator Agent (Port 11001)
PYTHONPATH="$WORKSPACE_DIR" "$PYTHON" email_validator_agent.py > "$WORKSPACE_DIR/resources/logs/agent_email_validator.log" 2>&1 &
VALIDATOR_PID=$!
echo $VALIDATOR_PID > "$WORKSPACE_DIR/runtime/pids/agent_email_validator.pid"

# Start Email Sender Agent (Port 11002)
PYTHONPATH="$WORKSPACE_DIR" "$PYTHON" email_sender_agent.py > "$WORKSPACE_DIR/resources/logs/agent_email_sender.log" 2>&1 &
SENDER_PID=$!
echo $SENDER_PID > "$WORKSPACE_DIR/runtime/pids/agent_email_sender.pid"

# Start Summarizer Agent (Port 11003)
PYTHONPATH="$WORKSPACE_DIR" "$PYTHON" summarizer_agent.py > "$WORKSPACE_DIR/resources/logs/agent_summarizer.log" 2>&1 &
SUMMARIZER_PID=$!
echo $SUMMARIZER_PID > "$WORKSPACE_DIR/runtime/pids/agent_summarizer.pid"

# Poll health for up to 10 seconds
for i in {1..10}; do
    WEATHER_OK=false
    VALIDATOR_OK=false
    SENDER_OK=false
    SUMMARIZER_OK=false

    if curl -s http://localhost:11000/docs &>/dev/null; then WEATHER_OK=true; fi
    if curl -s http://localhost:11001/docs &>/dev/null; then VALIDATOR_OK=true; fi
    if curl -s http://localhost:11002/docs &>/dev/null; then SENDER_OK=true; fi
    if curl -s http://localhost:11003/docs &>/dev/null; then SUMMARIZER_OK=true; fi

    if [ "$WEATHER_OK" = true ] && [ "$VALIDATOR_OK" = true ] && [ "$SENDER_OK" = true ] && [ "$SUMMARIZER_OK" = true ]; then
        echo "All mock agents started successfully (Weather: $WEATHER_PID, Validator: $VALIDATOR_PID, Sender: $SENDER_PID, Summarizer: $SUMMARIZER_PID)"
        exit 0
    fi
    sleep 1
done

echo "Failed to start one or more mock agents. Check log files under $WORKSPACE_DIR/resources/logs/"
exit 1
