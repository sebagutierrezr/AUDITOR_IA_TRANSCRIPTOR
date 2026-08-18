from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_DLL_HANDLES = []


def _configure_bundled_ffmpeg() -> None:
    """Make bundled FFmpeg Shared visible before TorchCodec/pyannote import."""
    candidates: list[Path] = []

    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
        candidates.extend(
            [
                base / "ffmpeg" / "bin",
                base / "_internal" / "ffmpeg" / "bin",
            ]
        )
    else:
        configured = os.environ.get("AUDITOR_IA_FFMPEG_BIN", "").strip()
        if configured:
            candidates.append(Path(configured))

    for folder in candidates:
        if not folder.is_dir():
            continue

        os.environ["PATH"] = str(folder) + os.pathsep + os.environ.get("PATH", "")

        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            try:
                _DLL_HANDLES.append(os.add_dll_directory(str(folder)))
            except OSError:
                pass
        return


_configure_bundled_ffmpeg()


def _runtime_self_test() -> int:
    try:
        import PySide6
        from PySide6.QtWidgets import QApplication

        import av
        import ctranslate2
        import faster_whisper
        import numpy
        import torch
        import torchaudio
        import torchcodec
        import pyannote.audio

        line = subprocess.check_output(
            ["ffmpeg", "-version"],
            text=True,
            stderr=subprocess.STDOUT,
        ).splitlines()[0]

        app = QApplication.instance() or QApplication([])
        app.quit()

        details = [
            f"FFmpeg={line}",
            f"PySide6={PySide6.__version__}",
            f"Torch={torch.__version__}",
            f"Torchaudio={torchaudio.__version__}",
            "TorchCodec=OK",
            f"Pyannote={pyannote.audio.__version__}",
            f"NumPy={numpy.__version__}",
            f"PyAV={av.__version__}",
            f"CTranslate2={ctranslate2.__version__}",
            "FasterWhisper=OK",
        ]

        Path("runtime_self_test_ok.txt").write_text("\n".join(details), encoding="utf-8")
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
