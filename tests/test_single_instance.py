"""Single-instance lock helpers."""

from __future__ import annotations

import uuid

from PySide6.QtCore import QSharedMemory
from PySide6.QtWidgets import QApplication

from desktop.app import _INSTANCE_KEY, acquire_single_instance_lock


def test_acquire_single_instance_lock_exclusive(qapp=None):
    # Ensure a QCoreApplication exists for QSharedMemory on some platforms.
    app = QApplication.instance() or QApplication([])
    # Use a unique key for this test so we don't collide with a running app.
    import desktop.app as app_mod

    original = app_mod._INSTANCE_KEY
    test_key = f"JobhuntsaverTestLock-{uuid.uuid4().hex}"
    app_mod._INSTANCE_KEY = test_key
    try:
        first = acquire_single_instance_lock()
        assert first is not None
        second = acquire_single_instance_lock()
        assert second is None
        # Release and re-acquire
        first.detach()
        again = acquire_single_instance_lock()
        assert again is not None
        again.detach()
    finally:
        app_mod._INSTANCE_KEY = original
        # Best-effort cleanup of any leftover segment under the test key
        leftover = QSharedMemory(test_key)
        if leftover.attach():
            leftover.detach()
        _ = app  # silence unused in some runners
