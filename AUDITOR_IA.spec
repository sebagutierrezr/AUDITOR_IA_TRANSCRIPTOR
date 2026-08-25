# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules, copy_metadata

root = Path(SPECPATH)
datas = [
    (str(root / "resources"), "resources"),
    (str(root / "ATTRIBUTIONS.md"), "."),
]
binaries = []
hiddenimports = [
    "PySide6",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "shiboken6",
]


def require_package(package: str) -> None:
    d, b, h = collect_all(package)
    datas.extend(d)
    binaries.extend(b)
    hiddenimports.extend(h)


for package in (
    "PySide6",
    "shiboken6",
    "torch",
    "torchaudio",
    "torchcodec",
    "pyannote.audio",
    "pyannote.core",
    "pyannote.database",
    "pyannote.metrics",
    "pyannote.pipeline",
    "faster_whisper",
    "ctranslate2",
    "av",
    "numpy",
    "huggingface_hub",
    "lightning",
    "scipy",
    "sklearn",
    "matplotlib",
    "speechbrain",
    "hyperpyyaml",
    "yaml",
    "soundfile",
    "docx",
):
    require_package(package)

for distribution in (
    "PySide6",
    "torch",
    "torchaudio",
    "torchcodec",
    "pyannote.audio",
    "faster-whisper",
    "ctranslate2",
    "speechbrain",
    "scikit-learn",
    "hyperpyyaml",
    "PyYAML",
    "soundfile",
    "SoundCard",
    "sounddevice",
):
    try:
        datas.extend(copy_metadata(distribution))
    except Exception:
        pass

hiddenimports.extend(collect_submodules("PySide6"))
hiddenimports.extend(collect_submodules("torchcodec"))
hiddenimports.extend(
    collect_submodules(
        "speechbrain",
        filter=lambda name: not name.startswith(
            "speechbrain.integrations.k2_fsa"
        ),
    )
)
hiddenimports = list(dict.fromkeys(hiddenimports))

a = Analysis(
    ["main.py"],
    pathex=[str(root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=[
        "tkinter",
        "pytest",
        "jupyter",
        "notebook",
        "k2",
        "speechbrain.integrations.k2_fsa",
    ],
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
    name="AUDITOR_IA_7.1.3_BUILD",
)
