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
