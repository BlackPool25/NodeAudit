from __future__ import annotations


def charge_card(card_token: str, amount_cents: int) -> None:
    if amount_cents <= 0:
        raise ValueError("amount must be positive")
