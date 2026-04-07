"""Checkout flow."""

import cart
import payments


def submit_order(items: list[dict[str, float]]) -> str:
    total = cart.calculate_total(items)
    # Cascading symptom: negative total is observed here but root cause is config -> cart.
    if total < 0:
        return "error: negative total"
    gateway_ok = payments.run_gateway_check("https://gateway.example.com/health")
    if gateway_ok != 0:
        return "error: gateway"
    return payments.charge(total)
