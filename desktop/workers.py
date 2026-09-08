"""Background workers so the GUI never freezes."""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QThread, Signal

from app.main import run_pipeline
from core.config import AppConfig
from desktop.services.browser_install import check_browser, repair_browser
from desktop.services.shutdown import get_shutdown_manager


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

    def run(self) -> None:
        try:
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


def start_worker(worker: QObject, slot_name: str = "run") -> QThread:
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(getattr(worker, slot_name))
    worker.finished.connect(thread.quit)
    if hasattr(worker, "failed"):
        worker.failed.connect(thread.quit)
    # Ensure thread/worker objects are deleted after finish
    thread.finished.connect(thread.deleteLater)
    mgr = get_shutdown_manager()
    mgr.register_thread(thread)
    mgr.register_worker(worker)
    thread.start()
    return thread
