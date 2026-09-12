"""Shared cancel registry for search ThreadPoolExecutors.

Keeps search cancel/shutdown out of circular imports between ``app.main`` and
individual job sources (e.g. Bundesagentur detail enrichment pools).
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor

_active_executors: list[ThreadPoolExecutor] = []
_executors_lock = threading.Lock()
_cancel_generation = 0


def register_executor(pool: ThreadPoolExecutor) -> None:
    with _executors_lock:
        if pool not in _active_executors:
            _active_executors.append(pool)


def unregister_executor(pool: ThreadPoolExecutor) -> None:
    with _executors_lock:
        if pool in _active_executors:
            _active_executors.remove(pool)


def current_cancel_generation() -> int:
    with _executors_lock:
        return _cancel_generation


def searches_cancelled(generation: int) -> bool:
    with _executors_lock:
        return generation != _cancel_generation


def cancel_active_searches() -> None:
    """Best-effort: stop accepting futures; running work may still finish."""
    global _cancel_generation
    with _executors_lock:
        _cancel_generation += 1
        pools = list(_active_executors)
        _active_executors.clear()
    for pool in pools:
        try:
            pool.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            # Python <3.9 cancel_futures
            try:
                pool.shutdown(wait=False)
            except Exception:
                pass
        except Exception:
            pass
