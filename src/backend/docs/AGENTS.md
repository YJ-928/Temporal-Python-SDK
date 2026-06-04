# Agent Services

## Overview

Agent Services are self-contained FastAPI applications that simulate external third-party systems.

These services are used for:

* Workflow demonstrations
* Runtime validation
* Zigflow integration testing
* Temporal workflow execution testing

Each agent runs independently and exposes a REST API.

The backend treats agents as external services that may be called by workflows executed through Zigflow Runtime and Temporal.

---

# Available Agents

| Agent                 | Port  | Purpose                    |
| --------------------- | ----- | -------------------------- |
| Weather Agent         | 11000 | Weather lookup service     |
| Email Validator Agent | 11001 | Email validation service   |
| Email Sender Agent    | 11002 | Mock email sending service |

Reserved Port Range:

```text
11000 - 11099
```

This range is reserved exclusively for Agent Services.

---

# Weather Agent

## Service Information

File:

```text
app/agents/weather_agent.py
```

Port:

```text
11000
```

Endpoint:

```http
POST /execute
```

Purpose:

Provides weather information for supported cities using local JSON data.

Data Source:

```text
app/resources/agent_data/weather_data.json
```

---

## Start Service

```bash
cd src/backend
python app/agents/weather_agent.py
```

---

## Health Check

```bash
curl http://localhost:11000/
```

Response:

```json
{
  "service": "Weather Agent",
  "status": "running",
  "port": 11000,
  "endpoint": "/execute"
}
```

---

## Execute Request

```bash
curl -X POST http://localhost:11000/execute \
  -H "Content-Type: application/json" \
  -d '{"city":"hyderabad"}'
```

Response:

```json
{
  "success": true,
  "city": "Hyderabad",
  "temperature": 35,
  "condition": "Sunny"
}
```

---

## List Available Cities

```bash
curl http://localhost:11000/cities
```

---

# Email Validator Agent

## Service Information

File:

```text
app/agents/email_validator_agent.py
```

Port:

```text
11001
```

Endpoint:

```http
POST /execute
```

Purpose:

Validates email addresses using regular expression checks.

---

## Start Service

```bash
cd src/backend
python app/agents/email_validator_agent.py
```

---

## Health Check

```bash
curl http://localhost:11001/
```

Response:

```json
{
  "service": "Email Validator Agent",
  "status": "running",
  "port": 11001,
  "endpoint": "/execute"
}
```

---

## Execute Request

```bash
curl -X POST http://localhost:11001/execute \
  -H "Content-Type: application/json" \
  -d '{"email":"user@gmail.com"}'
```

Response:

```json
{
  "success": true,
  "is_valid": true,
  "domain": "gmail.com",
  "message": "Email validated successfully"
}
```

---

## Invalid Email Example

```bash
curl -X POST http://localhost:11001/execute \
  -H "Content-Type: application/json" \
  -d '{"email":"invalid-email"}'
```

Response:

```json
{
  "success": true,
  "is_valid": false,
  "domain": null,
  "message": "Invalid email format"
}
```

---

# Email Sender Agent

## Service Information

File:

```text
app/agents/email_sender_agent.py
```

Port:

```text
11002
```

Endpoint:

```http
POST /execute
```

Purpose:

Simulates email delivery and persists messages to local storage.

Storage File:

```text
app/resources/runtime_data/sent_emails.json
```

---

## Start Service

```bash
cd src/backend
python app/agents/email_sender_agent.py
```

---

## Health Check

```bash
curl http://localhost:11002/
```

Response:

```json
{
  "service": "Email Sender Agent",
  "status": "running",
  "port": 11002,
  "endpoint": "/execute"
}
```

---

## Send Email

```bash
curl -X POST http://localhost:11002/execute \
  -H "Content-Type: application/json" \
  -d '{
    "to":"user@gmail.com",
    "subject":"Welcome",
    "body":"Hello from Agent Service"
  }'
```

Response:

```json
{
  "success": true,
  "message_id": "generated-uuid"
}
```

---

## List Sent Emails

```bash
curl http://localhost:11002/sent
```

Response:

```json
{
  "sent_emails": [],
  "count": 0
}
```

---

# Development Guidelines

## Naming Convention

Agent files must follow:

```text
<service_name>_agent.py
```

Examples:

```text
weather_agent.py
stock_agent.py
currency_agent.py
```

---

## API Convention

Every agent must expose:

### Health Check

```http
GET /
```

### Main Execution Endpoint

```http
POST /execute
```

---

## Logging

All agents must use:

```python
from app.config import get_logger
```

Project logger only.

---

## Request Validation

All request and response payloads must use Pydantic models.

---

## Runtime Rules

Agents should remain:

* Stateless
* Self-contained
* Independently runnable
* Local-development friendly

Avoid:

* Direct database dependencies
* External API dependencies
* Complex infrastructure requirements

The goal is fast local execution and deterministic workflow demonstrations.

---

# Testing

## Manual Testing

Start an agent:

```bash
python app/agents/weather_agent.py
```

Test:

```bash
curl http://localhost:11000/
```

```bash
curl http://localhost:11000/cities
```

```bash
curl -X POST http://localhost:11000/execute \
  -H "Content-Type: application/json" \
  -d '{"city":"bangalore"}'
```

---

# Troubleshooting

## Port Already In Use

Check:

```bash
lsof -i :11000
```

Kill:

```bash
kill -9 <PID>
```

---

## Import Errors

Run from backend root:

```bash
cd src/backend
python app/agents/weather_agent.py
```

Or configure:

```bash
export PYTHONPATH=$(pwd)
```

---

# Future Agent Candidates

Potential additions:

* Stock Agent
* Currency Agent
* SMS Agent
* Notification Agent
* Document Processing Agent
* Search Agent

These should follow the same conventions defined in this document.

---

# Summary

Current Agent Services:

* Weather Agent
* Email Validator Agent
* Email Sender Agent

All services are:

* FastAPI based
* Independently runnable
* Accessible through HTTP
* Suitable for Zigflow Runtime testing
* Suitable for Temporal workflow demonstrations

The Agent layer exists solely to provide realistic external integrations during workflow execution and runtime validation.
