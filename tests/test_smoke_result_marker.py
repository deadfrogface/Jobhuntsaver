"""Smoke marker helpers must prefer isolated LOCALAPPDATA paths."""

from __future__ import annotations

import os
from pathlib import Path

from desktop.app import _smoke_result_paths, _write_smoke_result


def test_smoke_result_paths_prefer_localappdata(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("desktop.app.sys.executable", str(tmp_path / "fake" / "Jobhuntsaver.exe"))
    paths = _smoke_result_paths()
    assert paths[0] == tmp_path / "Jobhuntsaver" / "smoke_test_result.txt"
    assert paths[1] == tmp_path / "fake" / "smoke_test_result.txt"


def test_write_smoke_result_writes_token_file(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setattr("desktop.app.sys.executable", str(tmp_path / "dist" / "Jobhuntsaver.exe"))
    _write_smoke_result(["SMOKE_START", "token=abc", "SMOKE_TEST_OK"])
    marker = tmp_path / "Jobhuntsaver" / "smoke_test_result.txt"
    text = marker.read_text(encoding="utf-8")
    assert "token=abc" in text
    assert "SMOKE_TEST_OK" in text
    # Dist mirror also written when parent exists / is creatable
    dist = tmp_path / "dist" / "smoke_test_result.txt"
    assert dist.is_file()
