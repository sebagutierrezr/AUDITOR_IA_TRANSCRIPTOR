from __future__ import annotations

import ctypes
import json
import logging
import os
import sys
import time
from pathlib import Path

EVENT_PREFIX = "AUDITOR_EVENT|"


def emit_event(kind: str, **payload) -> None:
    data = {"type": kind, **payload}
    print(
        EVENT_PREFIX
        + json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        flush=True,
    )


class ThrottledProgress:
    def __init__(self) -> None:
        self._last_value = -1
        self._last_message = ""
        self._last_time = 0.0

    def __call__(self, value: int, message: str) -> None:
        now = time.monotonic()
        value = max(0, min(100, int(value)))
        message = str(message or "").strip()
        changed_value = value != self._last_value
        changed_message = message != self._last_message
        enough_time = now - self._last_time >= 0.18
        if not (
            changed_value and (enough_time or value in (0, 100))
        ) and not (
            changed_message and enough_time
        ):
            return
        self._last_value = value
        self._last_message = message
        self._last_time = now
        emit_event("progress", value=value, message=message)


def _lower_windows_priority() -> None:
    """Deja CPU disponible para la interfaz sin alterar la calidad del modelo."""
    if os.name != "nt":
        return
    try:
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetCurrentProcess()
        BELOW_NORMAL_PRIORITY_CLASS = 0x00004000
        kernel32.SetPriorityClass(handle, BELOW_NORMAL_PRIORITY_CLASS)
    except Exception:
        pass


def _conversation_to_dict(conversation) -> dict:
    return {
        "source_path": str(conversation.source_path),
        "language": str(conversation.language),
        "segments": [
            {
                "start": float(segment.start),
                "end": float(segment.end),
                "text": str(segment.text),
                "speaker": str(getattr(segment, "speaker", "HABLANTE")),
                "confidence": getattr(segment, "confidence", None),
                "words": list(getattr(segment, "words", None) or []),
            }
            for segment in conversation.segments
        ],
    }


def run_job(job_path: Path) -> int:
    _lower_windows_priority()

    cpu_count = max(2, os.cpu_count() or 4)
    ai_threads = max(2, min(4, cpu_count - 2))
    os.environ.setdefault("OMP_NUM_THREADS", str(ai_threads))
    os.environ.setdefault("MKL_NUM_THREADS", str(ai_threads))
    os.environ.setdefault("OPENBLAS_NUM_THREADS", str(ai_threads))
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("PYANNOTE_METRICS_ENABLED", "0")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

    from app.engines.faster_whisper_engine import FasterWhisperEngine
    from app.services.audio_conversion_service import AudioConversionService
    from app.services.diarization_service import DiarizationService
    from app.services.logging_service import configure_logging
    from app.services.paths_service import AppPaths

    configure_logging()
    logger = logging.getLogger(__name__)
    progress = ThrottledProgress()
    prepared_path = None

    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
        audio_path = Path(str(job["audio_path"]))
        result_path = Path(str(job["result_path"]))
        language = str(job.get("language", "ES"))
        uppercase = bool(job.get("uppercase", True))
        show_timestamps = bool(job.get("show_timestamps", True))
        speaker_one_label = str(job.get("speaker_one_label", "AGENTE"))
        speaker_two_label = str(job.get("speaker_two_label", "CLIENTE"))
        first_speaker_is_one = bool(job.get("first_speaker_is_one", False))

        emit_event("started", message="PROCESO INICIADO")
        progress(1, "VALIDANDO ARCHIVO...")

        paths = AppPaths()
        converter = AudioConversionService(paths)
        prepared_path = converter.convert_to_mono_wav(audio_path, progress)

        progress(20, "CARGANDO MOTOR DE TRANSCRIPCIÓN...")
        engine = FasterWhisperEngine("ALTA")
        if not engine.is_ready():
            raise RuntimeError(
                "EL MODELO FASTER-WHISPER SMALL NO ESTÁ INSTALADO O ESTÁ INCOMPLETO."
            )

        conversation = engine.transcribe(
            prepared_path,
            language,
            uppercase,
            show_timestamps,
            progress,
        )
        if not conversation.segments:
            raise RuntimeError("NO SE DETECTÓ VOZ EN EL ARCHIVO.")

        progress(88, "IDENTIFICANDO DOS HABLANTES...")
        diarization = DiarizationService()
        if not diarization.is_ready():
            raise RuntimeError("COMMUNITY-1 NO ESTÁ INSTALADO O ESTÁ INCOMPLETO.")

        conversation = diarization.diarize(
            conversation=conversation,
            audio_path=prepared_path,
            speaker_one_label=speaker_one_label,
            speaker_two_label=speaker_two_label,
            first_speaker_is_one=first_speaker_is_one,
            progress_callback=progress,
        )

        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(_conversation_to_dict(conversation), ensure_ascii=False),
            encoding="utf-8",
        )
        progress(100, "TRANSCRIPCIÓN FINALIZADA")
        emit_event("completed", result_path=str(result_path))
        return 0

    except Exception as exc:
        logger.exception("ERROR EN PROCESO AISLADO DE ARCHIVO")
        emit_event(
            "failed",
            error_type=type(exc).__name__,
            message=str(exc).strip() or type(exc).__name__,
        )
        return 2
    finally:
        if prepared_path is not None:
            try:
                prepared_path.unlink(missing_ok=True)
            except Exception:
                pass


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        emit_event(
            "failed",
            error_type="ArgumentError",
            message="FALTA EL ARCHIVO DE TRABAJO.",
        )
        return 2
    return run_job(Path(argv[0]).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
