"""
api/postmortem.py
-----------------
Postmortem API endpoints.

POST /incidents/{incident_id}/postmortem/draft
  – generate a draft postmortem (does NOT store it)

POST /incidents/{incident_id}/postmortem/approve
  – approve and retain the postmortem to long-term memory

GET /incidents/{incident_id}/postmortem
  – retrieve the retained postmortem (if any)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="", tags=["postmortem"])


class PostmortemApproveIn(BaseModel):
    postmortem: dict
    actor: str = "engineer"


@router.post("/incidents/{incident_id}/postmortem/draft")
async def draft_postmortem_endpoint(incident_id: str):
    """Generate a draft postmortem for an incident.  Not stored until approved."""
    try:
        from postmortem import draft_postmortem
    except ImportError as e:
        raise HTTPException(503, f"postmortem service unavailable: {e}")

    try:
        pm = await draft_postmortem(incident_id)
        return pm
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"postmortem generation failed: {str(e)[:200]}")


@router.post("/incidents/{incident_id}/postmortem/approve")
async def approve_postmortem_endpoint(incident_id: str, body: PostmortemApproveIn):
    """
    Approve and retain a postmortem.

    The postmortem is permanently stored in long-term memory only after
    this endpoint is called with a valid postmortem payload.
    """
    try:
        from postmortem import approve_postmortem
    except ImportError as e:
        raise HTTPException(503, f"postmortem service unavailable: {e}")

    try:
        result = await approve_postmortem(incident_id, body.postmortem)
        try:
            from db import crud
            crud.add_audit(incident_id, body.actor, "postmortem_approved", {"result": result})
        except Exception:
            pass
        return {"incident_id": incident_id, "status": "retained", "result": result}
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        raise HTTPException(500, f"postmortem retention failed: {str(e)[:200]}")


@router.get("/incidents/{incident_id}/postmortem")
async def get_postmortem(incident_id: str):
    """
    Return postmortem information for an incident.
    Checks if a postmortem has been retained in memory.
    """
    # Check if postmortem events exist in audit log
    try:
        from db import crud
        audit = crud.list_audit(incident_id)
        pm_events = [
            a for a in audit
            if a.action in ("postmortem_retained", "postmortem_approved")
        ]
        if pm_events:
            import json
            latest = pm_events[0]
            return {
                "incident_id": incident_id,
                "status": "retained",
                "retained_at": latest.ts.isoformat() if hasattr(latest.ts, "isoformat") else str(latest.ts),
                "detail": json.loads(latest.payload_json) if latest.payload_json else {},
            }
    except Exception:
        pass

    return {
        "incident_id": incident_id,
        "status": "not_retained",
        "detail": "No approved postmortem found. Use POST /incidents/{id}/postmortem/draft to generate one.",
    }
