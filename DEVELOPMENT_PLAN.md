# Six-Hour Development Plan

## Team Structure

The project can be divided into six parallel workstreams.

  -----------------------------------------------------------------------
  Part                    Owner                   Primary Responsibility
  ----------------------- ----------------------- -----------------------
  P1                      AI and Integration      LLM, Hindsight, agent
                                                  workflow

  P2                      Backend                 FastAPI, SQLite, APIs,
                                                  SSE

  P3                      Data and Tools          Seed data, scenarios,
                                                  simulator, mock tools

  P4                      Frontend                Dashboard and simulator

  P5                      War Room                Investigation and
                                                  recommendation UI

  P6                      Post-Mortem and         Post-mortem, analytics,
                          Delivery                Docker, docs, demo
  -----------------------------------------------------------------------

## P1 --- AI and Hindsight Integration

### 0:00--0:20

Start Hindsight and create stub versions of the memory functions.

### 0:20--1:30

Implement:

-   `recall`
-   `retain_incident`
-   `retain_postmortem`
-   `reflect`

Include the incident ID in retained memory so recalled evidence can be
traced.

### 1:30--3:00

Build the agent pipeline:

``` text
context
 -> recall
 -> LLM reasoning
 -> structured JSON
 -> recommendation
```

The response should contain:

-   hypotheses
-   evidence IDs
-   recommended steps
-   runbook
-   failed fixes to avoid
-   approval requirement

### 3:00--3:45

Implement:

-   post-mortem drafting
-   retain-after-approval
-   memory ON/OFF behavior

### 3:45--4:30

Cache or provide fallback responses for the demo scenarios and tune
prompts.

## P2 --- Backend Core

### 0:00--0:15

Create FastAPI structure and router stubs.

### 0:15--1:30

Implement:

-   SQLite models
-   `POST /alerts`
-   `GET /incidents`
-   `GET /incidents/{id}`

### 1:30--2:30

Implement:

-   SSE event stream
-   feedback endpoint
-   event persistence

### 2:30--3:30

Implement:

-   memory toggle
-   reset endpoint
-   audit log query
-   CORS

### 3:30+

Fix integration issues.

## P3 --- Data, Simulator, and Tools

### 0:00--1:15

Create `seed_incidents.json` with approximately 18--20 incidents.

Include:

-   successful outcomes
-   3--4 failed fixes
-   partial outcomes
-   near-duplicate incidents

### 1:15--2:00

Create an idempotent memory seeding script.

### 2:00--3:00

Create approximately five scenarios:

1.  Database pool exhaustion
2.  Memory leak
3.  Bad deployment
4.  Cache stampede
5.  Novel incident

### 3:00--3:45

Create mock:

-   logs
-   metrics
-   deployments
-   remediation actions

### 3:45+

Run every scenario end-to-end.

## P4 --- Frontend Shell

### 0:00--0:30

Create:

-   Vite app
-   Tailwind
-   router
-   TypeScript types
-   API client
-   mock fixtures

### 0:30--2:00

Build Dashboard:

-   incident feed
-   severity badges
-   KPI cards
-   trigger alert button

### 2:00--3:00

Build Simulator:

-   scenario selection
-   memory ON/OFF
-   reset

### 3:00--3:30

Disable mocks and fix API contract mismatches.

### 3:30+

Global styling and integration.

## P5 --- War Room

The War Room is the primary demonstration page.

### 0:00--1:30

Build:

-   alert summary
-   logs
-   metrics
-   deployment context

### 1:30--2:30

Build:

-   ranked hypotheses
-   recommended steps
-   runbook
-   failed-fix warnings
-   similar incident panel
-   evidence explanation

### 2:30--3:30

Build:

-   live timeline
-   memory calls panel
-   Accept/Edit/Reject
-   Resolve button

### 3:30--4:00

Add novel-incident state.

### 4:00+

Polish the demonstration flow.

## P6 --- Post-Mortem and Delivery

### 0:00--0:45

Create Docker Compose and README.

### 0:45--2:15

Implement post-mortem generation, approval, and memory update
confirmation.

### 2:15--3:30

Implement optional analytics.

### 3:30--4:30

Prepare:

-   architecture diagram
-   screenshots
-   demo checklist
-   video script

### 4:30+

Run the complete demo and record it.

## Integration Checkpoints

### Checkpoint 1

Dashboard can trigger an incident.

### Checkpoint 2

Alert creates an incident and starts investigation.

### Checkpoint 3

Agent recalls historical memory and generates a recommendation.

### Checkpoint 4

War Room displays evidence and allows approval.

### Checkpoint 5

Simulation resolves the incident.

### Checkpoint 6

Post-mortem is generated and retained.

### Checkpoint 7

A later incident uses the newly retained memory.

## Anti-Conflict Rules

1.  Only edit files owned by your workstream.
2.  Shared files have one owner.
3.  Create API router stubs early so other contributors can work
    independently.
4.  Keep interfaces stable after integration starts.
5.  Merge small changes frequently.
6.  Do not add new dependencies without communicating them to the team.
7.  Do not change database schemas without informing the backend owner.
8.  Keep demo data deterministic.

## Definition of Done

The project is ready for demonstration when:

``` text
Trigger Scenario
      |
      v
Incident Appears
      |
      v
Memory Recall
      |
      v
Similar Incidents
      |
      v
Root Cause + Evidence
      |
      v
Runbook Recommendation
      |
      v
Human Approval
      |
      v
Simulated Resolution
      |
      v
Post-Mortem
      |
      v
Memory Updated
```

A second similar incident should be able to retrieve the newly stored
knowledge.
