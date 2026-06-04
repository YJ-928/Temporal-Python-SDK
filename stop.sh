#!/usr/bin/env bash

# Stop all services sequentially in reverse order

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}        Shutting Down Workflow Platform       ${NC}"
echo -e "${BLUE}==============================================${NC}"
echo ""

# 1. Stop Zigflow Runtime Daemon
echo -e "${BLUE}[1/4] Stopping Zigflow Runtime...${NC}"
bash scripts/stop_runtime.sh
echo ""

# 2. Stop Agents
echo -e "${BLUE}[2/4] Stopping Mock Agents...${NC}"
bash scripts/stop_agents.sh
echo ""

# 3. Stop Backend
echo -e "${BLUE}[3/4] Stopping FastAPI Backend...${NC}"
bash scripts/stop_backend.sh
echo ""

# 4. Stop Temporal
echo -e "${BLUE}[4/4] Stopping Temporal Server...${NC}"
bash scripts/stop_temporal.sh
echo ""

echo -e "${BLUE}==============================================${NC}"
echo -e "${GREEN}✓ All services successfully shut down.${NC}"
echo -e "${BLUE}==============================================${NC}"
exit 0
