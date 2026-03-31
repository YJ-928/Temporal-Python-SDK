# Temporal Deployment

## Overview

Deploying Temporal involves running the **Temporal Cluster** (server) and deploying your **Workers**. The cluster manages orchestration; Workers execute your code.

## Deployment Architecture

```
┌─────────────────────────────────────────────┐
│              Production Environment          │
│                                             │
│  ┌──────────────┐    ┌──────────────────┐  │
│  │ Temporal      │    │  Database        │  │
│  │ Cluster       │◄──►│  (PostgreSQL/    │  │
│  │ (Server)      │    │   Cassandra)     │  │
│  └──────┬───────┘    └──────────────────┘  │
│         │                                   │
│    ┌────┴────┐                              │
│    │         │                              │
│  ┌─▼──┐  ┌──▼─┐                            │
│  │W1  │  │W2  │  ... (Worker fleet)        │
│  └────┘  └────┘                            │
└─────────────────────────────────────────────┘
```

## Deployment Options

### 1. Local Development

```bash
temporal server start-dev
```

Runs an in-memory server — no external database needed.

### 2. Self-Hosted (Docker)

```yaml
# docker-compose.yml (simplified)
services:
  temporal:
    image: temporalio/auto-setup:latest
    ports:
      - "7233:7233"
    depends_on:
      - postgresql
  temporal-ui:
    image: temporalio/ui:latest
    ports:
      - "8233:8080"
  postgresql:
    image: postgres:15
```

### 3. Temporal Cloud

Temporal Cloud is a managed service that handles the cluster for you:

```python
from temporalio.client import Client, TLSConfig

client = await Client.connect(
    "your-namespace.tmprl.cloud:7233",
    namespace="your-namespace",
    tls=TLSConfig(
        client_cert=cert_bytes,
        client_private_key=key_bytes,
    ),
)
```

## Deploying Workers

Workers are your standard application processes. Deploy them like any Python service:

```bash
# Using systemd, Docker, Kubernetes, etc.
python worker.py
```

### Worker Scaling

- Run **multiple Worker instances** for high availability
- Workers on the same Task Queue share the workload
- Scale horizontally by adding more Worker processes

### Health Checks

Workers maintain a gRPC connection to the cluster. Monitor:
- Connection status
- Task processing rate
- Error rate

## Database Backends

| Database | Use Case |
|----------|----------|
| SQLite (dev server) | Local development only |
| PostgreSQL | Production (most common) |
| MySQL | Production alternative |
| Cassandra | High-scale production |

## Best Practices

- Use Temporal Cloud or a managed database for production
- Run at least 2 Worker instances per Task Queue
- Use health checks and monitoring
- Deploy Workers close to the Temporal Cluster for low latency
- Use namespaces to separate environments (dev, staging, prod)
- Version your Workflow and Activity code carefully during deployments

## Exercise

1. Start the dev server with `temporal server start-dev`
2. Start two Workers on the same Task Queue
3. Run a Workflow and observe which Worker executes it
