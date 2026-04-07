from inventory import is_available


def pick_item(preferred: str, fallback: str) -> str:
    if is_available(preferred):
        return preferred
    return fallback
