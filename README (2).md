# Incident Response Agent

An AI-powered incident response system that uses long-term operational
memory to investigate production incidents, retrieve relevant historical
incidents, recommend proven remediation steps, and learn from resolved
incidents.

The system is designed around one central idea:

> An incident response agent should not investigate every outage from
> scratch. It should remember what happened before, what worked, what
> failed, and what engineers learned.

## Problem

During production incidents, engineers often spend valuable time
searching through previous incidents, runbooks, logs, post-mortems, and
team knowledge.

A conventional LLM can reason about the current incident, but without
persistent organizational memory it may not know:

-   whether a similar incident happened before
-   what the root cause was
-   which remediation steps actually worked
-   which attempted fixes failed
-   which runbook was effective
-   what lessons were learned after the incident

This project addresses that gap by combining an LLM-based investigation
workflow with Hindsight long-term memory.

## Solution

The Incident Response Agent follows a memory-driven response loop:

``` text
New Alert
   |
   v
Incident Normalization
   |
   v
Severity Classification
   |
   v
Retrieve Historical Memory
   |
   v
Similar Incident Detection
   |
   v
AI Investigation
   |
   +--> Root Cause Hypotheses
   |
   +--> Evidence
   |
   +--> Proven Runbook
   |
   +--> Successful / Failed Fixes
   |
   v
Human Approval
   |
   v
Simulated Remediation
   |
   v
Resolution Verification
   |
   v
Post-Mortem Generation
   |
   v
Engineer Approval
   |
   v
Store New Knowledge in Hindsight
```

## Key Idea: Memory-Driven Incident Response

Hindsight is used as the long-term memory layer.

### Retain

Stores useful operational knowledge:

-   incident symptoms
-   services
-   errors
-   root causes
-   runbooks
-   remediation steps
-   successful outcomes
-   failed outcomes
-   lessons learned
-   approved post-mortems

### Recall

Retrieves relevant historical memories for a new incident.

### Reflect

Used where useful to reason over recalled memories and derive
higher-level operational insights.

The application database and Hindsight have different responsibilities:

  -----------------------------------------------------------------------
  System                              Responsibility
  ----------------------------------- -----------------------------------
  SQLite                              Current application state,
                                      incidents, events, approvals,
                                      status

  Hindsight                           Long-term operational memory

  LLM                                 Investigation, reasoning,
                                      structured recommendations

  FastAPI                             Backend orchestration

  React                               Dashboard and incident workflow
  -----------------------------------------------------------------------

## Features

### Tier 1 --- Demo Core

1.  Incident memory and seed data
2.  Alert ingestion
3.  Severity classification
4.  Similar incident detection
5.  Root-cause prediction with evidence
6.  Intelligent runbook recommendation
7.  Successful and failed fix memory
8.  Human-in-the-loop approval
9.  Timeline and audit log
10. Automatic post-mortem generation
11. Post-mortem learning loop
12. Incident dashboard
13. Simulation mode
14. Memory ON/OFF comparison
15. Visible Hindsight memory calls

### Optional Tier 2

If the core workflow is stable, the following can be added:

-   Conversational incident assistant
-   MTTR and incident analytics
-   Novel incident detection
-   Smart contextual alerts

The six-hour implementation prioritizes the Tier 1 workflow over
optional features.

## Technology Stack

  -----------------------------------------------------------------------
  Layer                   Technology              Purpose
  ----------------------- ----------------------- -----------------------
  Frontend                React + Vite +          Incident dashboard and
                          TypeScript              workflow UI

  Styling                 Tailwind CSS            Rapid interface
                                                  development

  Backend                 Python + FastAPI        API and orchestration

  Validation              Pydantic                Structured
                                                  request/response models

  LLM                     Claude API through an   Investigation and
                          `llm.py` wrapper        generation

  Memory                  Hindsight               Long-term incident
                                                  memory

  Application DB          SQLite + SQLModel       Application state only

  Realtime                Server-Sent Events      Live incident timeline
                          (SSE)                   

  HTTP                    httpx                   Direct HTTP
                                                  integrations

  Demo data               JSON seed files         Historical incidents
                                                  and scenarios

  Charts                  Recharts                Optional dashboard
                                                  analytics

  Version control         Git + GitHub            Team collaboration
  -----------------------------------------------------------------------

## Agent Tools

The implementation uses simple Python tool functions rather than
introducing a separate agent-tool platform.

Example tool categories:

-   mock log retrieval
-   mock metrics retrieval
-   mock deployment information
-   simulated restart
-   simulated rollback
-   simulated cache operation
-   resolution verification

Risky actions are marked with `needs_approval` and require explicit
human approval before execution.

## Architecture

``` text
                    +----------------------+
                    |       React UI       |
                    | Dashboard / War Room |
                    | Simulator / Postmortem|
                    +----------+-----------+
                               |
                               | HTTP / SSE
                               v
                    +----------------------+
                    |      FastAPI         |
                    | API + Orchestration  |
                    +----+------------+----+
                         |            |
             +-----------+            +-------------+
             |                                        |
             v                                        v
    +------------------+                    +------------------+
    |     SQLite       |                    |   Agent Layer    |
    | Application      |                    | Investigation    |
    | State            |                    | Recommendation   |
    +------------------+                    +--------+---------+
                                                    |
                          +-------------------------+----------------------+
                          |                        |                      |
                          v                        v                      v
                   +-------------+          +-------------+        +-------------+
                   |   Hindsight |          | Claude API  |        | Python Tools|
                   | Long-Term   |          | Reasoning   |        | Logs/Metrics|
                   | Memory      |          |             |        | Actions     |
                   +-------------+          +-------------+        +-------------+
```

## Incident Lifecycle

### 1. Alert

An alert arrives through the API or is triggered from the simulator.

### 2. Classification

The system normalizes the alert and assigns a severity such as P1, P2,
or P3 using incident impact information.

### 3. Context Gathering

The agent collects the incident description and simulated operational
context such as logs, metrics, deployments, and service information.

### 4. Memory Recall

Hindsight is queried for historical incidents matching:

-   service
-   symptoms
-   errors
-   failure patterns
-   root causes
-   previous remediation outcomes

### 5. Investigation

The LLM combines current evidence with recalled memory and produces
structured hypotheses.

Each recommendation should include:

-   hypothesis
-   confidence
-   supporting evidence
-   related incidents
-   recommended runbook
-   successful fixes
-   failed fixes to avoid

### 6. Human Approval

The engineer can:

-   accept
-   edit
-   reject

Risky actions require approval.

### 7. Simulated Remediation

The selected action is executed against the simulation layer rather than
a real production environment.

### 8. Verification

The simulator returns a result indicating whether the incident was
resolved.

### 9. Post-Mortem

The system generates a structured post-mortem containing:

-   summary
-   impact
-   timeline
-   root cause
-   resolution
-   lessons learned

### 10. Learning

After engineer approval, the post-mortem and outcome are retained in
Hindsight so future incidents can benefit from the newly learned
information.

## Memory ON/OFF Demonstration

A core demonstration compares the same incident with memory enabled and
disabled.

### Memory OFF

``` text
New Incident
    |
    v
LLM sees only current evidence
    |
    v
Generic investigation
```

### Memory ON

``` text
New Incident
    |
    v
Hindsight Recall
    |
    v
Historical incidents + outcomes
    |
    v
LLM investigation with evidence
    |
    v
Specific recommendation
```

The goal is to demonstrate that persistent memory changes the quality
and specificity of incident response.

## Seed Data

The demo contains approximately 15--20 historical incidents.

The dataset should include:

-   multiple services
-   repeated failure patterns
-   successful fixes
-   3--4 failed or partially successful fixes
-   near-duplicate incidents
-   different severities
-   different root causes

Example scenarios:

1.  Database connection pool exhaustion
2.  Memory leak
3.  Bad deployment
4.  Cache stampede
5.  Novel incident with no strong historical match

## Example Recommendation

``` json
{
  "root_cause": "Database connection pool exhaustion",
  "confidence": 0.91,
  "similar_incidents": ["INC-104", "INC-117"],
  "recommended_runbook": "DB-POOL-RECOVERY",
  "recommended_action": "Increase pool capacity and restart the affected service",
  "avoid": [
    "Repeated application restart without correcting pool exhaustion"
  ],
  "evidence": [
    "INC-104 had the same error pattern",
    "DB-POOL-RECOVERY resolved INC-104",
    "The same runbook succeeded in INC-117"
  ],
  "needs_approval": true
}
```

## Repository Structure

``` text
incident-agent/
|
+-- backend/
|   +-- main.py
|   +-- settings.py
|   +-- requirements.txt
|   +-- schemas.py
|   +-- db/
|   +-- api/
|   |   +-- alerts.py
|   |   +-- incidents.py
|   |   +-- feedback.py
|   |   +-- events.py
|   |   +-- simulate.py
|   |   +-- postmortem.py
|   |   +-- analytics.py
|   |   +-- assistant.py
|   +-- llm.py
|   +-- memory/
|   +-- agent/
|   +-- tools/
|
+-- data/
|   +-- seed_incidents.json
|   +-- scenarios.json
|
+-- scripts/
|   +-- seed_memory.py
|
+-- frontend/
|   +-- package.json
|   +-- src/
|       +-- App.tsx
|       +-- api/
|       +-- types.ts
|       +-- components/
|       +-- pages/
|           +-- Dashboard/
|           +-- Simulator/
|           +-- WarRoom/
|           +-- Postmortem/
|           +-- Analytics/
|
+-- docs/
|   +-- ARCHITECTURE.md
|   +-- FEATURES.md
|   +-- DEVELOPMENT_PLAN.md
|
+-- docker-compose.yml
+-- README.md
```

## Main API Surface

  -------------------------------------------------------------------------------
  Method                  Endpoint                        Purpose
  ----------------------- ------------------------------- -----------------------
  POST                    `/alerts`                       Ingest or trigger an
                                                          alert

  GET                     `/incidents`                    List incidents

  GET                     `/incidents/{id}`               Get incident details

  GET                     `/incidents/{id}/similar`       Retrieve similar
                                                          incidents

  POST                    `/incidents/{id}/investigate`   Start investigation

  POST                    `/incidents/{id}/feedback`      Accept, edit, or reject
                                                          recommendation

  GET                     `/incidents/{id}/events`        Stream/read incident
                                                          events

  POST                    `/incidents/{id}/simulate`      Execute simulated
                                                          action

  POST                    `/incidents/{id}/postmortem`    Generate post-mortem

  POST                    `/memory/reset`                 Reset demo state

  GET                     `/analytics`                    Optional analytics

  POST                    `/assistant`                    Optional conversational
                                                          assistant
  -------------------------------------------------------------------------------

## Safety and Scope

This project is a hackathon demonstration and does not execute real
production remediation.

All operational actions are simulated.

The human-in-the-loop workflow is intentionally preserved:

``` text
Recommendation
      |
      v
Human Review
      |
  +---+---+
  |       |
Approve  Reject
  |
  v
Simulation
```

## Six-Hour Implementation Strategy

The implementation is intentionally constrained.

### Priority 1

-   Hindsight integration
-   Seed memory
-   Alert ingestion
-   Incident investigation
-   Similar incident retrieval
-   Root-cause recommendation
-   Runbook recommendation
-   Worked/failed fix handling
-   Human approval
-   Simulation
-   Post-mortem learning

### Priority 2

-   Dashboard polish
-   Live SSE timeline
-   Memory activity panel
-   Memory ON/OFF comparison

### Priority 3

-   Conversational assistant
-   Analytics
-   Novel incident detection
-   Smart alerts

Do not add real Kubernetes, cloud infrastructure, production monitoring,
complex vector databases, or a second memory system during the six-hour
implementation.

## Expected Demo

A successful demonstration should show:

1.  Historical incidents are already stored in Hindsight.
2.  A new outage is triggered from the simulator.
3.  The incident appears on the dashboard.
4.  The agent recalls similar incidents.
5.  The agent identifies a likely root cause.
6.  The agent recommends a proven runbook.
7.  The UI shows why the recommendation was made.
8.  The engineer approves the action.
9.  The action is simulated and verified.
10. A post-mortem is generated.
11. The engineer approves the post-mortem.
12. The new knowledge is retained in Hindsight.
13. A later similar incident can use the newly stored knowledge.

## Success Criteria

The project is considered complete when the team can demonstrate the
full loop:

``` text
Remember
   -> Investigate
   -> Recommend
   -> Approve
   -> Resolve
   -> Learn
   -> Remember Again
```

The most important proof point is that the agent can use historical
incident memory to produce a more specific, evidence-backed response
than it can when memory is disabled.

## Team Development

The project is designed for six contributors working in parallel.

Recommended ownership:

-   P1: AI and Hindsight integration
-   P2: FastAPI backend and application database
-   P3: Seed data, simulator, and tools
-   P4: Frontend shell, dashboard, and simulator
-   P5: War Room / investigation UI
-   P6: Post-mortem, analytics, Docker, documentation, and demo content

See `docs/DEVELOPMENT_PLAN.md` for the detailed six-hour plan.

## License

Add the license required by the hackathon or the team's repository
policy.
