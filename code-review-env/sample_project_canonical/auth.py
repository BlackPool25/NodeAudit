from __future__ import annotations

from typing import TypedDict


class User(TypedDict):
    id: str
    card_token: str


def validate_token(token: str) -> User | None:
    if token.startswith("tok_"):
        return {"id": token[-4:], "card_token": token}
    return None
