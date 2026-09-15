"""Model catalog + download manager (checksum, resumable, atomic, disk check)."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from guenther.privacy import log_event

# No weights in git — catalog metadata only.
MODEL_CATALOG: dict[str, dict] = {
    "qwen3-1.7b": {
        "display_name": "Günther leicht (Qwen3 1.7B)",
        "license": "Apache-2.0",
        "approx_bytes": 1_200_000_000,
        "ram_gb_min": 3.0,
        "tier": "light",
        "filename": "Qwen3-1.7B-Q4_K_M.gguf",
        # Official HF GGUF repo; exact file may vary — manager verifies sha when set.
        "url": "",
        "sha256": "",
        "notes": "Apache-2.0; LIGHT default",
    },
    "qwen3-4b": {
        "display_name": "Günther Standard (Qwen3 4B)",
        "license": "Apache-2.0",
        "approx_bytes": 2_600_000_000,
        "ram_gb_min": 5.0,
        "tier": "standard",
        "filename": "Qwen3-4B-Q4_K_M.gguf",
        "url": "",
        "sha256": "",
        "notes": "Apache-2.0; STANDARD Autopick",
    },
    "phi4-mini": {
        "display_name": "Günther Alternative (Phi-4-mini)",
        "license": "MIT",
        "approx_bytes": 2_500_000_000,
        "ram_gb_min": 5.0,
        "tier": "standard",
        "filename": "Phi-4-mini-instruct-Q4_K_M.gguf",
        "url": "",
        "sha256": "",
        "notes": "MIT; STANDARD alternate",
    },
}


@dataclass
class DownloadProgress:
    model_id: str
    bytes_done: int = 0
    bytes_total: int = 0
    status: str = "idle"  # idle|checking|downloading|verifying|done|error|cancelled
    message: str = ""


@dataclass
class ModelManager:
    models_dir: Path
    catalog: dict[str, dict] = field(default_factory=lambda: dict(MODEL_CATALOG))

    def __post_init__(self) -> None:
        self.models_dir = Path(self.models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = self.models_dir / "installed.json"

    def list_catalog(self) -> list[dict]:
        out = []
        for mid, meta in self.catalog.items():
            row = {"id": mid, **meta, "installed": self.is_installed(mid)}
            out.append(row)
        return out

    def model_path(self, model_id: str) -> Path:
        meta = self.catalog[model_id]
        return self.models_dir / model_id / meta["filename"]

    def is_installed(self, model_id: str) -> bool:
        if model_id not in self.catalog:
            return False
        path = self.model_path(model_id)
        return path.is_file() and path.stat().st_size > 1_000_000

    def disk_free_bytes(self) -> int:
        usage = shutil.disk_usage(self.models_dir)
        return int(usage.free)

    def can_install(self, model_id: str) -> tuple[bool, str]:
        meta = self.catalog.get(model_id)
        if not meta:
            return False, "unknown_model"
        need = int(meta.get("approx_bytes") or 0) + 500_000_000  # headroom
        free = self.disk_free_bytes()
        if free < need:
            return False, "insufficient_disk"
        return True, "ok"

    def _load_state(self) -> dict:
        if not self._state_path.is_file():
            return {}
        try:
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_state(self, state: dict) -> None:
        tmp = self._state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self._state_path)

    def uninstall(self, model_id: str) -> bool:
        root = self.models_dir / model_id
        if root.exists():
            shutil.rmtree(root, ignore_errors=True)
        state = self._load_state()
        state.pop(model_id, None)
        self._save_state(state)
        log_event("model_uninstalled", model_id=model_id)
        return True

    def verify_checksum(self, path: Path, expected_sha256: str) -> bool:
        if not expected_sha256:
            return True  # REVIEW: empty sha means skip — user still opted in
        h = hashlib.sha256()
        with path.open("rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest().lower() == expected_sha256.lower()

    def install(
        self,
        model_id: str,
        *,
        progress_cb: Callable[[DownloadProgress], None] | None = None,
        cancel_check: Callable[[], bool] | None = None,
        allow_download: bool = False,
    ) -> DownloadProgress:
        """Download only when allow_download=True and URL configured — never silent."""
        prog = DownloadProgress(model_id=model_id, status="checking")
        meta = self.catalog.get(model_id)
        if not meta:
            prog.status = "error"
            prog.message = "unknown_model"
            return prog
        ok, reason = self.can_install(model_id)
        if not ok:
            prog.status = "error"
            prog.message = reason
            return prog
        if not allow_download:
            prog.status = "error"
            prog.message = "download_not_confirmed"
            return prog
        url = str(meta.get("url") or "")
        if not url:
            prog.status = "error"
            prog.message = "url_not_configured"
            log_event("model_install_blocked", model_id=model_id, reason="no_url")
            return prog

        dest_dir = self.models_dir / model_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        final_path = self.model_path(model_id)
        part_path = final_path.with_suffix(final_path.suffix + ".part")

        prog.status = "downloading"
        prog.bytes_total = int(meta.get("approx_bytes") or 0)
        if progress_cb:
            progress_cb(prog)

        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Karrierekrake-Guenther/1.0"})
            # Resume support
            headers = {}
            mode = "wb"
            existing = 0
            if part_path.is_file():
                existing = part_path.stat().st_size
                headers["Range"] = f"bytes={existing}-"
                mode = "ab"
            if headers:
                for k, v in headers.items():
                    req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=60) as resp, part_path.open(mode) as out:
                total = resp.headers.get("Content-Length")
                if total and not headers:
                    prog.bytes_total = int(total)
                prog.bytes_done = existing
                while True:
                    if cancel_check and cancel_check():
                        prog.status = "cancelled"
                        prog.message = "cancelled"
                        return prog
                    chunk = resp.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    prog.bytes_done += len(chunk)
                    if progress_cb:
                        progress_cb(prog)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            prog.status = "error"
            prog.message = "download_failed"
            log_event("model_download_failed", model_id=model_id, err=type(exc).__name__)
            return prog

        prog.status = "verifying"
        if progress_cb:
            progress_cb(prog)
        if not self.verify_checksum(part_path, str(meta.get("sha256") or "")):
            prog.status = "error"
            prog.message = "checksum_mismatch"
            part_path.unlink(missing_ok=True)
            return prog

        # Atomic replace
        tmp_final = final_path.with_suffix(".tmp")
        part_path.replace(tmp_final)
        tmp_final.replace(final_path)
        state = self._load_state()
        state[model_id] = {
            "path": str(final_path),
            "license": meta.get("license"),
            "filename": meta.get("filename"),
        }
        self._save_state(state)
        prog.status = "done"
        prog.message = "installed"
        log_event("model_installed", model_id=model_id)
        if progress_cb:
            progress_cb(prog)
        return prog


def default_models_dir() -> Path:
    """Resolve AppData models dir without importing desktop at module import time."""
    override = os.environ.get("KARRIEREKRAKE_MODELS_DIR")
    if override:
        return Path(override)
    try:
        from desktop.paths import ensure_app_dirs

        dirs = ensure_app_dirs()
        path = dirs["root"] / "models"
        path.mkdir(parents=True, exist_ok=True)
        return path
    except Exception:
        path = Path(tempfile.gettempdir()) / "Karrierekrake" / "models"
        path.mkdir(parents=True, exist_ok=True)
        return path
