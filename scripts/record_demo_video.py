#!/usr/bin/env python3
"""Record a short real-app demo video (H.264 MP4) with fictional demo data.

Requires a display (xvfb-run recommended). Records via ffmpeg x11grab.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "docs" / "assets" / "demo"
OUT_MP4 = OUT_DIR / "stellenanker-demo.mp4"


def main() -> int:
    if not shutil.which("ffmpeg"):
        print("ffmpeg missing", file=sys.stderr)
        return 1
    display = os.environ.get("DISPLAY")
    if not display:
        print("DISPLAY not set — run under xvfb-run", file=sys.stderr)
        return 1

    tmp = tempfile.mkdtemp(prefix="stellenanker-demo-")
    os.environ["LOCALAPPDATA"] = tmp
    # Prefer real X for recording (not offscreen)
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        del os.environ["QT_QPA_PLATFORM"]

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication

    from desktop.demo_data import DEMO_PROFILE, seed_demo_database
    from desktop.i18n import i18n
    from desktop.main_window import MainWindow
    from desktop.services import ConfigService
    from desktop.theme import stylesheet_for

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication(sys.argv)
    svc = ConfigService()
    cfg = svc.load()
    cfg = svc.apply_safe_defaults(cfg)
    cfg.application.first_name = DEMO_PROFILE["first_name"]
    cfg.application.last_name = DEMO_PROFILE["last_name"]
    cfg.application.email = DEMO_PROFILE["email"]
    cfg.profile.location.home_address = "Berlin, Deutschland"
    cfg.profile.jobs.desired_titles = list(DEMO_PROFILE["titles"])
    cfg.settings.theme = "light"
    cfg.settings.language = "de"
    cfg.settings.dry_run = True
    svc.save(cfg)
    svc.mark_first_run_done()
    seed_demo_database(cfg.db_path)
    i18n.set_language("de")
    app.setStyleSheet(stylesheet_for("light"))

    window = MainWindow(svc)
    window.resize(1180, 760)
    window.move(40, 40)
    window.show()
    window.raise_()
    window.profile.load_from_config()
    window.jobs.refresh()
    window.applications.refresh()
    window.dashboard.refresh()
    app.processEvents()

    raw = OUT_DIR / "_demo_raw.mkv"
    # Record root window region around the app
    ff = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-video_size",
            "1280x800",
            "-framerate",
            "15",
            "-f",
            "x11grab",
            "-i",
            f"{display}+0,0",
            "-t",
            "45",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "veryfast",
            "-crf",
            "28",
            str(raw),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    pages = [0, 1, 2, 3, 4, 5, 0]
    delays_ms = [2500, 4500, 3500, 4000, 3500, 3000, 2500]
    state = {"i": 0}

    def step() -> None:
        i = state["i"]
        if i >= len(pages):
            window.close()
            app.quit()
            return
        window._navigate(pages[i])
        app.processEvents()
        if pages[i] == 1 and window.jobs.table.rowCount() > 0:
            window.jobs.table.selectRow(0)
            app.processEvents()
        state["i"] = i + 1
        QTimer.singleShot(delays_ms[i], step)

    QTimer.singleShot(800, step)
    code = app.exec()
    try:
        ff.wait(timeout=60)
    except Exception:
        ff.kill()
    if raw.is_file() and raw.stat().st_size > 1000:
        subprocess.check_call(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(raw),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-crf",
                "26",
                str(OUT_MP4),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        raw.unlink(missing_ok=True)
        print(f"wrote {OUT_MP4.relative_to(ROOT)} size={OUT_MP4.stat().st_size}")
        return 0
    print("recording failed or empty", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
