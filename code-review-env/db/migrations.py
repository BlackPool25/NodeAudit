from __future__ import annotations

import os
from pathlib import Path

from sqlmodel import SQLModel, create_engine
from sqlalchemy import inspect, text

from env.env_loader import load_env_file


def get_default_db_path() -> Path:
    project_root = Path(__file__).resolve().parents[1]
    return project_root / "code_review_env.db"


def get_engine(db_path: str | Path | None = None, echo: bool = False):
    load_env_file()
    env_url = os.getenv("GRAPHREVIEW_DATABASE_URL", "").strip()
    if env_url:
        connect_args: dict[str, object] = {}
        if env_url.startswith("sqlite://"):
            connect_args["check_same_thread"] = False
        return create_engine(env_url, echo=echo, connect_args=connect_args)

    # Turso remote URL path (libSQL over SQLAlchemy dialect).
    turso_url = (
        os.getenv("GRAPHREVIEW_REMOTE_SQLITE_URL", "").strip()
        or os.getenv("TURSO_DATABASE_URL", "").strip()
    )
    turso_token = (
        os.getenv("GRAPHREVIEW_REMOTE_SQLITE_AUTH_TOKEN", "").strip()
        or os.getenv("TURSO_AUTH_TOKEN", "").strip()
    )
    if turso_url:
        # Example TURSO_DATABASE_URL: libsql://my-db.turso.io
        engine_url = f"sqlite+{turso_url}?secure=true"
        connect_args: dict[str, object] = {}
        if turso_token:
            connect_args["auth_token"] = turso_token
        return create_engine(engine_url, echo=echo, connect_args=connect_args)

    path = Path(db_path) if db_path else get_default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", echo=echo, connect_args={"check_same_thread": False})


def init_db(db_path: str | Path | None = None, echo: bool = False) -> None:
    load_env_file()
    from db import schema  # noqa: F401

    engine = get_engine(db_path=db_path, echo=echo)
    SQLModel.metadata.create_all(engine)
    _apply_lightweight_migrations(engine)


def _apply_lightweight_migrations(engine) -> None:
    inspector = inspect(engine)
    if "trainingannotation" not in inspector.get_table_names():
        from db.schema import TrainingAnnotation  # local import to avoid circular startup order
        TrainingAnnotation.__table__.create(bind=engine, checkfirst=True)

    inspector = inspect(engine)
    if "reviewannotation" not in inspector.get_table_names():
        return

    existing_columns = {col["name"] for col in inspector.get_columns("reviewannotation")}
    add_statements: list[str] = []
    if "task_id" not in existing_columns:
        add_statements.append("ALTER TABLE reviewannotation ADD COLUMN task_id TEXT")
    if "reward_given" not in existing_columns:
        add_statements.append("ALTER TABLE reviewannotation ADD COLUMN reward_given FLOAT DEFAULT 0.0")
    if "attributed_to" not in existing_columns:
        add_statements.append("ALTER TABLE reviewannotation ADD COLUMN attributed_to TEXT")
    if "is_amendment" not in existing_columns:
        add_statements.append("ALTER TABLE reviewannotation ADD COLUMN is_amendment BOOLEAN DEFAULT 0")

    if not add_statements:
        add_statements = []

    if "moduleedge" in inspector.get_table_names():
        edge_columns = {col["name"] for col in inspector.get_columns("moduleedge")}
        if "connection_summary" not in edge_columns:
            add_statements.append("ALTER TABLE moduleedge ADD COLUMN connection_summary TEXT DEFAULT ''")

    if "analyzerrun" in inspector.get_table_names():
        analyzer_columns = {col["name"] for col in inspector.get_columns("analyzerrun")}
        if "analyzer_version" not in analyzer_columns:
            add_statements.append("ALTER TABLE analyzerrun ADD COLUMN analyzer_version TEXT DEFAULT ''")
        if "command_hash" not in analyzer_columns:
            add_statements.append("ALTER TABLE analyzerrun ADD COLUMN command_hash TEXT DEFAULT ''")

    if not add_statements:
        return

    with engine.begin() as conn:
        for stmt in add_statements:
            conn.execute(text(stmt))


if __name__ == "__main__":
    init_db()
    print("Database initialized")
