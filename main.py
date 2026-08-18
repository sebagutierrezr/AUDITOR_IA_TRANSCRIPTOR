from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_DLL_HANDLES = []


def _configure_native_runtime() -> None:
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
        candidates.extend([
            base / "ffmpeg" / "bin",
            base / "_internal" / "ffmpeg" / "bin",
        ])
    else:
        configured = os.environ.get("AUDITOR_IA_FFMPEG_BIN", "").strip()
        if configured:
            candidates.append(Path(configured))

    for folder in candidates:
        try:
            folder = folder.resolve()
        except Exception:
            continue
        if not folder.is_dir():
            continue
        os.environ["PATH"] = str(folder) + os.pathsep + os.environ.get("PATH", "")
        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            try:
                _DLL_HANDLES.append(os.add_dll_directory(str(folder)))
            except OSError:
                pass
        break


_configure_native_runtime()


def _runtime_self_test() -> int:
    try:
        import PySide6
        from PySide6.QtWidgets import QApplication
        import av
        import ctranslate2
        import faster_whisper
        import numpy
        import torch
        import torchcodec
        import pyannote.audio

        line = subprocess.check_output(
            ["ffmpeg", "-version"], text=True, stderr=subprocess.STDOUT
        ).splitlines()[0]
        if "ffmpeg version 7" not in line.lower():
            raise RuntimeError(f"FFmpeg incorrecto: {line}")

        app = QApplication.instance() or QApplication([])
        _ = PySide6.__version__
        _ = av.__version__
        _ = ctranslate2.__version__
        _ = numpy.__version__
        _ = torch.__version__
        _ = torchcodec
        _ = pyannote.audio
        _ = faster_whisper
        app.quit()
        return 0
    except Exception as exc:
        try:
            Path("runtime_self_test_error.txt").write_text(
                f"{type(exc).__name__}: {exc}", encoding="utf-8"
            )
        except Exception:
            pass
        return 91


if os.environ.get("AUDITOR_IA_SELF_TEST") == "1":
    raise SystemExit(_runtime_self_test())

from app.bootstrap import run_app

if __name__ == "__main__":
    raise SystemExit(run_app())
