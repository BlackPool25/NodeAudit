from __future__ import annotations

from auth import validate_token
from payments import charge_card


def checkout(token: str, amount_cents: int) -> str:
    user = validate_token(token)
    # Medium bug: user may be None and attribute access will fail.
    charge_card(user["card_token"], amount_cents)
    return "ok"
