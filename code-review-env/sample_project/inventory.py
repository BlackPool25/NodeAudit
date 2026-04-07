from validators import is_non_empty


STOCK = {"widget": 4, "gizmo": 0}


def is_available(item_name: str) -> bool:
    if not is_non_empty(item_name):
        return False
    return STOCK.get(item_name, 0) > 0
