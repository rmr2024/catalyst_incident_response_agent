from fastapi import APIRouter

from db import crud

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("")
def analytics():
	return crud.stats(include_analytics=True)
