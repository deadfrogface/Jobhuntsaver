"""Playwright Chromium detection, bundling path, check & repair.

Packaged EXE must NEVER run ``sys.executable -m playwright`` — that relaunches
Jobhuntsaver.exe. Use the Playwright driver binary, or rely on bundled browsers.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger("jobhuntsaver")

BROWSERS_DIRNAME = "ms-playwright"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def project_or_bundle_root() -> Path:
    """Directory containing the EXE (frozen) or the repo root (dev)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def meipass_dir() -> Path | None:
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return None


def candidate_browsers_dirs() -> list[Path]:
    """Ordered list of places where Chromium may live."""
    roots: list[Path] = []
    env = (os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or "").strip()
    if env:
        roots.append(Path(env))
    root = project_or_bundle_root()
    roots.append(root / BROWSERS_DIRNAME)
    mi = meipass_dir()
    if mi:
        roots.append(mi / BROWSERS_DIRNAME)
    # Dev / user cache fallback
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    roots.append(Path(local) / "ms-playwright")
    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[Path] = []
    for p in roots:
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def find_chromium_executable(browsers_dir: Path | None = None) -> Path | None:
    dirs = [browsers_dir] if browsers_dir else candidate_browsers_dirs()
    for base in dirs:
        if not base or not base.exists():
            continue
        matches = sorted(base.glob("chromium-*/chrome-win*/chrome.exe"))
        if matches:
            return matches[-1]  # newest revision if multiple
        # Headless shell / other layouts
        matches = sorted(base.glob("chromium_headless_shell-*/chrome-win*/headless_shell.exe"))
        if matches:
            return matches[-1]
    return None


def preferred_browsers_dir() -> Path:
    """Directory we set as PLAYWRIGHT_BROWSERS_PATH (create for repair installs)."""
    if is_frozen():
        # Prefer next to the EXE so the distribution is self-contained and repairable.
        return project_or_bundle_root() / BROWSERS_DIRNAME
    env = (os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or "").strip()
    if env:
        return Path(env)
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local) / "ms-playwright"


def configure_playwright_browsers_path() -> Path:
    """Set PLAYWRIGHT_BROWSERS_PATH for packaged/dev use. Call at app startup."""
    # If already set and contains chromium, keep it.
    existing = (os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or "").strip()
    if existing and find_chromium_executable(Path(existing)):
        return Path(existing)

    # Prefer a candidate that already has Chromium.
    for candidate in candidate_browsers_dirs():
        if find_chromium_executable(candidate):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(candidate)
            return candidate

    target = preferred_browsers_dir()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(target)
    return target


def playwright_available() -> bool:
    configure_playwright_browsers_path()
    if find_chromium_executable():
        return True
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            path = Path(getattr(p.chromium, "executable_path", "") or "")
            return bool(path) and path.exists()
    except Exception:
        return False


def browser_status_detail() -> str:
    configure_playwright_browsers_path()
    exe = find_chromium_executable()
    if exe:
        return f"OK: {exe}"
    return f"missing (expected under {preferred_browsers_dir()})"


def _playwright_driver_command() -> list[str]:
    """Return argv to run Playwright CLI via its driver — never sys.executable when frozen."""
    from playwright._impl._driver import compute_driver_executable

    driver_executable, driver_cli = compute_driver_executable()
    return [str(driver_executable), str(driver_cli)]


def _run_playwright_install(browsers_path: Path) -> tuple[bool, str]:
    browsers_path.mkdir(parents=True, exist_ok=True)
    try:
        from playwright._impl._driver import get_driver_env
    except Exception as exc:  # noqa: BLE001
        return False, f"Playwright-Treiber fehlt: {exc}"

    try:
        cmd = _playwright_driver_command() + ["install", "chromium"]
    except Exception as exc:  # noqa: BLE001
        return False, f"Playwright-Treiber nicht gefunden: {exc}"

    # Safety: never pass Jobhuntsaver.exe as interpreter
    if is_frozen() and Path(cmd[0]).resolve() == Path(sys.executable).resolve():
        return False, "Interner Fehler: Playwright-Treiber zeigt auf Jobhuntsaver.exe."

    env = os.environ.copy()
    env.update(get_driver_env())
    env["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers_path)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return False, "Zeitüberschreitung bei der Browser-Reparatur."
    except OSError as exc:
        return False, str(exc)

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        return False, detail or "Browser-Reparatur fehlgeschlagen."

    configure_playwright_browsers_path()
    if not find_chromium_executable(browsers_path) and not find_chromium_executable():
        return False, (
            "Download meldete Erfolg, aber Chromium wurde nicht gefunden. "
            f"Bitte Ordner prüfen: {browsers_path}"
        )
    return True, f"Browser-Komponente bereit ({browsers_path})"


def check_browser() -> tuple[bool, str]:
    """Verify bundled/local Chromium is present (no download)."""
    configure_playwright_browsers_path()
    exe = find_chromium_executable()
    if exe:
        return True, f"Browser-Komponente gefunden:\n{exe}"
    if is_frozen():
        return False, (
            "Browser-Komponente fehlt in dieser Installation.\n\n"
            f"Erwarteter Ordner:\n{preferred_browsers_dir()}\n\n"
            "Nutzen Sie „Browser-Komponente reparieren“ (Internet nötig) "
            "oder installieren Sie Jobhuntsaver erneut."
        )
    return False, (
        "Browser-Komponente fehlt.\n"
        "Nutzen Sie „Browser-Komponente reparieren“ oder:\n"
        "python -m playwright install chromium"
    )


def repair_browser() -> tuple[bool, str]:
    """Install/repair Chromium into the preferred browsers directory.

    Uses the Playwright driver binary — never relaunches the frozen EXE.
    """
    configure_playwright_browsers_path()
    if playwright_available():
        exe = find_chromium_executable()
        return True, f"Browser-Komponente ist bereits vorhanden:\n{exe}"

    target = preferred_browsers_dir()
    ok, msg = _run_playwright_install(target)
    if ok:
        return True, msg

    if is_frozen():
        return False, (
            f"{msg}\n\n"
            "Die mitgelieferte Browser-Komponente fehlt oder ist beschädigt.\n"
            f"Zielordner: {target}\n"
            "Bitte Internetverbindung prüfen oder Jobhuntsaver neu installieren."
        )
    return False, msg


# Backwards-compatible name used by workers
def install_chromium() -> tuple[bool, str]:
    """Legacy entry: check first; repair only if missing."""
    ok, msg = check_browser()
    if ok:
        return True, msg
    return repair_browser()
