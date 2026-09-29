from datetime import datetime
from typing import Literal
from pydantic import BaseModel

class Alert(BaseModel):
    service: str; message: str; severity: Literal["P1","P2","P3"] | None = None; metrics: dict = {}; timestamp: datetime
class MemoryHit(BaseModel):
    id: str; text: str; incident_id: str | None = None; score: float | None = None; outcome: Literal["worked","failed","partial"] | None = None
class Hypothesis(BaseModel):
    cause: str; confidence: float; evidence_ids: list[str]
class Recommendation(BaseModel):
    hypotheses: list[Hypothesis]; steps: list[str]; runbook: str | None; avoid: list[str]; whats_different: str; is_novel: bool; similar: list[MemoryHit]; needs_approval: bool
class AgentEvent(BaseModel):
    incident_id: str; kind: Literal["agent","memory","human"]; step: str; detail: str; ts: datetime
class Postmortem(BaseModel):
    incident_id: str; summary: str; timeline: list[str]; impact: str; root_cause: str; resolution: str; lessons: list[str]
