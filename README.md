# Incident Response Agent

A hackathon-scale incident response application with a FastAPI backend and a Streamlit frontend. It ingests incident alerts, records investigation and remediation activity, and provides incident analytics and post-mortems. The application stores incident data in SQLite and exposes a REST API with server-sent event streams.

## Current Architecture

- `backend/main.py` creates the FastAPI app, initializes the database, and registers API routers.
- `backend/api/` contains alert, incident, feedback, event, admin, post-mortem, and analytics routes.
- `backend/core/` coordinates incident intake, execution, outcomes, and event delivery.
- `backend/db/` contains SQLModel records, SQLite setup, and CRUD helpers.
- `backend/schemas.py` contains request/response data contracts.
- `frontend/` contains the Streamlit console, including Dashboard and Simulator pages, plus Python mock incident and scenario fixtures.

The backend can use configured integrations when available and includes fallback behavior for unavailable agent, memory, and action integrations.

## Prerequisites

- Python 3.11 or later
- For container use: Docker Desktop with its Linux engine running and Docker Compose support
- Optional integration credentials/settings are listed in `backend/.env.example`

## Run Locally

In PowerShell:

```powershell
cd backend
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
python -m pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at `http://localhost:8000`; interactive OpenAPI documentation is at `http://localhost:8000/docs`. The default local SQLite database is `backend/incidents.db` when launched from the `backend` directory. The application creates its tables on startup.

Set optional provider and integration values in `backend/.env` as needed. Do not commit secrets.

## Run With Docker Compose

From the repository root:

```powershell
docker compose up --build
```

Compose builds only the backend, using `backend/` as its build context, and publishes port 8000. The `backend-data` named volume is mounted at `/data`, with SQLite configured at `/data/incidents.db`; incident data persists across container recreation. Stop the service with `docker compose down`. `docker compose down --volumes` also deletes the database volume and its data.

This Compose setup is backend-only: it does not build or launch the Streamlit frontend. The image build requires Docker Desktop's Linux engine to be running.

## API

All endpoints are served from `http://localhost:8000`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health and memory-enabled status |
| `POST` | `/alerts` | Ingest an alert |
| `POST` | `/alerts/webhook` | Ingest generic or Alertmanager webhook payloads |
| `POST` | `/alerts/demo` | Create the built-in payments database demo incident |
| `GET` | `/incidents` | List incidents; supports status, service, severity, active, and limit filters |
| `GET` | `/incidents/stats` | Existing incident statistics |
| `GET` | `/incidents/{incident_id}` | Incident details |
| `GET` | `/incidents/{incident_id}/timeline` | Combined event, action, and audit timeline |
| `GET` | `/incidents/{incident_id}/memory-calls` | Memory-related incident events |
| `GET` | `/incidents/{incident_id}/similar` | Similar incidents from the recommendation |
| `GET` | `/incidents/{incident_id}/events` | Per-incident server-sent event stream |
| `GET` | `/events/stream` | Global server-sent event stream |
| `POST` | `/incidents/{incident_id}/feedback` | Accept, edit, or reject a recommendation |
| `POST` | `/incidents/{incident_id}/investigate` | Restart an incident investigation |
| `POST` | `/incidents/{incident_id}/simulate` | Execute the incident's remediation actions |
| `POST` | `/incidents/{incident_id}/resolve` | Record incident outcome and resolution |
| `POST`, `GET` | `/settings/memory` | Read or change the memory-enabled setting |
| `POST` | `/reset` | Reset incident data and memory setting |
| `GET` | `/audit` | List audit entries; supports incident_id and limit filters |
| `POST` | `/incidents/{incident_id}/postmortem` | Generate a post-mortem response from recorded incident data |
| `GET` | `/analytics` | Return overall statistics and field distributions |

The per-incident simulation endpoint is `/incidents/{incident_id}/simulate`. The separate P3 scenario API routes `GET /simulate/scenarios` and `POST /simulate/{scenario_id}` are not present. The `/assistant` router currently has no endpoints.

### P6: Post-mortem and Analytics

`POST /incidents/{incident_id}/postmortem` returns the existing `Postmortem` response fields: summary, timeline, impact, root cause, resolution, and lessons. It uses recorded incident, event, action, audit, alert, and recommendation data; the generated response is not stored as a separate record.

`GET /analytics` extends the existing statistics with memory-use counts, TTR summaries, and distributions for suggestion verdict, outcome, and top hypothesis. `GET /incidents/stats` retains the original statistics response.

### Example Requests

Trigger the built-in demo alert in PowerShell:

```powershell
$demo = Invoke-RestMethod -Method Post -Uri http://localhost:8000/alerts/demo
$demo
```

List incidents and inspect analytics/statistics:

```powershell
Invoke-RestMethod http://localhost:8000/incidents
Invoke-RestMethod http://localhost:8000/analytics
Invoke-RestMethod http://localhost:8000/incidents/stats
```

After the incident has been created, generate its post-mortem:

```powershell
$id = $demo.incident_id
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/incidents/$id/postmortem"
```

Equivalent curl examples:

```sh
curl -X POST http://localhost:8000/alerts/demo
curl http://localhost:8000/analytics
curl http://localhost:8000/incidents/stats
curl -X POST http://localhost:8000/incidents/INC-1001/postmortem
```

## Development and Testing

Run the backend from its directory so settings and the default SQLite file resolve as expected:

```powershell
cd backend
python -m compileall -q .
```

There is currently no checked-in automated test suite. Use `/docs` to inspect and exercise the API. For a clean local reset, `POST /reset` deletes all incident, event, action, and audit records.

## Current Limitations

- There are no P3 seed or scenario JSON files on current main. The frontend does include mock incident and scenario fixtures, and the backend provides the built-in `POST /alerts/demo` alert.
- The P3 scenario API routes `GET /simulate/scenarios` and `POST /simulate/{scenario_id}` are not implemented; per-incident simulation is available at `POST /incidents/{incident_id}/simulate`.
- The `/assistant` router currently has no endpoints.
- Docker image builds require Docker Desktop's Linux engine to be running.
