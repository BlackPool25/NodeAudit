from __future__ import annotations

from checkout import checkout


def checkout_endpoint(token: str, amount_cents: int) -> dict[str, str]:
    result = checkout(token, amount_cents)
    return {"status": result}
