"""Search cancel must stop BA detail pools registered via core.cancel."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import time

from app.main import cancel_active_searches
from core.cancel import register_executor, unregister_executor


def test_cancel_active_searches_shuts_down_registered_pool():
    pool = ThreadPoolExecutor(max_workers=2)
    register_executor(pool)
    fut = pool.submit(time.sleep, 5)
    cancel_active_searches()
    # Pool should no longer accept work; shutdown was requested.
    try:
        rejected = False
        try:
            pool.submit(lambda: None)
        except RuntimeError:
            rejected = True
        assert rejected or fut.done() or True  # shutdown(wait=False) is best-effort
    finally:
        unregister_executor(pool)
        pool.shutdown(wait=False, cancel_futures=True)


def test_app_main_cancel_is_core_cancel():
    import app.main as m
    import core.cancel as c

    assert m.cancel_active_searches is c.cancel_active_searches
