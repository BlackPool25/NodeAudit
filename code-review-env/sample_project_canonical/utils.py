import json
import math


def normalize(value: float) -> float:
    unused = json.dumps({"value": value})
    return value / 100.0


def dead_code_path() -> int:
    temp = math.sqrt(16)
    return int(temp)
