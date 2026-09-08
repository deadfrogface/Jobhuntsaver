"""Browser install helpers must never relaunch a frozen EXE."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

from desktop.services import browser_install as bi


def test_playwright_driver_command_not_sys_executable(monkeypatch):
    fake_exe = Path("C:/fake/Jobhuntsaver.exe")
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    monkeypatch.setattr(bi, "is_frozen", lambda: True)

    driver = (Path("C:/fake/node.exe"), Path("C:/fake/cli.js"))

    with mock.patch("playwright._impl._driver.compute_driver_executable", return_value=driver):
        cmd = bi._playwright_driver_command()
    assert Path(cmd[0]).name.lower() == "node.exe"
    assert Path(cmd[0]).resolve() != fake_exe.resolve()


def test_repair_refuses_if_driver_is_exe(monkeypatch, tmp_path):
    fake_exe = tmp_path / "Jobhuntsaver.exe"
    fake_exe.write_bytes(b"MZ")
    monkeypatch.setattr(sys, "executable", str(fake_exe))
    monkeypatch.setattr(bi, "is_frozen", lambda: True)
    monkeypatch.setattr(bi, "preferred_browsers_dir", lambda: tmp_path / "ms-playwright")
    monkeypatch.setattr(bi, "playwright_available", lambda: False)
    monkeypatch.setattr(bi, "configure_playwright_browsers_path", lambda: tmp_path / "ms-playwright")
    monkeypatch.setattr(
        bi,
        "_playwright_driver_command",
        lambda: [str(fake_exe), "install", "chromium"],
    )

    ok, msg = bi.repair_browser()
    assert ok is False
    assert "Jobhuntsaver.exe" in msg


def test_check_browser_finds_fake_chrome(monkeypatch, tmp_path):
    chrome = tmp_path / "chromium-999" / "chrome-win64" / "chrome.exe"
    chrome.parent.mkdir(parents=True)
    chrome.write_bytes(b"fake")
    monkeypatch.setattr(bi, "candidate_browsers_dirs", lambda: [tmp_path])
    monkeypatch.setattr(bi, "configure_playwright_browsers_path", lambda: tmp_path)
    ok, msg = bi.check_browser()
    assert ok is True
    assert "chrome.exe" in msg
