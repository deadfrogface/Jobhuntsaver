"""Scheduled task must launch headless --once, never bare GUI EXE."""

from __future__ import annotations

import sys
from unittest.mock import patch

from core.config import empty_app_config
from desktop.services.schedule_service import ScheduleService


def test_dev_schedule_command_includes_once():
    svc = ScheduleService(empty_app_config())
    cmd = svc._python_command()
    assert "-m" in cmd
    assert "app.main" in cmd
    assert "--once" in cmd


def test_frozen_schedule_command_includes_once(tmp_path):
    svc = ScheduleService(empty_app_config())
    exe = str(tmp_path / "Jobhuntsaver.exe")
    with patch.object(sys, "frozen", True, create=True), patch.object(sys, "executable", exe):
        cmd = svc._python_command()
    assert cmd[0] == exe
    assert cmd[-1] == "--once"
    assert len(cmd) == 2
