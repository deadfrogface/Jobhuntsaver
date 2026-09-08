"""Human-readable run logging for Jobhuntsaver.

Privacy: never log CV/resume body text at INFO. Prefer paths, lengths, counts.
"""

from __future__ import annotations

import logging
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# ~2 MB × 3 backups keeps disk use bounded under AppData/logs
_LOG_MAX_BYTES = 2 * 1024 * 1024
_LOG_BACKUP_COUNT = 3


def _attach_rotating_file(logger: logging.Logger, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=_LOG_MAX_BYTES,
        backupCount=_LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")
    )
    logger.addHandler(handler)


class RunLogger:
    """Writes both standard logging and a readable run summary file."""

    def __init__(self, logs_dir: Path, name: str | None = None) -> None:
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.path = self.logs_dir / f"run_{name or stamp}.log"
        self._lines: list[str] = []

        self.logger = logging.getLogger("jobhuntsaver")
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")
            )
            self.logger.addHandler(handler)
            _attach_rotating_file(self.logger, self.path)

    def info(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M")
        line = f"{stamp} {message}"
        self._lines.append(line)
        self.logger.info(message)

    def error(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M")
        line = f"{stamp} ERROR {message}"
        self._lines.append(line)
        self.logger.error(message)

    def summary(self) -> str:
        return "\n".join(self._lines)


def setup_logging(logs_dir: Path | None = None) -> logging.Logger:
    """Configure root jobhuntsaver logger with rotating file under logs_dir."""
    logger = logging.getLogger("jobhuntsaver")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    stream = logging.StreamHandler()
    stream.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")
    )
    logger.addHandler(stream)
    if logs_dir is None:
        try:
            from desktop.paths import ensure_app_dirs

            logs_dir = ensure_app_dirs()["logs"]
        except Exception:
            logs_dir = Path("logs")
    _attach_rotating_file(logger, Path(logs_dir) / "jobhuntsaver.log")
    return logger
