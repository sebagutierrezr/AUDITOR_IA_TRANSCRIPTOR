from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Evita llamadas externas durante la diarización local.
# Los modelos ya vienen incluidos en la distribución.
os.environ.setdefault("PYANNOTE_METRICS_ENABLED", "0")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

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
        import speechbrain

        from app.services.speechbrain_compat import (
            patch_speechbrain_lazy_import,
        )

        patch_speechbrain_lazy_import()

        import soundcard
        import sounddevice
        import sklearn

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
            f"SpeechBrain={speechbrain.__version__}",
            "SoundCard=OK",
            "sounddevice=OK",
            f"Sklearn={sklearn.__version__}",
        ]

        if getattr(sys, "frozen", False):
            base = Path(sys.executable).resolve().parent
            required = [
                base / "models" / "small" / "model.bin",
                base / "models" / "pyannote-community-1" / "config.yaml",
                base / "models" / "speechbrain-ecapa" / "embedding_model.ckpt",
            ]
            missing = [str(path) for path in required if not path.is_file()]
            if missing:
                raise RuntimeError("Modelos empaquetados incompletos: " + " | ".join(missing))

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


def _run_file_worker_mode() -> int | None:
    if "--file-worker-smoke" in sys.argv:
        print("AUDITOR_FILE_WORKER_SMOKE_OK", flush=True)
        return 0

    if "--file-worker" not in sys.argv:
        return None

    try:
        index = sys.argv.index("--file-worker")
        job_path = sys.argv[index + 1]
    except (ValueError, IndexError):
        return 2

    from app.file_worker_cli import main as file_worker_main
    return file_worker_main([job_path])


_file_worker_exit = _run_file_worker_mode()
if _file_worker_exit is not None:
    raise SystemExit(_file_worker_exit)


from app.bootstrap import run_app


if __name__ == "__main__":
    raise SystemExit(run_app())
