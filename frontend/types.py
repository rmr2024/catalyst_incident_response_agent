"""
Shared schemas and types for the Incident Response Agent frontend.
Maps directly to backend contracts (backend/schemas.py and backend/db/models.py).
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class Alert(BaseModel):
    service: str
    message: str
    severity: Optional[Literal["P1", "P2", "P3"]] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[str] = None


class MemoryHit(BaseModel):
    id: str
    text: str
    incident_id: Optional[str] = None
    score: Optional[float] = None
    outcome: Optional[Literal["worked", "failed", "partial"]] = None


class Hypothesis(BaseModel):
    cause: str
    confidence: float
    evidence_ids: List[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    steps: List[str] = Field(default_factory=list)
    runbook: Optional[str] = None
    avoid: List[str] = Field(default_factory=list)
    whats_different: str = ""
    is_novel: bool = False
    similar: List[MemoryHit] = Field(default_factory=list)
    needs_approval: bool = True


class AgentEvent(BaseModel):
    incident_id: str
    kind: Literal["agent", "memory", "human"]
    step: str
    detail: str = ""
    ts: Optional[str] = None


class ActionOut(BaseModel):
    id: int
    incident_id: str
    idx: int
    step: str
    risky: bool = False
    status: Literal["pending", "running", "success", "failed"] = "pending"
    output: str = ""
    ts: Optional[str] = None


class SimilarRef(BaseModel):
    incident_id: Optional[str] = None
    outcome: Optional[str] = None
    score: Optional[float] = None


class SmartAlert(BaseModel):
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
    id: str
    service: str
    message: str
    severity: Literal["P1", "P2", "P3"]
    severity_reason: str = ""
    source: str = "manual"
    status: Literal["investigating", "recommended", "awaiting_approval", "executing", "resolved", "mitigated", "fix_failed"]
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
    alert: Dict[str, Any] = Field(default_factory=dict)
    recommendation: Optional[Recommendation] = None
    smart_alert: Optional[SmartAlert] = None
    actions: List[ActionOut] = Field(default_factory=list)
    events: List[AgentEvent] = Field(default_factory=list)


class Stats(BaseModel):
    total: int = 0
    active: int = 0
    p1: int = 0
    p2: int = 0
    p3: int = 0
    avg_ttr_minutes: float = 0.0


class Scenario(BaseModel):
    id: str
    title: str
    service: str
    severity: Literal["P1", "P2", "P3"]
    message: str
    description: str
    expected_root_cause: str
    recommended_runbook: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
