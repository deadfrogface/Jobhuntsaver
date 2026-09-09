"""Shutdown manager unit tests."""

from __future__ import annotations

from desktop.services.shutdown import ApplicationShutdownManager, get_shutdown_manager


def test_shutdown_is_idempotent():
    mgr = ApplicationShutdownManager()
    calls = {"n": 0}

    def cb():
        calls["n"] += 1

    mgr.register_callback(cb)
    mgr.shutdown(reason="test")
    mgr.shutdown(reason="test-again")
    assert calls["n"] == 1
    assert mgr._done is True


def test_shutdown_cancels_workers():
    mgr = ApplicationShutdownManager()

    class DummyWorker:
        def __init__(self):
            self.cancelled = False

        def request_cancel(self):
            self.cancelled = True

    class DummyThread:
        def __init__(self):
            self.interrupted = False
            self.quit_called = False
            self._running = True

        def isRunning(self):
            return self._running

        def requestInterruption(self):
            self.interrupted = True

        def quit(self):
            self.quit_called = True
            self._running = False

        def wait(self, _ms):
            return True

    worker = DummyWorker()
    thread = DummyThread()
    mgr.register_worker(worker)
    mgr.register_thread(thread)
    mgr.shutdown(reason="test")
    assert worker.cancelled is True
    assert thread.interrupted is True
    assert thread.quit_called is True


def test_default_minimize_to_tray_is_false():
    from core.config import SettingsConfig

    assert SettingsConfig().minimize_to_tray is False


def test_get_shutdown_manager_singleton():
    a = get_shutdown_manager()
    b = get_shutdown_manager()
    assert a is b


def test_shutdown_closes_registered_browsers():
    mgr = ApplicationShutdownManager()

    class DummyBrowser:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    browser = DummyBrowser()
    mgr.register_browser(browser)
    mgr.shutdown(reason="browser-test")
    assert browser.closed is True
