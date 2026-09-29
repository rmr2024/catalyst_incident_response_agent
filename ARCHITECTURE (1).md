# Architecture

## Overview

The Incident Response Agent is a memory-driven AI workflow composed of
five major layers:

1.  Presentation
2.  Backend orchestration
3.  Agent reasoning
4.  Long-term memory
5.  Simulated operational tools

``` text
User
 |
 v
Streamlit Frontend
 |
 | HTTP / SSE
 v
FastAPI Backend
 |
 +----------------------+
 |                      |
 v                      v
SQLite               Agent Layer
 |                      |
 |              +-------+-------+
 |              |       |       |
 |              v       v       v
 |          Hindsight  LLM    Tools
 |              |       |       |
 +--------------+-------+-------+
                |
                v
          Incident Result
```

## Components

### Frontend

Technology:

-   Streamlit (Python)
-   Streamlit Multipage Architecture (`pages/` directory)
-   Custom CSS & Streamlit components
-   Altair / Plotly where analytics and charts are implemented
-   httpx / requests client for FastAPI communication

Primary screens:

-   Dashboard (`1_Dashboard.py`)
-   Simulator (`2_Simulator.py`)
-   War Room (`3_War_Room.py`)
-   Post-Mortem (`4_Postmortem.py`)
-   Analytics (`5_Analytics.py`)

The frontend is responsible for presentation and user interaction. It
should not contain incident investigation logic.

### FastAPI Backend

The backend coordinates the workflow.

Responsibilities:

-   API routing
-   request validation
-   incident creation
-   severity classification
-   database persistence
-   agent invocation
-   memory calls
-   action approval
-   simulation
-   event streaming
-   post-mortem generation

### SQLite

SQLite is the application state store.

It can contain:

-   incidents
-   incident events
-   action requests
-   approvals
-   runbooks
-   current status
-   simulation results

SQLite is not the long-term AI memory.

### Hindsight

Hindsight is the long-term memory system.

Memory records should contain enough context to make historical
knowledge useful.

Example memory:

``` text
Incident ID: INC-104
Service: payment-api
Symptoms: connection pool exhausted, HTTP 503 spike
Root cause: database connection pool saturation
Resolution: increased pool size and restarted affected service
Runbook: DB-POOL-RECOVERY
Outcome: worked
Lessons: verify connection usage before repeated restarts
```

### LLM Layer

The LLM receives:

-   current incident
-   current logs and metrics
-   recalled memories
-   tool results

It produces structured output.

The LLM should not invent historical evidence. Historical claims must be
grounded in recalled incidents.

### Tool Layer

Tools are simple Python functions.

Examples:

``` text
get_logs(service)
get_metrics(service)
get_recent_deploys(service)
simulate_restart(service)
simulate_rollback(service)
verify_resolution(incident_id)
```

Actions that can affect system state should expose:

``` text
needs_approval = true
```

The hackathon implementation executes them only against simulated
infrastructure.

## Investigation Pipeline

``` text
POST /alerts
     |
     v
Normalize Alert
     |
     v
Classify Severity
     |
     v
Create Incident in SQLite
     |
     v
Gather Context
     |
     v
Hindsight Recall
     |
     v
Agent Reasoning
     |
     +----> Similar Incidents
     |
     +----> Root Cause
     |
     +----> Evidence
     |
     +----> Runbook
     |
     +----> Successful Fixes
     |
     +----> Failed Fixes
     |
     v
Recommendation
     |
     v
Human Approval
     |
     v
Simulated Tool Execution
     |
     v
Verification
     |
     v
Post-Mortem
     |
     v
Hindsight Retain
```

## Realtime Events

Server-Sent Events can stream events to the War Room.

Example event sequence:

``` text
alert_received
incident_created
severity_classified
context_collected
memory_recall_started
memory_recall_completed
investigation_started
hypothesis_generated
recommendation_created
approval_requested
action_approved
action_executed
resolution_verified
postmortem_generated
memory_retained
```

The UI can render these events as a live timeline.

## Memory ON/OFF

The backend should expose a memory-enabled flag.

When memory is enabled:

``` text
current context
     +
Hindsight recall
     |
     v
LLM
```

When memory is disabled:

``` text
current context
     |
     v
LLM
```

This allows the demo to compare generic reasoning with memory-grounded
reasoning.

## Data Boundaries

``` text
SQLite
  |
  +-- application state
  +-- current workflow
  +-- audit events
  +-- approvals

Hindsight
  |
  +-- historical knowledge
  +-- incident memories
  +-- outcomes
  +-- lessons
  +-- approved post-mortems
```

Keeping these responsibilities separate prevents the application
database from becoming a replacement for Hindsight.

## Security Model

For the hackathon:

-   never expose production credentials
-   keep API keys in environment variables
-   simulate remediation actions
-   require approval for risky actions
-   record approvals and outcomes
-   never store secrets in incident memory

## Deployment

A local Docker Compose setup may contain:

``` text
frontend (Streamlit, port 8501)
backend (FastAPI, port 8000)
hindsight
```

SQLite can remain local to the backend for the hackathon.

The project should also support running frontend (`streamlit run frontend/app.py`) and backend (`uvicorn backend.main:app`) separately
during development.
