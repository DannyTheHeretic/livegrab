# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for a Windows Livegrab.exe.

Run from the project root with Python only:

    py -3 -m PyInstaller --noconfirm --clean packaging/Livegrab.spec

static/ is bundled next to livegrab_lib. server.py sets PROJECT_ROOT to
Path(__file__).resolve().parent.parent. In a PyInstaller build that parent
is sys._MEIPASS, where --add-data places static/, so the frozen exe finds
index.html, app.js, and app.css without a source change.

If a future layout nests the package somewhere else, server.py has to set
the base directory from sys._MEIPASS when getattr(sys, "frozen", False).
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH).resolve().parent
hidden = collect_submodules("livegrab_lib")

a = Analysis(
    [str(root / "livegrab.py")],
    pathex=[str(root)],
    binaries=[],
    datas=[(str(root / "static"), "static")],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Livegrab",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
