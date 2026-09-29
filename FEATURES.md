# Features

## Tier 1 --- Demo Core

### F1. Incident Memory and Seed Data

Stores historical operational knowledge in Hindsight.

Memory includes:

-   symptoms
-   service
-   errors
-   root cause
-   resolution
-   runbook
-   outcome
-   lessons learned

The initial dataset contains approximately 15--20 incidents.

### F2. Alert Ingestion and Severity Classification

Accepts alerts through an API and a demo trigger button.

The alert is normalized and classified as P1, P2, or P3 using incident
impact information.

### F3. Similar Incident Detection

Uses Hindsight recall to find historical incidents with similar:

-   symptoms
-   services
-   errors
-   failure patterns

### F4. Root-Cause Prediction with Evidence

Produces ranked root-cause hypotheses.

Each hypothesis includes:

-   confidence
-   supporting evidence
-   related historical incidents
-   explanation of the recommendation

### F5. Runbook Recommendation

Recommends a proven runbook based on similar incidents and previous
outcomes.

The system should prefer runbooks with successful historical outcomes.

### F6. Fix Outcome Memory

Tracks:

-   worked fixes
-   failed fixes
-   partially successful fixes

Successful fixes are prioritized. Failed fixes are surfaced as actions
to avoid.

### F7. Human-in-the-Loop Approval

Allows an engineer to:

-   accept
-   edit
-   reject

A risky remediation action cannot execute until approved.

### F8. Timeline and Audit Log

Records:

-   alert
-   investigation steps
-   memory calls
-   recommendations
-   approvals
-   actions
-   results

### F9. Post-Mortem Generation and Learning Loop

Generates a post-mortem containing:

-   summary
-   impact
-   timeline
-   root cause
-   resolution
-   lessons learned

After approval, the post-mortem is retained in Hindsight.

### F10. Incident Dashboard

Implemented as an interactive Streamlit dashboard displaying:

-   active incidents
-   resolved incidents
-   severity
-   affected service
-   current status
-   basic KPIs

### F11. Simulation Mode and Memory ON/OFF

Provided via a dedicated Streamlit Simulator page with predefined outage scenarios.

The memory toggle allows the same incident to be investigated with and
without historical memory.

### F12. Visible Memory Calls

Displays Hindsight activity in the Streamlit UI (War Room):

``` text
RECALL
  -> memories found
  -> incidents returned

RETAIN
  -> post-mortem stored
  -> memory updated
```

This makes the role of Hindsight visible during the demonstration.

## Tier 2 --- Optional

### F13. Conversational Assistant

Example questions:

-   Have we seen this before?
-   What fixed this last time?
-   Which runbook worked?
-   What should we avoid?

### F14. Analytics

Potential metrics:

-   time to resolve
-   memory-enabled vs memory-disabled response
-   recurring services
-   recurring root causes
-   recommendation outcomes

### F15. Novel Incident Detection

If no strong historical match exists, the agent explicitly reports that
the incident appears novel instead of inventing a historical match.

### F16. Smart Alerts

Adds contextual information to an alert:

-   severity
-   likely cause
-   similar incidents
-   recommended response

## Feature Prioritization

  Priority                  Features
  ------------------------- ----------
  Must build                F1--F12
  Build if core is stable   F13, F15
  Last priority             F14, F16

## Non-Goals for the Six-Hour Build

The project does not require:

-   real production infrastructure
-   Kubernetes control
-   real cloud remediation
-   complex vector database infrastructure
-   multiple memory databases
-   enterprise RBAC
-   production monitoring integrations
-   complex machine-learning models
-   autonomous destructive operations

The goal is to prove the memory-driven incident response workflow.
