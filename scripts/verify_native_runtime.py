from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

_DLL_HANDLES = []


def configure_ffmpeg(path: Path) -> None:
    path = path.resolve()
    if not path.is_dir():
        raise RuntimeError(f"FFmpeg bin no existe: {path}")

    for pattern in ("avcodec-*.dll", "avformat-*.dll", "avutil-*.dll", "swresample-*.dll"):
        if not list(path.glob(pattern)):
            raise RuntimeError(f"FFmpeg Shared incompleto. Falta {pattern}")

    os.environ["PATH"] = str(path) + os.pathsep + os.environ.get("PATH", "")
    if os.name == "nt" and hasattr(os, "add_dll_directory"):
        _DLL_HANDLES.append(os.add_dll_directory(str(path)))

    first = subprocess.check_output(
        [str(path / "ffmpeg.exe"), "-version"],
        text=True,
        stderr=subprocess.STDOUT,
    ).splitlines()[0]
    print(first)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg-bin", required=True)
    parser.add_argument("--voice-model", default="")
    args = parser.parse_args()

    configure_ffmpeg(Path(args.ffmpeg_bin))

    import PySide6
    import torch
    import torchaudio
    import torchcodec
    import pyannote.audio
    import speechbrain
    import sklearn
    import faster_whisper
    import ctranslate2
    import av
    import numpy

    print("PySide6:", PySide6.__version__)
    print("Torch:", torch.__version__)
    print("Torchaudio:", torchaudio.__version__)
    print("TorchCodec: IMPORT OK")
    print("pyannote.audio:", pyannote.audio.__version__)
    print("SpeechBrain:", speechbrain.__version__)
    print("scikit-learn:", sklearn.__version__)
    print("Faster-Whisper: IMPORT OK")
    print("CTranslate2:", ctranslate2.__version__)
    print("PyAV:", av.__version__)
    print("NumPy:", numpy.__version__)

    if args.voice_model:
        model_path = Path(args.voice_model).resolve()
        if not (model_path / "config.yaml").is_file():
            raise RuntimeError(f"Community-1 incompleto: {model_path}")

        from pyannote.audio import Pipeline
        pipeline = Pipeline.from_pretrained(str(model_path))
        if pipeline is None:
            raise RuntimeError("Community-1 no pudo cargarse localmente.")
        print("COMMUNITY-1 LOCAL: OK")

    print("RUNTIME NATIVO: VERIFICADO")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
