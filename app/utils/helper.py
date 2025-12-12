from typing import Any

def safe_int_convert(value: Any, default: int = 0) -> int:
    try:
        s = str(value)
        if '.' in s:
            return int(float(value))
        return int(value)
    except (ValueError, TypeError):
        return default