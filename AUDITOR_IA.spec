# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH)
datas = [
    (str(root / "resources"), "resources"),
]
binaries = []
hiddenimports = []

for package in (
    "PySide6",
    "faster_whisper",
    "ctranslate2",
    "av",
    "soundcard",
    "sounddevice",
    "docx",
    "numpy",
    "huggingface_hub",
):
    try:
        d, b, h = collect_all(package)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

a = Analysis(
    ["main.py"],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "matplotlib"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AUDITOR_IA",
    icon=str(root / "resources" / "logo.ico"),
    console=False,
    debug=False,
    strip=False,
    upx=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="AUDITOR_IA_6.0_PORTABLE",
)
