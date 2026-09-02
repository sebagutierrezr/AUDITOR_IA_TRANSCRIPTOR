from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Todo el procesamiento de modelos es local.
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

_DLL_HANDLES = []


def _bundle_roots() -> list[Path]:
    roots: list[Path] = []
    if getattr(sys, "frozen", False):
        roots.append(Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)).resolve())
        roots.append(Path(sys.executable).resolve().parent)
    else:
        roots.append(Path(__file__).resolve().parent)

    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def _configure_bundled_ffmpeg() -> None:
    """Hace visible FFmpeg Shared antes de importar librerias multimedia."""
    candidates: list[Path] = []

    configured = os.environ.get("AUDITOR_IA_FFMPEG_BIN", "").strip()
    if configured:
        candidates.append(Path(configured))

    for root in _bundle_roots():
        candidates.append(root / "ffmpeg" / "bin")
        candidates.append(root / "ffmpeg")

    for folder in candidates:
        if not (folder / "ffmpeg.exe").is_file():
            continue

        os.environ["PATH"] = str(folder) + os.pathsep + os.environ.get("PATH", "")

        if os.name == "nt" and hasattr(os, "add_dll_directory"):
            try:
                _DLL_HANDLES.append(os.add_dll_directory(str(folder)))
            except OSError:
                pass
        return


_configure_bundled_ffmpeg()


def _find_bundle_file(relative: str) -> Path:
    for root in _bundle_roots():
        candidate = root / relative
        if candidate.is_file():
            return candidate
    return _bundle_roots()[0] / relative


def _runtime_self_test() -> int:
    """Prueba real del contenido que se entregara al usuario.

    No usa componentes antiguos de PyTorch/pyannote/speechbrain; 8.0.0 usa
    NeMo-Speech + SortFormer para archivos y Faster-Whisper para modo En vivo.
    """
    try:
        import PySide6
        import av
        import ctranslate2
        import faster_whisper
        import numpy
        import soundcard
        import sounddevice
        from faster_whisper import WhisperModel

        ffmpeg = _find_bundle_file("ffmpeg/bin/ffmpeg.exe")
        ffprobe = _find_bundle_file("ffmpeg/bin/ffprobe.exe")
        nemo = _find_bundle_file("nemo-speech/bin/nemo-speech.exe")
        asr = _find_bundle_file("models/nemotron-3.5-asr-streaming-0.6b.q8_0.gguf")
        diar = _find_bundle_file("models/sortformer-v2-q8_0.gguf")
        whisper_dir = _find_bundle_file("models/small/model.bin").parent

        required = [
            ffmpeg,
            ffprobe,
            nemo,
            asr,
            diar,
            whisper_dir / "model.bin",
            whisper_dir / "config.json",
            whisper_dir / "tokenizer.json",
        ]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError("Activos empaquetados incompletos: " + " | ".join(missing))

        ffmpeg_line = subprocess.check_output(
            [str(ffmpeg), "-version"],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=20,
        ).splitlines()[0]

        nemo_check = subprocess.run(
            [str(nemo), "doctor"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60,
        )
        if nemo_check.returncode != 0:
            raise RuntimeError("nemo-speech doctor fallo: " + nemo_check.stdout[-1200:])

        # Comprueba que el modelo de En vivo no solo exista: debe poder abrirse
        # totalmente offline con CTranslate2.
        model = WhisperModel(
            str(whisper_dir),
            device="cpu",
            compute_type="int8",
            cpu_threads=2,
            num_workers=1,
            local_files_only=True,
        )
        del model

        details = [
            ffmpeg_line,
            f"PySide6={PySide6.__version__}",
            f"NumPy={numpy.__version__}",
            f"PyAV={av.__version__}",
            f"CTranslate2={ctranslate2.__version__}",
            "FasterWhisper=OK",
            "FasterWhisperSmall=OK",
            "SoundCard=OK",
            "SoundDevice=OK",
            "NeMoSpeechDoctor=OK",
            "NemotronGGUF=OK",
            "SortFormerGGUF=OK",
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
