#!/usr/bin/env bash

# Start all services sequentially and verify health

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}       Initializing FlowAutomate Platform      ${NC}"
echo -e "${BLUE}==============================================${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Start Temporal
echo -e "${BLUE}[1/4] Starting Temporal Server...${NC}"
bash "$SCRIPT_DIR/scripts/start_temporal.sh"
echo ""

# 2. Start Agents
echo -e "${BLUE}[2/4] Starting Mock Agents...${NC}"
bash "$SCRIPT_DIR/scripts/start_agents.sh"
echo ""

# 3. Start Zigflow Runtime Daemon
echo -e "${BLUE}[3/4] Starting Zigflow Runtime...${NC}"
bash "$SCRIPT_DIR/scripts/start_runtime.sh"
echo ""

# 4. Start Backend
echo -e "${BLUE}[4/4] Starting FastAPI Backend...${NC}"
bash "$SCRIPT_DIR/scripts/start_backend.sh"
echo ""

# Health Checks Verification Table
echo -e "${BLUE}==============================================${NC}"
echo -e "${BLUE}             Service Health Status            ${NC}"
echo -e "${BLUE}==============================================${NC}"

HEALTHY_ALL=true

# Temporal check
if temporal operator namespace list --address localhost:7233 &>/dev/null; then
    echo -e "Temporal Server : ${GREEN}HEALTHY${NC}"
else
    echo -e "Temporal Server : ${RED}UNHEALTHY${NC}"
    HEALTHY_ALL=false
fi

# Backend check
if curl -s http://localhost:8000/health &>/dev/null; then
    echo -e "FastAPI Backend : ${GREEN}HEALTHY${NC}"
else
    echo -e "FastAPI Backend : ${RED}UNHEALTHY${NC}"
    HEALTHY_ALL=false
fi

# Agents check
if curl -s http://localhost:11000/docs &>/dev/null && \
   curl -s http://localhost:11001/docs &>/dev/null && \
   curl -s http://localhost:11002/docs &>/dev/null; then
    echo -e "Mock Agents     : ${GREEN}HEALTHY${NC}"
else
    echo -e "Mock Agents     : ${RED}UNHEALTHY${NC}"
    HEALTHY_ALL=false
fi

# Runtime check
if curl -s http://localhost:3005/health &>/dev/null; then
    echo -e "Zigflow Runtime : ${GREEN}HEALTHY${NC}"
else
    echo -e "Zigflow Runtime : ${RED}UNHEALTHY${NC}"
    HEALTHY_ALL=false
fi

echo -e "${BLUE}==============================================${NC}"

if [ "$HEALTHY_ALL" = true ]; then
    echo -e "${GREEN}✓ All services are active and ready!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some services failed to start or verify health.${NC}"
    exit 1
fi
