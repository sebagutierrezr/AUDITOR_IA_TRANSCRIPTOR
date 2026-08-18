from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

_HANDLES = []


def configure_ffmpeg(path: Path) -> None:
    path = path.resolve()
    if not path.is_dir():
        raise RuntimeError(f"FFmpeg bin no existe: {path}")

    for pattern in (
        "avcodec-*.dll",
        "avformat-*.dll",
        "avutil-*.dll",
        "swresample-*.dll",
    ):
        if not list(path.glob(pattern)):
            raise RuntimeError(f"FFmpeg Shared incompleto: {pattern}")

    os.environ["PATH"] = str(path) + os.pathsep + os.environ.get("PATH", "")
    if os.name == "nt" and hasattr(os, "add_dll_directory"):
        _HANDLES.append(os.add_dll_directory(str(path)))

    first = subprocess.check_output(
        [str(path / "ffmpeg.exe"), "-version"], text=True, stderr=subprocess.STDOUT
    ).splitlines()[0]
    print(first)
    if "ffmpeg version 7" not in first.lower():
        raise RuntimeError("Se requiere FFmpeg 7 Shared.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg-bin", required=True)
    parser.add_argument("--voice-model", default="")
    args = parser.parse_args()

    configure_ffmpeg(Path(args.ffmpeg_bin))

    import PySide6
    import torch
    import torchcodec
    import pyannote.audio
    import faster_whisper
    import ctranslate2
    import av
    import numpy

    print("PySide6:", PySide6.__version__)
    print("Torch:", torch.__version__)
    print("TorchCodec: OK")
    print("pyannote.audio: OK")
    print("Faster-Whisper: OK")
    print("CTranslate2:", ctranslate2.__version__)
    print("PyAV:", av.__version__)
    print("NumPy:", numpy.__version__)

    if args.voice_model:
        model = Path(args.voice_model).resolve()
        if not (model / "config.yaml").is_file():
            raise RuntimeError(f"Community-1 incompleto: {model}")
        from pyannote.audio import Pipeline
        pipe = Pipeline.from_pretrained(str(model))
        if pipe is None:
            raise RuntimeError("Community-1 no pudo cargarse.")
        print("COMMUNITY-1 LOCAL: OK")

    print("RUNTIME NATIVO: VERIFICADO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
