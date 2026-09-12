"""Central, idempotent application shutdown for the desktop GUI."""

from __future__ import annotations

import atexit
import logging
import subprocess
import sys
import threading
from typing import Any, Callable

logger = logging.getLogger("jobhuntsaver.shutdown")

_DEFAULT_THREAD_WAIT_MS = 15000
_DEFAULT_PROCESS_WAIT_S = 3.0


class ApplicationShutdownManager:
    """Tracks GUI-owned resources and tears them down once on exit."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._done = False
        self._stopping = False
        self._threads: list[Any] = []  # QThread
        self._workers: list[Any] = []  # objects with request_cancel/cancel
        self._browsers: list[Any] = []  # BrowserManager-like
        self._processes: list[subprocess.Popen] = []
        self._pids: list[int] = []
        self._callbacks: list[Callable[[], None]] = []
        self._tray: Any = None
        self._log = logger

    @property
    def is_stopping(self) -> bool:
        return self._stopping or self._done

    def reset_for_tests(self) -> None:
        with self._lock:
            self._done = False
            self._stopping = False
            self._threads.clear()
            self._workers.clear()
            self._browsers.clear()
            self._processes.clear()
            self._pids.clear()
            self._callbacks.clear()
            self._tray = None

    def register_thread(self, thread: Any) -> None:
        with self._lock:
            if thread is not None and thread not in self._threads:
                self._threads.append(thread)

    def register_worker(self, worker: Any) -> None:
        with self._lock:
            if worker is not None and worker not in self._workers:
                self._workers.append(worker)

    def register_browser(self, browser: Any) -> None:
        with self._lock:
            if browser is not None and browser not in self._browsers:
                self._browsers.append(browser)

    def register_process(self, proc: subprocess.Popen) -> None:
        with self._lock:
            if proc is not None and proc not in self._processes:
                self._processes.append(proc)

    def register_pid(self, pid: int | None) -> None:
        """Track a raw PID (e.g. Playwright Chromium) for best-effort kill on exit."""
        if not pid:
            return
        with self._lock:
            if pid not in self._pids:
                self._pids.append(int(pid))

    def unregister_pid(self, pid: int | None) -> None:
        if not pid:
            return
        with self._lock:
            try:
                self._pids.remove(int(pid))
            except ValueError:
                pass

    def register_callback(self, callback: Callable[[], None]) -> None:
        with self._lock:
            self._callbacks.append(callback)

    def set_tray(self, tray: Any) -> None:
        with self._lock:
            self._tray = tray

    def _log_step(self, message: str) -> None:
        self._log.info(message)
        # Visible console breadcrumbs for packaged debugging only
        if getattr(sys, "frozen", False):
            print(f"[shutdown] {message}", flush=True)

    def shutdown(self, *, reason: str = "user") -> None:
        """Idempotent full shutdown. Safe to call multiple times."""
        with self._lock:
            if self._done:
                self._log_step("Shutdown already completed — ignoring.")
                return
            if self._stopping:
                self._log_step("Shutdown already in progress — ignoring re-entry.")
                return
            self._stopping = True

        self._log_step(f"Shutdown requested ({reason})")

        try:
            self._log_step("Stopping workers")
            self._cancel_workers()

            self._log_step("Stopping threads")
            self._stop_threads()

            self._log_step("Closing browser resources")
            self._close_browsers()

            self._log_step("Stopping tracked subprocesses")
            self._stop_processes()

            self._log_step("Running shutdown callbacks")
            self._run_callbacks()

            self._log_step("Hiding system tray")
            self._hide_tray()

            self._log_step("Quitting QApplication")
            self._quit_qt()

            self._log_step("Shutdown complete")
        except Exception as exc:  # noqa: BLE001
            self._log.exception("Shutdown error: %s", exc)
            self._log_step(f"Shutdown error: {exc}")
            self._quit_qt()
        finally:
            with self._lock:
                self._done = True
                self._stopping = False

    def _cancel_workers(self) -> None:
        # Ask pipeline to abandon hung JobSpy executors first.
        try:
            from app.main import cancel_active_searches

            cancel_active_searches()
        except Exception as exc:  # noqa: BLE001
            self._log.debug("cancel_active_searches: %s", exc)
        with self._lock:
            workers = list(self._workers)
        for worker in workers:
            try:
                if hasattr(worker, "request_cancel"):
                    worker.request_cancel()
                elif hasattr(worker, "cancel"):
                    worker.cancel()
            except Exception as exc:  # noqa: BLE001
                self._log.warning("Worker cancel failed: %s", exc)

    def _stop_threads(self) -> None:
        with self._lock:
            threads = list(self._threads)
            self._threads.clear()
        for thread in threads:
            try:
                # Guard against already-deleted C++ QThread wrappers.
                if thread is None:
                    continue
                try:
                    running = bool(hasattr(thread, "isRunning") and thread.isRunning())
                except RuntimeError:
                    # Internal C++ object already deleted
                    continue
                if not running:
                    continue
                if hasattr(thread, "requestInterruption"):
                    try:
                        thread.requestInterruption()
                    except RuntimeError:
                        continue
                if hasattr(thread, "quit"):
                    try:
                        thread.quit()
                    except RuntimeError:
                        continue
                if hasattr(thread, "wait"):
                    try:
                        if not thread.wait(_DEFAULT_THREAD_WAIT_MS):
                            self._log.warning(
                                "Thread did not finish within %sms — abandoning (no further calls)",
                                _DEFAULT_THREAD_WAIT_MS,
                            )
                    except RuntimeError:
                        continue
            except Exception as exc:  # noqa: BLE001
                self._log.warning("Thread stop failed: %s", exc)
        # Drop worker refs after threads are asked to stop — avoid double ownership.
        with self._lock:
            self._workers.clear()

    def _close_browsers(self) -> None:
        with self._lock:
            browsers = list(self._browsers)
            self._browsers.clear()
        for browser in browsers:
            try:
                browser.close()
            except Exception as exc:  # noqa: BLE001
                self._log.warning("Browser close failed: %s", exc)

    def _stop_processes(self) -> None:
        with self._lock:
            procs = list(self._processes)
            self._processes.clear()
            pids = list(self._pids)
            self._pids.clear()
        for pid in pids:
            try:
                import os
                import signal
                os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError, OSError) as exc:
                self._log.debug("PID %s already gone: %s", pid, exc)
            except Exception as exc:  # noqa: BLE001
                self._log.warning("PID cleanup failed for %s: %s", pid, exc)
        for proc in procs:
            try:
                if proc.poll() is not None:
                    continue
                proc.terminate()
                try:
                    proc.wait(timeout=_DEFAULT_PROCESS_WAIT_S)
                except subprocess.TimeoutExpired:
                    self._log.warning("Process %s still alive — killing", proc.pid)
                    proc.kill()
                    proc.wait(timeout=2)
            except Exception as exc:  # noqa: BLE001
                self._log.warning("Process cleanup failed: %s", exc)

    def _run_callbacks(self) -> None:
        with self._lock:
            callbacks = list(self._callbacks)
        for cb in callbacks:
            try:
                cb()
            except Exception as exc:  # noqa: BLE001
                self._log.warning("Shutdown callback failed: %s", exc)

    def _hide_tray(self) -> None:
        tray = self._tray
        if tray is None:
            return
        try:
            tray.hide()
            # Drop reference so Qt can tear down the tray icon
            if hasattr(tray, "setVisible"):
                tray.setVisible(False)
        except Exception as exc:  # noqa: BLE001
            self._log.warning("Tray hide failed: %s", exc)

    def _quit_qt(self) -> None:
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                app.quit()
        except Exception as exc:  # noqa: BLE001
            self._log.warning("QApplication.quit failed: %s", exc)


_manager: ApplicationShutdownManager | None = None
_manager_lock = threading.Lock()


def get_shutdown_manager() -> ApplicationShutdownManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = ApplicationShutdownManager()
            # Avoid noisy atexit during unit tests; packaged/GUI registers via aboutToQuit.
            if getattr(sys, "frozen", False) or "pytest" not in sys.modules:
                atexit.register(lambda: _manager and _manager.shutdown(reason="atexit"))
        return _manager
