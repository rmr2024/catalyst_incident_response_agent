from sqlmodel import Session, SQLModel, create_engine

from settings import BACKEND_DIR, settings

_url = settings.database_url
if _url.startswith("sqlite:///./"):
    _url = f"sqlite:///{(BACKEND_DIR / _url[len('sqlite:///./'):]).as_posix()}"

_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(_url, connect_args=_args)


def init_db() -> None:
    import db.models  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    return Session(engine, expire_on_commit=False)
