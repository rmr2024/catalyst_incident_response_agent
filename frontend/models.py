"""
Incident Response Agent - Frontend Data Contract Layer (Pure Python / Pydantic)
Defines clean domain models matching the Incident Response Agent contract:
- Incident
- Alert
- SimilarIncident
- Recommendation
- SimulationScenario
- TimelineEvent
- IncidentStats & MemoryState

Supports both camelCase and snake_case field access via Pydantic model aliases.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["P1", "P2", "P3"]
IncidentStatus = Literal[
    "investigating",
    "recommended",
    "awaiting_approval",
    "executing",
    "resolved",
    "mitigated",
    "fix_failed",
]
ActionOutcome = Literal["worked", "failed", "partial"]
TimelineEventType = Literal["agent", "memory", "human", "action", "system"]


class BaseContractModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")


class SimilarIncident(BaseContractModel):
    incident_id: str = Field(alias="incidentId")
    similarity: float
    outcome: ActionOutcome
    root_cause: str = Field(alias="rootCause")
    resolution: str


class Recommendation(BaseContractModel):
    hypothesis: str
    confidence: float
    evidence: List[str] = Field(default_factory=list)
    recommended_steps: List[str] = Field(default_factory=list, alias="recommendedSteps")
    runbook: str
    failed_before: List[str] = Field(default_factory=list, alias="failedBefore")
    previous_successful_fix: Optional[str] = Field(default=None, alias="previousSuccessfulFix")
    needs_approval: bool = Field(default=True, alias="needsApproval")
    whats_different: str = Field(default="", alias="whatsDifferent")
    is_novel: bool = Field(default=False, alias="isNovel")


class TimelineEvent(BaseContractModel):
    id: str
    timestamp: str
    type: TimelineEventType
    message: str
    status: Optional[str] = None
    detail: Optional[str] = None


class Alert(BaseContractModel):
    id: str
    service: str
    error_rate: Optional[float] = Field(default=None, alias="errorRate")
    affected_users: Optional[int] = Field(default=None, alias="affectedUsers")
    impact: Optional[str] = None
    timestamp: str
    message: Optional[str] = None
    severity: Optional[Severity] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


class Incident(BaseContractModel):
    id: str
    title: str
    service: str
    severity: Severity
    status: IncidentStatus
    symptoms: str
    root_cause: Optional[str] = Field(default=None, alias="rootCause")
    resolution: Optional[str] = None
    started_at: str = Field(alias="startedAt")
    resolved_at: Optional[str] = Field(default=None, alias="resolvedAt")
    affected_users: Optional[int] = Field(default=None, alias="affectedUsers")
    recommendation: Optional[Recommendation] = None
    similar_incidents: List[SimilarIncident] = Field(default_factory=list, alias="similarIncidents")
    timeline: List[TimelineEvent] = Field(default_factory=list)
    is_novel: bool = Field(default=False, alias="isNovel")
    memory_used: bool = Field(default=True, alias="memoryUsed")
    outcome: Optional[str] = Field(default=None, alias="outcome")


class SimulationScenario(BaseContractModel):
    id: str
    name: str
    description: str
    service: str
    expected_severity: Severity = Field(alias="expectedSeverity")
    symptoms: str
    expected_matching_incident: str = Field(alias="expectedMatchingIncident")
    metrics: Dict[str, Any] = Field(default_factory=dict)


class IncidentStats(BaseContractModel):
    total: int = 0
    active: int = 0
    resolved_today: int = Field(default=0, alias="resolvedToday")
    p1: int = 0
    p2: int = 0
    p3: int = 0
    avg_ttr_minutes: float = Field(default=0.0, alias="avgTtrMinutes")


class MemoryState(BaseContractModel):
    enabled: bool
    actor: Optional[str] = "engineer"


class SimulationResponse(BaseContractModel):
    success: bool
    incident_id: Optional[str] = Field(default=None, alias="incidentId")
    status: Optional[str] = None
    message: Optional[str] = None
    incident: Optional[Incident] = None
    memory_enabled: bool = Field(default=True, alias="memoryEnabled")


# ---------------------------------------------------------------------------
# War Room contract (P5)
#
# Mirrors the backend investigation contract (backend/schemas.py and
# backend/db/models.py) consumed by pages/3_WarRoom.py.
#
# These deliberately subclass plain BaseModel rather than BaseContractModel:
# the War Room validates raw backend payloads that use snake_case exclusively
# and must not silently accept camelCase aliases from the dashboard contract.
#
# NOTE: this branch of the frontend already owns the names Alert and
# Recommendation for the dashboard/simulator contract (see above), and those
# have a different shape. The War Room's recommendation model is therefore
# exposed as WarRoomRecommendation to avoid shadowing the canonical one.
# ---------------------------------------------------------------------------


class MemoryHit(BaseModel):
    """A single recalled historical incident from long-term memory."""

    id: str
    text: str
    incident_id: Optional[str] = None
    score: Optional[float] = None
    outcome: Optional[ActionOutcome] = None


class Hypothesis(BaseModel):
    """A candidate root cause with confidence and supporting evidence ids."""

    cause: str
    confidence: float
    evidence_ids: List[str] = Field(default_factory=list)


class WarRoomRecommendation(BaseModel):
    """Investigation recommendation as returned by the backend."""

    hypotheses: List[Hypothesis] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    runbook: Optional[str] = None
    avoid: List[str] = Field(default_factory=list)
    whats_different: str = ""
    is_novel: bool = False
    similar: List[MemoryHit] = Field(default_factory=list)
    needs_approval: bool = True


class AgentEvent(BaseModel):
    """An agent/memory/human event recorded against an incident."""

    incident_id: str
    kind: Literal["agent", "memory", "human"]
    step: str
    detail: str = ""
    ts: Optional[str] = None


class ActionOut(BaseModel):
    """An executed (or pending) remediation step."""

    id: int
    incident_id: str
    idx: int
    step: str
    risky: bool = False
    status: str = "pending"
    output: str = ""
    ts: Optional[str] = None


class SimilarRef(BaseModel):
    """Lightweight reference to a similar incident."""

    incident_id: Optional[str] = None
    outcome: Optional[ActionOutcome] = None
    score: Optional[float] = None


class SmartAlert(BaseModel):
    """Severity-scored alert emitted by the ingestion pipeline."""

    incident_id: str
    severity: str
    severity_reason: str = ""
    service: str
    headline: str
    likely_cause: Optional[str] = None
    confidence: Optional[float] = None
    similar: List[SimilarRef] = Field(default_factory=list)
    recommended_response: Optional[str] = None
    avoid: List[str] = Field(default_factory=list)
    is_novel: bool = False
    needs_approval: bool = False


class IncidentSummary(BaseModel):
    """List-view incident summary (mirrors backend db.models.IncidentSummary)."""

    id: str
    service: str
    message: str
    severity: Severity
    severity_reason: str = ""
    source: str = "manual"
    status: str
    headline: Optional[str] = None
    is_novel: bool = False
    memory_used: bool = True
    top_hypothesis: Optional[str] = None
    top_confidence: Optional[float] = None
    suggestion_verdict: Optional[Literal["accepted", "edited", "rejected"]] = None
    outcome: Optional[str] = None
    resolution: Optional[str] = None
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None
    ttr_seconds: Optional[float] = None


class IncidentDetail(IncidentSummary):
    """Full incident detail consumed by the War Room."""

    alert: Dict[str, Any] = Field(default_factory=dict)
    recommendation: Optional[WarRoomRecommendation] = None
    smart_alert: Optional[SmartAlert] = None
    actions: List[ActionOut] = Field(default_factory=list)
    events: List[AgentEvent] = Field(default_factory=list)


class TimelineEntry(BaseModel):
    """A single row of the unified incident timeline."""

    ts: str
    source: Literal["event", "action", "audit"]
    kind: str
    title: str
    detail: str = ""


class FeedbackRequest(BaseModel):
    """Human review verdict for a recommended plan."""

    action: Literal["accept", "edit", "reject"]
    steps: Optional[List[str]] = None
    comment: Optional[str] = None
    actor: str = "engineer"
    retry: bool = False


class FeedbackResponse(BaseModel):
    """Result of submitting a FeedbackRequest."""

    incident_id: str
    status: Literal["executing", "investigating", "rejected"]


class ResolveRequest(BaseModel):
    """Operator-supplied resolution outcome for an incident."""

    outcome: ActionOutcome = "worked"
    resolution: Optional[str] = None
    actor: Optional[str] = None
