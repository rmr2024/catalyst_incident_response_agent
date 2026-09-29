from datetime import datetime, timezone

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from schemas import AgentEvent


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Incident(SQLModel, table=True):
    id: str = Field(primary_key=True)
    service: str = Field(index=True)
    message: str
    severity: str = Field(index=True)
    severity_reason: str = ""
    source: str = "manual"
    status: str = Field(default="investigating", index=True)
    alert_json: str = "{}"
    recommendation_json: str | None = None
    smart_alert_json: str | None = None
    is_novel: bool = False
    memory_used: bool = True
    top_hypothesis: str | None = None
    top_confidence: float | None = None
    suggestion_verdict: str | None = None
    outcome: str | None = None
    resolution: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    resolved_at: datetime | None = None
    ttr_seconds: float | None = None


class EventRow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incident_id: str = Field(index=True)
    kind: str
    step: str
    detail: str = ""
    ts: datetime = Field(default_factory=utcnow)


class ActionRow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incident_id: str = Field(index=True)
    idx: int
    step: str
    risky: bool = False
    status: str = "pending"
    output: str = ""
    ts: datetime = Field(default_factory=utcnow)


class AuditLog(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    incident_id: str | None = Field(default=None, index=True)
    actor: str
    action: str
    payload_json: str = "{}"
    ts: datetime = Field(default_factory=utcnow)


class SimilarRef(BaseModel):
    incident_id: str | None = None
    outcome: str | None = None
    score: float | None = None


class SmartAlert(BaseModel):
    incident_id: str
    severity: str
    severity_reason: str
    service: str
    headline: str
    likely_cause: str | None = None
    confidence: float | None = None
    similar: list[SimilarRef] = []
    recommended_response: str | None = None
    avoid: list[str] = []
    is_novel: bool = False
    needs_approval: bool = False


class ActionOut(BaseModel):
    id: int
    incident_id: str
    idx: int
    step: str
    risky: bool
    status: str
    output: str
    ts: datetime


class IncidentSummary(BaseModel):
    id: str
    service: str
    message: str
    severity: str
    severity_reason: str
    source: str
    status: str
    headline: str | None = None
    is_novel: bool
    memory_used: bool
    top_hypothesis: str | None = None
    top_confidence: float | None = None
    suggestion_verdict: str | None = None
    outcome: str | None = None
    resolution: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None
    ttr_seconds: float | None = None


class IncidentDetail(IncidentSummary):
    alert: dict
    recommendation: dict | None = None
    smart_alert: SmartAlert | None = None
    actions: list[ActionOut] = []
    events: list[AgentEvent] = []
