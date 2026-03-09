from __future__ import annotations

import time
from collections import defaultdict
from contextlib import contextmanager
from threading import Lock
from typing import Dict, Iterator, Optional

_COUNTERS: Dict[str, float] = defaultdict(float)
_LOCK = Lock()


def _metric_key(name: str, tags: Optional[Dict[str, str]] = None) -> str:
    if not tags:
        return name
    normalized = ",".join(f"{k}={tags[k]}" for k in sorted(tags))
    return f"{name}|{normalized}"


def incr(name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None) -> None:
    key = _metric_key(name, tags)
    with _LOCK:
        _COUNTERS[key] += value


@contextmanager
def timed(name: str, tags: Optional[Dict[str, str]] = None) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = (time.perf_counter() - start) * 1000.0
        incr(f"{name}_count", 1.0, tags)
        incr(f"{name}_ms_total", elapsed, tags)


def get_metrics_snapshot() -> Dict[str, float]:
    with _LOCK:
        return dict(_COUNTERS)
