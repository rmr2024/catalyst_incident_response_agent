import importlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from settings import memory_enabled, settings

log = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from db.session import init_db
        init_db()
    except Exception as e:
        log.warning("db init failed: %s", e)
    yield


app = FastAPI(title="Incident Response Agent", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list + ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True, "memory": memory_enabled()}


for _name in ["alerts", "incidents", "feedback", "events", "admin", "simulate", "postmortem", "analytics", "assistant"]:
    try:
        app.include_router(importlib.import_module(f"api.{_name}").router)
    except Exception as e:
        log.warning("router %s not loaded: %s", _name, e)
