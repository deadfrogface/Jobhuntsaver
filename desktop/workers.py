"""Background workers so the GUI never freezes."""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QThread, Qt, Signal

from core.config import AppConfig
from desktop.services.browser_install import check_browser, repair_browser
from desktop.services.shutdown import get_shutdown_manager

# playwright / jobspy / app.main stay lazy — imported inside PipelineWorker.run only


class PipelineWorker(QObject):
    progress = Signal(str)
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, config: AppConfig, mode: str | None = None) -> None:
        super().__init__()
        self.config = config
        self.mode = mode
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        self._cancel.set()
        try:
            from app.main import cancel_active_searches

            cancel_active_searches()
        except Exception:
            pass

    def run(self) -> None:
        try:
            # Lazy: avoids importing playwright/jobspy at desktop startup
            from app.main import run_pipeline

            stats = run_pipeline(
                self.config,
                mode=self.mode,
                progress_callback=self.progress.emit,
                should_stop=self._cancel.is_set,
            )
            if self._cancel.is_set():
                self.progress.emit("Abgebrochen.")
            self.finished.emit(stats or {})
        except Exception as exc:  # noqa: BLE001 — surface user-friendly via failed
            self.failed.emit(str(exc))


class BrowserCheckWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self) -> None:
        super().__init__()
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        if self._cancel.is_set():
            self.finished.emit(False, "Abgebrochen.")
            return
        ok, msg = check_browser()
        self.finished.emit(ok, msg)


class BrowserRepairWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self) -> None:
        super().__init__()
        self._cancel = threading.Event()

    def request_cancel(self) -> None:
        self._cancel.set()

    def run(self) -> None:
        if self._cancel.is_set():
            self.finished.emit(False, "Abgebrochen.")
            return
        ok, msg = repair_browser()
        self.finished.emit(ok, msg)


# Backwards-compatible alias
BrowserInstallWorker = BrowserRepairWorker



def thread_is_running(thread: QThread | None) -> bool:
    """True if *thread* is a live, running QThread (never raises on deleted C++)."""
    if thread is None:
        return False
    try:
        return bool(thread.isRunning())
    except RuntimeError:
        # C++ QThread already destroyed (e.g. after deleteLater).
        return False


def connect_queued(signal, slot) -> None:
    """Always queue cross-thread UI updates onto the receiver thread.

    Plain Python callables connected without an explicit type can run in the
    *emitter* thread under PySide6 — which mutates QWidgets off the GUI thread
    and causes QObject/QTextDocument/QBasicTimer affinity errors.
    """
    signal.connect(slot, Qt.ConnectionType.QueuedConnection)


def start_worker(worker: QObject, slot_name: str = "run") -> QThread:
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(getattr(worker, slot_name))
    worker.finished.connect(thread.quit)
    if hasattr(worker, "failed"):
        worker.failed.connect(thread.quit)

    mgr = get_shutdown_manager()
    mgr.register_thread(thread)
    mgr.register_worker(worker)

    def _unregister() -> None:
        # Avoid double-ownership: do not call methods on this thread from shutdown
        # after it has finished. deleteLater only after unregister.
        with mgr._lock:
            if thread in mgr._threads:
                mgr._threads.remove(thread)
            if worker in mgr._workers:
                mgr._workers.remove(worker)
        try:
            worker.deleteLater()
        except RuntimeError:
            pass
        try:
            thread.deleteLater()
        except RuntimeError:
            pass

    thread.finished.connect(_unregister)
    thread.start()
    return thread
