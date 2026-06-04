#!/usr/bin/env bash

# Start Temporal workers for backend development
# Starts 2 workers polling the same task queue

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

TASK_QUEUE="${TASK_QUEUE:-dsl-executor}"
WORKFLOW_TYPE="${WORKFLOW_TYPE:-DslWorkflow}"
WORKER_COUNT=2

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Temporal Workers - Backend${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Verify Temporal is running
echo -e "${BLUE}[1/3] Checking Temporal server...${NC}"
if ! curl -s http://localhost:7233 &>/dev/null; then
    echo -e "${RED}❌ Temporal server not reachable at localhost:7233${NC}"
    echo -e "${YELLOW}Please start Temporal first:${NC}"
    echo -e "${YELLOW}  ./start_temporal.sh${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Temporal server reachable${NC}"
echo ""

# Verify Python environment
echo -e "${BLUE}[2/3] Checking Python environment...${NC}"
if [ ! -d "../../.venv" ]; then
    echo -e "${RED}❌ Virtual environment not found at ../../.venv${NC}"
    echo -e "${YELLOW}Please create it first:${NC}"
    echo -e "${YELLOW}  cd ../.. && python3 -m venv .venv && source .venv/bin/activate${NC}"
    echo -e "${YELLOW}  pip install -r requirements.txt${NC}"
    exit 1
fi

# Activate virtual environment
source ../../.venv/bin/activate

if ! python -c "import temporalio" &>/dev/null; then
    echo -e "${RED}❌ temporalio package not installed${NC}"
    echo -e "${YELLOW}Please install dependencies:${NC}"
    echo -e "${YELLOW}  pip install -r ../../requirements.txt${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python environment ready${NC}"
echo ""

# Start workers
echo -e "${BLUE}[3/3] Starting $WORKER_COUNT workers...${NC}"
echo -e "${GREEN}Task Queue: $TASK_QUEUE${NC}"
echo -e "${GREEN}Workflow Type: $WORKFLOW_TYPE${NC}"
echo ""

# Trap Ctrl+C to gracefully shutdown all workers
trap 'echo -e "\n${YELLOW}Stopping all workers...${NC}"; kill 0; exit 0' SIGINT SIGTERM

# Worker script (inline Python)
WORKER_SCRIPT=$(cat <<'EOF'
import asyncio
import sys
import logging
from temporalio.client import Client
from temporalio.worker import Worker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def run_worker(worker_id: int, task_queue: str):
    """Run a single worker instance."""
    try:
        client = await Client.connect("localhost:7233")
        logger.info(f"Worker {worker_id} connected to Temporal")
        
        # For now, workers poll but won't execute workflows
        # This is a bootstrap script - actual workflow/activity registration
        # happens in the application layer
        
        # Placeholder worker (polls but has no workflows registered yet)
        # In production, this would import and register actual workflows/activities
        worker = Worker(
            client,
            task_queue=task_queue,
            workflows=[],  # TODO: Register workflows from app layer
            activities=[]  # TODO: Register activities from app layer
        )
        
        logger.info(f"Worker {worker_id} polling task queue: {task_queue}")
        logger.info(f"Worker {worker_id} ready (no workflows registered yet)")
        
        await worker.run()
        
    except KeyboardInterrupt:
        logger.info(f"Worker {worker_id} shutting down gracefully...")
    except Exception as e:
        logger.error(f"Worker {worker_id} error: {e}")
        raise

if __name__ == "__main__":
    worker_id = int(sys.argv[1])
    task_queue = sys.argv[2]
    
    asyncio.run(run_worker(worker_id, task_queue))
EOF
)

# Start workers in background
for i in $(seq 1 $WORKER_COUNT); do
    echo -e "${GREEN}Starting worker $i...${NC}"
    python -c "$WORKER_SCRIPT" $i "$TASK_QUEUE" &
    sleep 1
done

echo ""
echo -e "${GREEN}✓ All workers started${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop all workers${NC}"
echo ""

# Wait for all background processes
wait
