#!/usr/bin/env bash

# Start all agent services for backend development
# Agents: Weather (11000), Email Validator (11001), Email Sender (11002)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Agent Services - Backend${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Verify Python environment
echo -e "${BLUE}[1/4] Checking Python environment...${NC}"
if [ ! -d "../../.venv" ]; then
    echo -e "${RED}❌ Virtual environment not found at ../../.venv${NC}"
    echo -e "${YELLOW}Please create it first:${NC}"
    echo -e "${YELLOW}  cd ../.. && python3 -m venv .venv && source .venv/bin/activate${NC}"
    echo -e "${YELLOW}  pip install -r requirements.txt${NC}"
    exit 1
fi

# Activate virtual environment
source ../../.venv/bin/activate

if ! python -c "import fastapi, uvicorn" &>/dev/null; then
    echo -e "${RED}❌ fastapi/uvicorn not installed${NC}"
    echo -e "${YELLOW}Please install dependencies:${NC}"
    echo -e "${YELLOW}  pip install -r ../../requirements.txt${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python environment ready${NC}"
echo ""

# Verify agent files exist
echo -e "${BLUE}[2/4] Verifying agent files...${NC}"
if [ ! -f "app/agents/weather_agent.py" ]; then
    echo -e "${RED}❌ app/agents/weather_agent.py not found${NC}"
    exit 1
fi
if [ ! -f "app/agents/email_validator_agent.py" ]; then
    echo -e "${RED}❌ app/agents/email_validator_agent.py not found${NC}"
    exit 1
fi
if [ ! -f "app/agents/email_sender_agent.py" ]; then
    echo -e "${RED}❌ app/agents/email_sender_agent.py not found${NC}"
    exit 1
fi

echo -e "${GREEN}✓ All agent files present${NC}"
echo ""

# Trap Ctrl+C to gracefully shutdown all agents
trap 'echo -e "\n${YELLOW}Stopping all agents...${NC}"; kill 0; exit 0' SIGINT SIGTERM

# Start agents
echo -e "${BLUE}[3/4] Starting agent services...${NC}"
echo ""

echo -e "${GREEN}Starting Weather Agent on port 11000...${NC}"
cd app/agents && python weather_agent.py &
WEATHER_PID=$!
sleep 2

echo -e "${GREEN}Starting Email Validator Agent on port 11001...${NC}"
python email_validator_agent.py &
VALIDATOR_PID=$!
sleep 2

echo -e "${GREEN}Starting Email Sender Agent on port 11002...${NC}"
python email_sender_agent.py &
SENDER_PID=$!
sleep 2

cd ../..

echo ""
echo -e "${BLUE}[4/4] Verifying agent ports...${NC}"

# Verify ports are active
WEATHER_OK=false
VALIDATOR_OK=false
SENDER_OK=false

if curl -s http://localhost:11000/docs &>/dev/null; then
    echo -e "${GREEN}✓ Weather Agent active on port 11000${NC}"
    WEATHER_OK=true
else
    echo -e "${RED}❌ Weather Agent not reachable on port 11000${NC}"
fi

if curl -s http://localhost:11001/docs &>/dev/null; then
    echo -e "${GREEN}✓ Email Validator Agent active on port 11001${NC}"
    VALIDATOR_OK=true
else
    echo -e "${RED}❌ Email Validator Agent not reachable on port 11001${NC}"
fi

if curl -s http://localhost:11002/docs &>/dev/null; then
    echo -e "${GREEN}✓ Email Sender Agent active on port 11002${NC}"
    SENDER_OK=true
else
    echo -e "${RED}❌ Email Sender Agent not reachable on port 11002${NC}"
fi

echo ""

if [ "$WEATHER_OK" = true ] && [ "$VALIDATOR_OK" = true ] && [ "$SENDER_OK" = true ]; then
    echo -e "${GREEN}✓ All agents started successfully${NC}"
    echo ""
    echo -e "${BLUE}Agent Endpoints:${NC}"
    echo -e "  ${GREEN}Weather Agent:         http://localhost:11000${NC}"
    echo -e "  ${GREEN}Email Validator Agent: http://localhost:11001${NC}"
    echo -e "  ${GREEN}Email Sender Agent:    http://localhost:11002${NC}"
    echo ""
    echo -e "${BLUE}API Documentation:${NC}"
    echo -e "  ${GREEN}Weather Agent:         http://localhost:11000/docs${NC}"
    echo -e "  ${GREEN}Email Validator Agent: http://localhost:11001/docs${NC}"
    echo -e "  ${GREEN}Email Sender Agent:    http://localhost:11002/docs${NC}"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C to stop all agents${NC}"
    echo ""
else
    echo -e "${RED}❌ Some agents failed to start${NC}"
    echo -e "${YELLOW}Check the terminal output above for errors${NC}"
    kill 0
    exit 1
fi

# Wait for all background processes
wait
