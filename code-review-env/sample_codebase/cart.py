"""Cart calculations."""

import config


def calculate_subtotal(items: list[dict[str, float]]) -> float:
    subtotal = 0.0
    for item in items:
        subtotal += float(item.get("price", 0.0)) * float(item.get("qty", 0.0))
    return subtotal


def calculate_total(items: list[dict[str, float]]) -> float:
    subtotal = calculate_subtotal(items)
    # BUG: config.DISCOUNT_RATE is intended to be 0.20, but set to 20 in config.
    discounted = subtotal - (subtotal * config.DISCOUNT_RATE)
    return discounted + (discounted * config.TAX_RATE)
