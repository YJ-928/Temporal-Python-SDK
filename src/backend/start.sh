#!/bin/bash
#
# Master Bootstrap Script
# Starts entire backend stack: Temporal + Workers + Agents + FastAPI
#
# Usage: ./start.sh
# Stop: Ctrl+C (graceful shutdown of all services)
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Process tracking
TEMPORAL_PID=""
WORKERS_PID=""
AGENTS_PID=""
FASTAPI_PID=""
CLEANUP_DONE=false

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"

#==============================================================================
# Cleanup function - kills all background processes
#==============================================================================
cleanup() {
    if [ "$CLEANUP_DONE" = true ]; then
        return
    fi
    CLEANUP_DONE=true

    echo -e "\n${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Shutting down all services...${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Kill FastAPI
    if [ -n "$FASTAPI_PID" ]; then
        echo -e "${YELLOW}Stopping FastAPI (PID: $FASTAPI_PID)...${NC}"
        kill "$FASTAPI_PID" 2>/dev/null || true
        wait "$FASTAPI_PID" 2>/dev/null || true
        echo -e "${GREEN}✓ FastAPI stopped${NC}"
    fi

    # Kill agents
    if [ -n "$AGENTS_PID" ]; then
        echo -e "${YELLOW}Stopping agents...${NC}"
        kill "$AGENTS_PID" 2>/dev/null || true
        # Kill all agent processes (ports 11000-11002)
        pkill -f "python.*agent.*11000" 2>/dev/null || true
        pkill -f "python.*agent.*11001" 2>/dev/null || true
        pkill -f "python.*agent.*11002" 2>/dev/null || true
        echo -e "${GREEN}✓ Agents stopped${NC}"
    fi

    # Kill workers
    if [ -n "$WORKERS_PID" ]; then
        echo -e "${YELLOW}Stopping workers...${NC}"
        kill "$WORKERS_PID" 2>/dev/null || true
        # Kill all worker processes
        pkill -f "python.*worker.*dsl-executor" 2>/dev/null || true
        pkill -f "zigflow run" 2>/dev/null || true
        echo -e "${GREEN}✓ Workers stopped${NC}"
    fi

    # Kill Temporal
    if [ -n "$TEMPORAL_PID" ]; then
        echo -e "${YELLOW}Stopping Temporal...${NC}"
        kill "$TEMPORAL_PID" 2>/dev/null || true
        wait "$TEMPORAL_PID" 2>/dev/null || true
        echo -e "${GREEN}✓ Temporal stopped${NC}"
    fi

    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}All services stopped successfully${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
}

# Trap Ctrl+C and script exit
trap cleanup SIGINT SIGTERM EXIT

#==============================================================================
# Header
#==============================================================================
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}           Temporal Python SDK - Backend Stack Startup${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

#==============================================================================
# Step 1: Verify Docker
#==============================================================================
echo -e "${BLUE}[1/8] Verifying Docker...${NC}"
if ! command -v docker &>/dev/null; then
    echo -e "${RED}❌ Docker not found${NC}"
    echo -e "${YELLOW}Please install Docker: https://docs.docker.com/get-docker/${NC}"
    exit 1
fi

if ! docker info &>/dev/null; then
    echo -e "${RED}❌ Docker daemon not running${NC}"
    echo -e "${YELLOW}Please start Docker Desktop${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker running${NC}"
echo ""

#==============================================================================
# Step 2: Verify Temporal CLI
#==============================================================================
echo -e "${BLUE}[2/8] Verifying Temporal CLI...${NC}"
if ! command -v temporal &>/dev/null; then
    echo -e "${RED}❌ Temporal CLI not found${NC}"
    echo -e "${YELLOW}Install: brew install temporal (macOS) or see https://docs.temporal.io/cli${NC}"
    exit 1
fi

TEMPORAL_VERSION=$(temporal --version 2>&1 | head -n1 || echo "unknown")
echo -e "${GREEN}✓ Temporal CLI available ($TEMPORAL_VERSION)${NC}"
echo ""

#==============================================================================
# Step 3: Verify Python Virtual Environment
#==============================================================================
echo -e "${BLUE}[3/8] Verifying Python virtual environment...${NC}"
VENV_PATH="$SCRIPT_DIR/../../.venv"

if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}❌ Virtual environment not found at $VENV_PATH${NC}"
    echo -e "${YELLOW}Run: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt${NC}"
    exit 1
fi

if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo -e "${RED}❌ Virtual environment activation script missing${NC}"
    exit 1
fi

# Activate venv
source "$VENV_PATH/bin/activate"
echo -e "${GREEN}✓ Python virtual environment activated${NC}"
echo ""

#==============================================================================
# Step 4: Start Temporal Server
#==============================================================================
echo -e "${BLUE}[4/8] Starting Temporal Server...${NC}"

# Check if Temporal is already running
if temporal namespace list &>/dev/null; then
    echo -e "${GREEN}✓ Temporal already running${NC}"
else
    # Start Temporal in background using our script
    cd "$SCRIPT_DIR"
    bash "$SCRIPTS_DIR/start_temporal.sh" &>/dev/null &
    TEMPORAL_PID=$!

    echo -e "${YELLOW}Waiting for Temporal to start...${NC}"

    # Wait up to 30 seconds for Temporal to be ready
    for i in {1..30}; do
        if temporal namespace list &>/dev/null; then
            echo -e "${GREEN}✓ Temporal Server running (PID: $TEMPORAL_PID)${NC}"
            echo -e "${GREEN}  Web UI: http://localhost:8233${NC}"
            break
        fi

        # Check if process died
        if ! kill -0 "$TEMPORAL_PID" 2>/dev/null; then
            echo -e "${RED}❌ Temporal failed to start${NC}"
            exit 1
        fi

        sleep 1
    done

    # Final check
    if ! temporal namespace list &>/dev/null; then
        echo -e "${RED}❌ Temporal not responding after 30 seconds${NC}"
        exit 1
    fi
fi
echo ""

#==============================================================================
# Step 5: Start Workers
#==============================================================================
echo -e "${BLUE}[5/8] Starting Temporal Workers...${NC}"

# Export required env vars for workers
export TASK_QUEUE="${TASK_QUEUE:-workflow-builder}"
export WORKFLOW_TYPE="${WORKFLOW_TYPE:-DslWorkflow}"

# Create compiled directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/resources/compiled"

# Start zigflow run daemon watching the compiled directory
zigflow run --dir "$SCRIPT_DIR/resources/compiled" --watch --metrics-listen-address "127.0.0.1:9095" --health-listen-address "127.0.0.1:3005" &>/dev/null &
WORKERS_PID=$!

# Give workers time to initialize
sleep 2

if kill -0 "$WORKERS_PID" 2>/dev/null; then
    echo -e "${GREEN}✓ Zigflow worker daemon running (PID: $WORKERS_PID)${NC}"
    echo -e "${GREEN}  Watching directory: $SCRIPT_DIR/resources/compiled${NC}"
else
    echo -e "${RED}❌ Zigflow worker daemon failed to start${NC}"
    exit 1
fi
echo ""

#==============================================================================
# Step 6: Start Agent Services
#==============================================================================
echo -e "${BLUE}[6/8] Starting Agent Services...${NC}"

bash "$SCRIPTS_DIR/start_agents.sh" &>/dev/null &
AGENTS_PID=$!

# Wait for agents to be ready
echo -e "${YELLOW}Waiting for agents to start...${NC}"
sleep 3

# Verify all 3 agents
AGENTS_OK=true
for port in 11000 11001 11002; do
    if ! curl -s http://localhost:$port/docs &>/dev/null; then
        echo -e "${RED}❌ Agent on port $port not responding${NC}"
        AGENTS_OK=false
    fi
done

if [ "$AGENTS_OK" = true ]; then
    echo -e "${GREEN}✓ All agents running (PID: $AGENTS_PID)${NC}"
    echo -e "${GREEN}  Weather Agent: http://localhost:11000${NC}"
    echo -e "${GREEN}  Email Validator: http://localhost:11001${NC}"
    echo -e "${GREEN}  Email Sender: http://localhost:11002${NC}"
else
    echo -e "${RED}❌ One or more agents failed to start${NC}"
    exit 1
fi
echo ""

#==============================================================================
# Step 7: Start FastAPI Backend
#==============================================================================
echo -e "${BLUE}[7/8] Starting FastAPI Backend...${NC}"

cd "$SCRIPT_DIR"
PYTHONPATH=. python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &>/dev/null &
FASTAPI_PID=$!

# Wait for FastAPI to be ready
echo -e "${YELLOW}Waiting for FastAPI to start...${NC}"
sleep 2

if curl -s http://localhost:8000/docs &>/dev/null; then
    echo -e "${GREEN}✓ FastAPI running (PID: $FASTAPI_PID)${NC}"
    echo -e "${GREEN}  API Docs: http://localhost:8000/docs${NC}"
else
    echo -e "${RED}❌ FastAPI not responding${NC}"
    exit 1
fi
echo ""

#==============================================================================
# Step 8: System Ready
#==============================================================================
echo -e "${BLUE}[8/8] Verifying System Health...${NC}"

# Final health checks
ALL_OK=true

if ! curl -s http://localhost:8233 &>/dev/null; then
    echo -e "${RED}❌ Temporal Web UI unreachable${NC}"
    ALL_OK=false
fi

if ! curl -s http://localhost:8000/docs &>/dev/null; then
    echo -e "${RED}❌ FastAPI unreachable${NC}"
    ALL_OK=false
fi

if [ "$ALL_OK" = true ]; then
    echo -e "${GREEN}✓ All services healthy${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}                         🚀 SYSTEM READY 🚀${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${CYAN}📊 Service URLs:${NC}"
echo ""
echo -e "${YELLOW}Temporal Web UI:${NC}"
echo -e "  http://localhost:8233"
echo ""
echo -e "${YELLOW}FastAPI (Compiler API):${NC}"
echo -e "  http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}Agent Services:${NC}"
echo -e "  Weather Agent:         http://localhost:11000/docs"
echo -e "  Email Validator Agent: http://localhost:11001/docs"
echo -e "  Email Sender Agent:    http://localhost:11002/docs"
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

#==============================================================================
# Keep running and wait for Ctrl+C
#==============================================================================
while true; do
    sleep 1

    # Periodic health check (every 10 seconds)
    if [ $((SECONDS % 10)) -eq 0 ]; then
        # Check if any critical process died
        if ! kill -0 "$FASTAPI_PID" 2>/dev/null; then
            echo -e "${RED}❌ FastAPI died unexpectedly${NC}"
            cleanup
        fi

        if ! kill -0 "$AGENTS_PID" 2>/dev/null; then
            echo -e "${RED}❌ Agents died unexpectedly${NC}"
            cleanup
        fi
    fi
done
