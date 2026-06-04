#!/usr/bin/env bash

# Start Temporal development server (local mode) for backend development
# Backend-local version of root start-temporal-dev.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Temporal Bootstrap - Backend${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if Docker is available
echo -e "${BLUE}[1/4] Checking Docker...${NC}"
if ! command -v docker &>/dev/null; then
    echo -e "${RED}❌ Docker not found.${NC}"
    echo -e "${YELLOW}Please install Docker: https://docs.docker.com/get-docker/${NC}"
    exit 1
fi

if ! docker info &>/dev/null; then
    echo -e "${RED}❌ Docker daemon not running.${NC}"
    echo -e "${YELLOW}Please start Docker and try again.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker available${NC}"
echo ""

# Check if Temporal CLI is installed
echo -e "${BLUE}[2/4] Checking Temporal CLI...${NC}"
if ! command -v temporal &>/dev/null; then
    echo -e "${YELLOW}⚠ Temporal CLI not found.${NC}"
    echo -e "${YELLOW}Install via: curl -sSf https://temporal.download/cli.sh | sh${NC}"
    echo -e "${YELLOW}Or follow: https://docs.temporal.io/cli${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Temporal CLI available ($(temporal --version))${NC}"
echo ""

# Start Temporal dev server
echo -e "${BLUE}[3/4] Starting Temporal dev server...${NC}"
echo -e "${YELLOW}This will start Temporal in the foreground.${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server.${NC}"
echo ""

# Check if Temporal is already running
if curl -s http://localhost:7233 &>/dev/null; then
    echo -e "${YELLOW}⚠ Temporal seems to be already running on port 7233${NC}"
    echo -e "${YELLOW}  If you want to restart it, stop the existing instance first.${NC}"
    echo ""
fi

echo -e "${GREEN}Starting Temporal dev server...${NC}"
echo -e "${GREEN}Web UI will be available at: http://localhost:8233${NC}"
echo -e "${GREEN}gRPC endpoint: localhost:7233${NC}"
echo ""

# Start temporal dev server with persistence to survive restarts
temporal server start-dev \
    --ui-port 8233 \
    --db-filename temporal-dev.db \
    --namespace default

# If we reach here, the server was stopped
echo ""
echo -e "${YELLOW}Temporal server stopped.${NC}"
