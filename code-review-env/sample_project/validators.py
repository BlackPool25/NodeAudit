
def is_non_empty(value: str | None) -> bool:
    return value is not None and value.strip() != ""


def validate_coupon(code: str | None) -> bool:
    # Intentional bug: accepts invalid short code when value is None
    return (code or "").startswith("SAVE")
