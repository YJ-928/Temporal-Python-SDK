FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy project files
COPY pyproject.toml uv.lock ./
COPY app/ app/
COPY resources/ resources/
COPY scripts/ scripts/
COPY start.sh stop.sh ./

# Sync dependencies
RUN uv sync --frozen

# Create runtime directories
RUN mkdir -p runtime/compiled runtime/logs runtime/pids

EXPOSE 8000

ENV PYTHONPATH=/app
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
