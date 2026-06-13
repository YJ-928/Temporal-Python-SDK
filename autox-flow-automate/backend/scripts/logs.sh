#!/usr/bin/env bash
# Stream all service logs in real time with color-coded prefixes.
# Usage:
#   ./scripts/logs.sh               — last 20 lines + live stream (all services)
#   ./scripts/logs.sh --lines 50    — last 50 lines + live stream
#   ./scripts/logs.sh --service backend   — backend only
#   ./scripts/logs.sh --service zigflow   — zigflow only
#   ./scripts/logs.sh --service agents    — all three agents

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$(cd "$SCRIPT_DIR/.." && pwd)/resources/logs"

LINES=20
SERVICE="all"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --lines) LINES="$2"; shift 2 ;;
        --service) SERVICE="$2"; shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
GRAY='\033[0;37m'
NC='\033[0m'

PIDS=()

cleanup() {
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null || true
    done
    echo ""
    echo "Log viewer stopped."
    exit 0
}

trap cleanup INT TERM

follow() {
    local color="$1"
    local label="$2"
    local file="$3"
    if [[ -f "$file" ]]; then
        tail -n "$LINES" -f "$file" 2>/dev/null | while IFS= read -r line; do
            printf "${color}[%-18s]${NC} %s\n" "$label" "$line"
        done &
        PIDS+=($!)
    else
        printf "${YELLOW}[%-18s]${NC} log file not found — service may not have started yet\n" "$label"
    fi
}

echo -e "${BLUE}=================================================${NC}"
echo -e "${BLUE}   Workflow Platform — Live Log Viewer           ${NC}"
echo -e "${BLUE}   Showing last ${LINES} lines + live stream         ${NC}"
echo -e "${BLUE}   Press Ctrl+C to stop                          ${NC}"
echo -e "${BLUE}=================================================${NC}"
echo ""

case "$SERVICE" in
    backend)
        follow "$BLUE"    "backend"         "$LOG_DIR/backend.log"
        ;;
    zigflow)
        follow "$GREEN"   "zigflow"         "$LOG_DIR/zigflow.log"
        ;;
    agents)
        follow "$CYAN"    "agent:weather"   "$LOG_DIR/agent_weather.log"
        follow "$YELLOW"  "agent:validator" "$LOG_DIR/agent_email_validator.log"
        follow "$MAGENTA" "agent:sender"    "$LOG_DIR/agent_email_sender.log"
        ;;
    all)
        follow "$BLUE"    "backend"         "$LOG_DIR/backend.log"
        follow "$GREEN"   "zigflow"         "$LOG_DIR/zigflow.log"
        follow "$CYAN"    "agent:weather"   "$LOG_DIR/agent_weather.log"
        follow "$YELLOW"  "agent:validator" "$LOG_DIR/agent_email_validator.log"
        follow "$MAGENTA" "agent:sender"    "$LOG_DIR/agent_email_sender.log"
        ;;
    *)
        echo "Unknown service: $SERVICE. Use: backend | zigflow | agents | all"
        exit 1
        ;;
esac

wait
