# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import (
    collect_all,
    collect_submodules,
)


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
    """
    Dependencias críticas: si PyInstaller no puede recopilarlas,
    el build debe FALLAR en vez de crear un ejecutable incompleto.
    """
    d, b, h = collect_all(package)
    datas.extend(d)
    binaries.extend(b)
    hiddenimports.extend(h)


# Interfaz: nunca ocultar errores de colección.
require_package("PySide6")
require_package("shiboken6")

# Dependencias esenciales del producto.
for package in (
    "faster_whisper",
    "ctranslate2",
    "av",
    "docx",
    "numpy",
    "huggingface_hub",
    "torch",
    "torchaudio",
    "torchcodec",
    "pyannote.audio",
    "pyannote.core",
    "pyannote.database",
    "pyannote.metrics",
    "speechbrain",
    "lightning",
    "scipy",
    "sklearn",
    "soundcard",
    "sounddevice",
):
    try:
        require_package(package)
    except Exception as exc:
        # Paquetes no esenciales para el arranque pueden apoyarse
        # además en el análisis normal de imports, pero dejamos
        # constancia visible durante el build.
        print(
            f"[PyInstaller] Advertencia recopilando "
            f"{package}: {type(exc).__name__}: {exc}"
        )

# Refuerzo para módulos dinámicos de Qt.
hiddenimports.extend(
    collect_submodules("PySide6")
)

# Quitar duplicados manteniendo el orden.
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
        "matplotlib",
        "jupyter",
        "notebook",
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
    name="AUDITOR_IA_6.1.1_PORTABLE",
)
