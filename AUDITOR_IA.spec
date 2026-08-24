# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

root = Path(SPECPATH)

datas = []
binaries = []
hiddenimports = [
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "shiboken6",
]


def collect_required(package: str) -> None:
    d, b, h = collect_all(package)
    datas.extend(d)
    binaries.extend(b)
    hiddenimports.extend(h)


for package in (
    "PySide6",
    "shiboken6",
    "openai",
    "httpx",
    "httpcore",
    "anyio",
    "pydantic",
    "pydantic_core",
    "certifi",
    "sniffio",
    "docx",
):
    try:
        collect_required(package)
    except Exception:
        pass

for distribution in (
    "PySide6",
    "openai",
    "python-docx",
    "pydantic",
    "httpx",
):
    try:
        datas.extend(copy_metadata(distribution))
    except Exception:
        pass

hiddenimports.extend(collect_submodules("openai"))
hiddenimports = list(dict.fromkeys(hiddenimports))

if (root / "resources").is_dir():
    datas.append((str(root / "resources"), "resources"))
if (root / "config" / "defaults.json").is_file():
    datas.append((str(root / "config" / "defaults.json"), "config"))
if (root / "ATTRIBUTIONS.md").is_file():
    datas.append((str(root / "ATTRIBUTIONS.md"), "."))

analysis = Analysis(
    ["main.py"],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[
        "torch",
        "torchaudio",
        "torchcodec",
        "pyannote",
        "faster_whisper",
        "ctranslate2",
        "av",
        "sounddevice",
        "soundcard",
        "matplotlib",
        "sklearn",
        "scipy",
        "tkinter",
        "pytest",
        "jupyter",
        "notebook",
    ],
    noarchive=False,
)

pyz = PYZ(analysis.pure)

icon = str(root / "resources" / "logo.ico") if (root / "resources" / "logo.ico").is_file() else None

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="AUDITOR_IA",
    icon=icon,
    console=False,
    debug=False,
    strip=False,
    upx=False,
)

coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    name="AUDITOR_IA_7.0.0_APP",
)
