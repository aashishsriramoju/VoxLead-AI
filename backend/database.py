# database.py – SQLAlchemy engine + session factory + Base class
# All DB setup in one place. Models import Base from here; main.py calls init_db().

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from config import DATABASE_URL

# connect_args is required only for SQLite to allow multi-thread access from FastAPI
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# Session factory – every request gets its own session via the dependency below
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """All ORM models inherit from this Base so create_all() finds them."""
    pass


def get_db():
    """
    FastAPI dependency that yields a DB session and always closes it.
    Usage:  db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called once at startup from main.py."""
    # Import models here so SQLAlchemy sees them before create_all()
    import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
