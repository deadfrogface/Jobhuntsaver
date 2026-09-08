# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Jobhuntsaver desktop app (one-folder)."""

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

hidden = (
    collect_submodules("search")
    + collect_submodules("apply")
    + collect_submodules("core")
    + collect_submodules("desktop")
)

a = Analysis(
    [os.path.join(ROOT, "desktop", "app.py")],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, "templates"), "templates"),
        (os.path.join(ROOT, "config", "profile.yaml.example"), "config"),
        (os.path.join(ROOT, "config", "application_profile.yaml.example"), "config"),
        (os.path.join(ROOT, "config", "settings.yaml.example"), "config"),
        (os.path.join(ROOT, "NOTICE"), "."),
        (os.path.join(ROOT, "LICENSE"), "."),
    ],
    hiddenimports=hidden
    + [
        "app.main",
        "browser.browser_manager",
        "playwright",
        "yaml",
        "PySide6",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Jobhuntsaver",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Jobhuntsaver",
)
