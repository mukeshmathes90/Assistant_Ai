"""Database engine and session."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Knowledge-base metadata columns added after the original schema. SQLAlchemy's
# create_all() does not alter existing tables, so for SQLite we add any missing
# columns with a lightweight, idempotent ALTER TABLE migration.
_KB_METADATA_COLUMNS = [
    ("faqs", "source_url", "VARCHAR(300)"),
    ("faqs", "source_type", "VARCHAR(40)"),
    ("faqs", "last_updated", "DATETIME"),
    ("college_information", "source_url", "VARCHAR(300)"),
    ("college_information", "source_type", "VARCHAR(40)"),
    ("college_information", "last_updated", "DATETIME"),
]


def ensure_knowledge_columns():
    """Add knowledge-base provenance columns to existing tables if missing."""
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    statements = []
    for table, column, col_type in _KB_METADATA_COLUMNS:
        if not inspector.has_table(table):
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        if column not in existing:
            statements.append(
                f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"
            )
    if statements:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))


def init_db():
    """Create all tables and apply lightweight migrations."""
    from . import models  # noqa: F401  (ensure models are registered)

    Base.metadata.create_all(bind=engine)
    ensure_knowledge_columns()