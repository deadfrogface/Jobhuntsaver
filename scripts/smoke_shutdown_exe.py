"""Packaged EXE: close via WM_CLOSE must terminate Jobhuntsaver.exe."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXE = ROOT / "dist" / "Jobhuntsaver" / "Jobhuntsaver.exe"
WM_CLOSE = 0x0010
TIMEOUT_S = 10.0


def _find_main_hwnd(pid: int) -> int:
    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def enum_proc(hwnd, _lparam):
        proc_id = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if proc_id.value == pid and user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                found.append(hwnd)
        return True

    user32.EnumWindows(enum_proc, 0)
    return int(found[0]) if found else 0


def main() -> int:
    if sys.platform != "win32":
        print("SKIP: Windows only")
        return 0
    if not EXE.exists():
        print(f"SKIP: {EXE} missing — build first")
        return 0

    subprocess.run(
        ["taskkill", "/F", "/IM", "Jobhuntsaver.exe"],
        capture_output=True,
        text=True,
    )
    time.sleep(0.5)

    # Isolated AppData so tray-minimize from a previous user setting cannot hide us.
    with tempfile.TemporaryDirectory(prefix="jhs_shutdown_") as tmp:
        env = os.environ.copy()
        env["LOCALAPPDATA"] = tmp
        # Pre-seed completed first-run so the wizard does not steal WM_CLOSE.
        appdata = Path(tmp) / "Jobhuntsaver"
        (appdata / "config").mkdir(parents=True, exist_ok=True)
        (appdata / "meta.json").write_text(
            '{"first_run_completed": true, "shutdown_fix_v1": true}\n',
            encoding="utf-8",
        )
        (appdata / "config" / "settings.yaml").write_text(
            "minimize_to_tray: false\nmode: search_only\ndry_run: true\n",
            encoding="utf-8",
        )
        proc = subprocess.Popen([str(EXE)], env=env, cwd=str(EXE.parent))
        print(f"Started pid={proc.pid} LOCALAPPDATA={tmp}")
        deadline = time.time() + 20
        hwnd = 0
        while time.time() < deadline:
            hwnd = _find_main_hwnd(proc.pid)
            if hwnd:
                break
            if proc.poll() is not None:
                print("FAIL: process exited before window appeared", proc.returncode)
                return 1
            time.sleep(0.25)
        if not hwnd:
            print("FAIL: main window not found")
            proc.kill()
            return 1

        print(f"Sending WM_CLOSE to hwnd={hwnd}")
        ctypes.windll.user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)

        end = time.time() + TIMEOUT_S
        while time.time() < end:
            if proc.poll() is not None:
                elapsed = TIMEOUT_S - (end - time.time())
                print(f"OK: process exited code={proc.returncode} after {elapsed:.1f}s")
                try:
                    EXE.rename(EXE.with_suffix(".exe.rename_test"))
                    EXE.with_suffix(".exe.rename_test").rename(EXE)
                    print("OK: EXE folder is not locked")
                except OSError as exc:
                    print(f"FAIL: EXE still locked: {exc}")
                    return 1
                return 0
            time.sleep(0.2)

        print("FAIL: process still running after timeout")
        # Diagnostics: still visible?
        print("hwnd still?", _find_main_hwnd(proc.pid))
        subprocess.run(["taskkill", "/F", "/PID", str(proc.pid)], capture_output=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
