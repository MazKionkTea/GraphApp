"""DB engine + session factory."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings
from app.db.base import Base


# SQLite needs check_same_thread=False for FastAPI's async pool
connect_args = {"check_same_thread": False} if "sqlite" in settings.db_path.as_uri() else {}

db_url = f"sqlite:///{settings.db_path}"
engine = create_engine(
    db_url,
    connect_args=connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Called on app startup."""
    # Import all models so SQLAlchemy knows about them
    from app.db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
