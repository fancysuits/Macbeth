# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller recipe for a self-contained macOS app."""

from pathlib import Path

project_root = Path(SPECPATH)
sprite = project_root / "scottish_terrier_sprites.png"
datas = [(str(sprite), ".")] if sprite.is_file() else []

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Macbeth",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
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
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Macbeth",
)
app = BUNDLE(
    coll,
    name="Macbeth.app",
    icon=None,
    bundle_identifier="com.example.macbeth-screen-pet",
    version="1.0.0",
    info_plist={
        "CFBundleDisplayName": "Macbeth",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    },
)

