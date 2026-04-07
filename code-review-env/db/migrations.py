from __future__ import annotations

from pathlib import Path

from sqlmodel import SQLModel, create_engine


def get_default_db_path() -> Path:
    project_root = Path(__file__).resolve().parents[1]
    return project_root / "code_review_env.db"


def get_engine(db_path: str | Path | None = None, echo: bool = False):
    path = Path(db_path) if db_path else get_default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", echo=echo)


def init_db(db_path: str | Path | None = None, echo: bool = False) -> None:
    from db import schema  # noqa: F401

    engine = get_engine(db_path=db_path, echo=echo)
    SQLModel.metadata.create_all(engine)


if __name__ == "__main__":
    init_db()
    print("Database initialized")
