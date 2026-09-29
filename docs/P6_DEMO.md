# P6 Demo Guide

This API-focused demo shows the existing alert demo endpoint, incident details, statistics, analytics, and generated post-mortem. Current main also includes a Streamlit frontend with Dashboard and Simulator pages and per-incident simulation; this guide demonstrates the P6 APIs directly and does not require using the UI.

## 1. Start FastAPI

From PowerShell, install dependencies and start the backend:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Keep this terminal running. The API is at `http://localhost:8000`; `/docs` provides interactive API documentation. The app creates its SQLite tables at startup.

## 2. Create a Demo Alert

In a second PowerShell terminal:

```powershell
$base = "http://localhost:8000"
$demo = Invoke-RestMethod -Method Post -Uri "$base/alerts/demo"
$demo | Format-List
$incidentId = $demo.incident_id
```

Expected status: **200 OK**. The response includes the newly assigned `incident_id`, severity, severity reason, and initial status. The endpoint creates a payments database alert with recorded error-rate, latency, and affected-user metrics.

Equivalent curl request:

```sh
curl -i -X POST http://localhost:8000/alerts/demo
```

Copy the `incident_id` from the response when using curl for the following requests.

## 3. Show the Incident

```powershell
$incident = Invoke-RestMethod -Method Get -Uri "$base/incidents/$incidentId"
$incident | Format-List id, service, message, severity, status, top_hypothesis, outcome
```

Expected status: **200 OK**. The alert intake starts investigation in a background task, so status and investigation details can change after the initial response. Re-run the GET request to see the latest stored incident state.

Equivalent curl request (replace the ID):

```sh
curl -i http://localhost:8000/incidents/INC-1001
```

## 4. Request Incident Statistics

```powershell
Invoke-RestMethod -Method Get -Uri "$base/incidents/stats" | ConvertTo-Json -Depth 8
```

Expected status: **200 OK**. This returns the existing overall totals, status/severity counts, MTTR values, novelty count, and acceptance rate.

```sh
curl -i http://localhost:8000/incidents/stats
```

## 5. Request Analytics

```powershell
Invoke-RestMethod -Method Get -Uri "$base/analytics" | ConvertTo-Json -Depth 8
```

Expected status: **200 OK**. In addition to the existing statistics, analytics includes distributions for memory usage, suggestion verdicts, outcomes, and top hypotheses, plus TTR count/average/minimum/maximum. Values reflect incidents currently stored in the SQLite database.

```sh
curl -i http://localhost:8000/analytics
```

## 6. Generate a Post-mortem

```powershell
$postmortem = Invoke-RestMethod -Method Post -Uri "$base/incidents/$incidentId/postmortem"
$postmortem | Select-Object summary, timeline, impact, root_cause, resolution, lessons | Format-List
```

Expected status: **200 OK**. The response contains these fields:

- `summary`
- `timeline`
- `impact`
- `root_cause`
- `resolution`
- `lessons`

Equivalent curl request (replace the ID):

```sh
curl -i -X POST http://localhost:8000/incidents/INC-1001/postmortem
```

The post-mortem is generated as an API response from the incident's currently recorded data. It is **not persisted** as a separate database record. An unknown incident ID returns **404 Not Found**.

## Short Presentation Script

"I start the FastAPI service and trigger the built-in demo alert. The API returns a new incident ID, which I use to retrieve the incident and inspect the current investigation state. I then compare the existing incident statistics with the extended analytics endpoint. Finally, I request a post-mortem and show its summary, timeline, impact, root cause, resolution, and lessons. The post-mortem is assembled from recorded incident information and returned directly; it is not saved as a separate record."

## Scope and Limitations

- Current main includes the Streamlit frontend and per-incident `POST /incidents/{incident_id}/simulate` endpoint; this walkthrough remains API-focused.
- Current main does not contain P3 seed or scenario JSON files. The frontend has Python mock incident and scenario fixtures.
- The separate P3 scenario API routes `GET /simulate/scenarios` and `POST /simulate/{scenario_id}` are not present.
- The demo flow uses only the existing `POST /alerts/demo` endpoint and stored incident data.
