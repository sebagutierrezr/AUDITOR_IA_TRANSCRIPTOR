from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import psutil


class Progress:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.value = -1
        self.last_write = 0.0

    def _write(self, payload: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        temp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.path)

    def __call__(self, value: int, message: str) -> None:
        now = time.monotonic()
        value = int(max(0, min(100, value)))
        if value == self.value and now - self.last_write < 0.35:
            return
        self.value = value
        self.last_write = now
        self._write({"type": "progress", "value": value, "message": str(message)})

    def failed(self, exc: Exception) -> None:
        self._write(
            {
                "type": "failed",
                "error_type": type(exc).__name__,
                "message": str(exc).strip() or type(exc).__name__,
            }
        )

    def completed(self, result_path: Path, warning: str | None = None) -> None:
        self._write(
            {
                "type": "completed",
                "value": 100,
                "message": "TRANSCRIPCION FINALIZADA",
                "result_path": str(result_path),
                "warning": warning or "",
            }
        )


def _lower_own_priority() -> None:
    try:
        proc = psutil.Process()
        if os.name == "nt":
            proc.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
        cpus = psutil.cpu_count(logical=True) or 4
        if cpus >= 6:
            proc.cpu_affinity(list(range(max(2, cpus - 2))))
    except Exception:
        pass


def run_job(job_path: Path) -> int:
    from app.services.audio_conversion_service import AudioConversionService
    from app.services.file_transcription_service import FileTranscriptionService
    from app.services.paths_service import AppPaths

    prepared: Path | None = None
    job = json.loads(job_path.read_text(encoding="utf-8"))
    result_path = Path(job["result_path"])
    progress_path = Path(job["progress_path"])
    progress = Progress(progress_path)

    _lower_own_priority()
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("OMP_NUM_THREADS", str(max(2, min(4, (os.cpu_count() or 4) - 2))))

    try:
        audio = Path(job["audio_path"])
        if not audio.is_file():
            raise FileNotFoundError("EL ARCHIVO DE AUDIO YA NO EXISTE.")

        progress(2, "PREPARANDO AUDIO...")
        prepared = AudioConversionService(AppPaths()).convert_to_mono_wav(audio, progress)

        service = FileTranscriptionService(str(job.get("performance_mode", "AUTO") or "AUTO"))
        segments, warning = service.transcribe(
            prepared,
            agent_label=job.get("speaker_one_label", "AGENTE"),
            client_label=job.get("speaker_two_label", "CLIENTE"),
            uppercase=bool(job.get("uppercase", True)),
            language=str(job.get("language", "ES") or "ES"),
            show_timestamps=bool(job.get("show_timestamps", True)),
            progress=progress,
        )

        payload = {
            "source_path": str(audio),
            "language": "ES",
            "segments": segments,
            "warning": warning or "",
        }
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        progress.completed(result_path, warning)
        return 0
    except Exception as exc:
        progress.failed(exc)
        return 2
    finally:
        if prepared is not None:
            try:
                prepared.unlink(missing_ok=True)
            except Exception:
                pass


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        return 2
    return run_job(Path(argv[0]).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
