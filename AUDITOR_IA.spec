# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

root = Path(SPECPATH)
datas = [(str(root / "resources"), "resources"), (str(root / "ATTRIBUTIONS.md"), ".")]
binaries = []
hiddenimports = ["PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets", "shiboken6"]


def require_package(package: str) -> None:
    d, b, h = collect_all(package)
    datas.extend(d)
    binaries.extend(b)
    hiddenimports.extend(h)


for package in (
    "PySide6", "shiboken6", "faster_whisper", "ctranslate2", "av",
    "numpy", "torch", "torchaudio", "torchcodec", "pyannote.audio"
):
    require_package(package)

for package in (
    "huggingface_hub", "pyannote.core", "pyannote.database", "pyannote.metrics",
    "speechbrain", "lightning", "scipy", "sklearn", "matplotlib", "docx",
    "soundcard", "sounddevice"
):
    try:
        require_package(package)
    except Exception as exc:
        print(f"[PyInstaller] Advertencia: {package}: {type(exc).__name__}: {exc}")

hiddenimports.extend(collect_submodules("PySide6"))
hiddenimports = list(dict.fromkeys(hiddenimports))

a = Analysis(
    ["main.py"],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "jupyter", "notebook"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True, name="AUDITOR_IA",
    icon=str(root / "resources" / "logo.ico"), console=False, debug=False,
    strip=False, upx=False,
)
coll = COLLECT(
    exe, a.binaries, a.datas, strip=False, upx=False,
    name="AUDITOR_IA_6.1.1_PORTABLE",
)
