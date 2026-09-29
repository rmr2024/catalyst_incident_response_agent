"""
Incident Response Agent - Frontend Data Contract Layer (Pure Python / Pydantic)
Re-exports domain models and registers them for seamless import.
"""

import sys
from models import (
    ActionOutcome,
    Alert,
    BaseContractModel,
    Incident,
    IncidentStatus,
    IncidentStats,
    MemoryState,
    Recommendation,
    Severity,
    SimilarIncident,
    SimulationResponse,
    SimulationScenario,
    TimelineEvent,
    TimelineEventType,
)

__all__ = [
    "ActionOutcome",
    "Alert",
    "BaseContractModel",
    "Incident",
    "IncidentStatus",
    "IncidentStats",
    "MemoryState",
    "Recommendation",
    "Severity",
    "SimilarIncident",
    "SimulationResponse",
    "SimulationScenario",
    "TimelineEvent",
    "TimelineEventType",
]

# Inject domain models into sys.modules['types'] so that both
# `from types import Alert, Incident...` and `from models import ...` work seamlessly.
_types_mod = sys.modules.get("types")
if _types_mod:
    for name in __all__:
        if name in globals():
            setattr(_types_mod, name, globals()[name])
