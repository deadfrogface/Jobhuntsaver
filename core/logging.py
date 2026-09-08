"""Human-readable run logging for Jobhuntsaver."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


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
            file_handler = logging.FileHandler(self.path, encoding="utf-8")
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")
            )
            self.logger.addHandler(file_handler)

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


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("jobhuntsaver")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
            datefmt="%H:%M:%S",
        )
    return logger
