"""Background workers so the GUI never freezes."""

from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal

from app.main import run_pipeline
from core.config import AppConfig
from desktop.services.browser_install import check_browser, repair_browser


class PipelineWorker(QObject):
    progress = Signal(str)
    finished = Signal(dict)
    failed = Signal(str)

    def __init__(self, config: AppConfig, mode: str | None = None) -> None:
        super().__init__()
        self.config = config
        self.mode = mode

    def run(self) -> None:
        try:
            stats = run_pipeline(
                self.config,
                mode=self.mode,
                progress_callback=self.progress.emit,
            )
            self.finished.emit(stats or {})
        except Exception as exc:  # noqa: BLE001 — surface user-friendly via failed
            self.failed.emit(str(exc))


class BrowserCheckWorker(QObject):
    finished = Signal(bool, str)

    def run(self) -> None:
        ok, msg = check_browser()
        self.finished.emit(ok, msg)


class BrowserRepairWorker(QObject):
    finished = Signal(bool, str)

    def run(self) -> None:
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
    thread.start()
    return thread
