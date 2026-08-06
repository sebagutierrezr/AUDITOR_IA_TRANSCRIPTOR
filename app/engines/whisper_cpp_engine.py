import json
import logging
import os
import subprocess
from pathlib import Path

from app.engines.base_speech_engine import ProgressCallback, SpeechEngine
from app.models.conversation import Conversation, Segment
from app.services.audio_conversion_service import AudioConversionService
from app.services.paths_service import AppPaths


class WhisperCppEngine(SpeechEngine):
    def __init__(
        self,
        paths: AppPaths,
        audio_converter: AudioConversionService,
        model_name: str = "ggml-base-q5_1.bin",
    ) -> None:
        self._paths = paths
        self._audio_converter = audio_converter
        self._model_path = self._paths.models / model_name
        self._logger = logging.getLogger(__name__)

    @property
    def executable_path(self) -> Path:
        candidates = list(self._paths.engines.rglob("whisper-cli.exe"))
        if not candidates:
            candidates = list(self._paths.engines.rglob("main.exe"))
        return candidates[0] if candidates else self._paths.engines / "whisper-cli.exe"

    @property
    def model_path(self) -> Path:
        return self._model_path

    def is_ready(self) -> bool:
        return self.executable_path.exists() and self._model_path.exists()

    def transcribe(
        self,
        audio_path: Path,
        language: str,
        uppercase: bool,
        show_timestamps: bool,
        progress_callback: ProgressCallback | None = None,
    ) -> Conversation:
        if not self.is_ready():
            raise RuntimeError(
                "EL MOTOR O EL MODELO NO ESTÁ INSTALADO. "
                "INSTÁLELO DESDE CONFIGURACIÓN."
            )

        if progress_callback:
            progress_callback(5, "PREPARANDO AUDIO...")

        wav_path = self._audio_converter.convert_to_whisper_wav(audio_path)
        output_base = self._paths.temp / f"transcription_{os.getpid()}"

        try:
            if progress_callback:
                progress_callback(15, "TRANSCRIBIENDO...")

            threads = max(2, min(8, (os.cpu_count() or 4) - 1))
            command = [
                str(self.executable_path),
                "-m",
                str(self._model_path),
                "-f",
                str(wav_path),
                "-l",
                "auto" if language == "AUTO" else language.lower(),
                "-t",
                str(threads),
                "-oj",
                "-of",
                str(output_base),
                "-pp",
            ]

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            if result.returncode != 0:
                self._logger.error(
                    "WHISPER.CPP RETURN CODE %s\nSTDOUT:\n%s\nSTDERR:\n%s",
                    result.returncode,
                    result.stdout,
                    result.stderr,
                )
                raise RuntimeError(
                    "WHISPER.CPP NO PUDO COMPLETAR LA TRANSCRIPCIÓN."
                )

            json_path = output_base.with_suffix(".json")
            if not json_path.exists():
                raise RuntimeError("WHISPER.CPP NO GENERÓ EL RESULTADO JSON.")

            conversation = self._parse_json(
                json_path=json_path,
                source_path=audio_path,
                uppercase=uppercase,
                show_timestamps=show_timestamps,
            )

            if progress_callback:
                progress_callback(100, "TRANSCRIPCIÓN FINALIZADA.")

            return conversation
        finally:
            wav_path.unlink(missing_ok=True)
            output_base.with_suffix(".json").unlink(missing_ok=True)

    def _parse_json(
        self,
        json_path: Path,
        source_path: Path,
        uppercase: bool,
        show_timestamps: bool,
    ) -> Conversation:
        payload = json.loads(json_path.read_text(encoding="utf-8", errors="replace"))
        language = str(
            payload.get("result", {}).get("language")
            or payload.get("language")
            or "DESCONOCIDO"
        ).upper()

        raw_segments = (
            payload.get("transcription")
            or payload.get("segments")
            or payload.get("result", {}).get("segments")
            or []
        )

        segments: list[Segment] = []
        for raw in raw_segments:
            text = str(raw.get("text", "")).strip()
            if not text:
                continue
            if uppercase:
                text = text.upper()

            start, end = self._extract_times(raw)
            if show_timestamps:
                text = f"[{self._format_time(start)}] {text}"

            segments.append(
                Segment(
                    start=start,
                    end=end,
                    text=text,
                )
            )

        if not segments:
            fallback_text = str(payload.get("text", "")).strip()
            if uppercase:
                fallback_text = fallback_text.upper()
            if fallback_text:
                segments.append(Segment(0.0, 0.0, fallback_text))

        return Conversation(
            source_path=str(source_path),
            language=language,
            segments=segments,
        )

    @staticmethod
    def _extract_times(raw: dict) -> tuple[float, float]:
        offsets = raw.get("offsets", {})
        start = offsets.get("from", raw.get("start", 0))
        end = offsets.get("to", raw.get("end", 0))

        def normalize(value: object) -> float:
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return 0.0
            # whisper.cpp JSON offsets are commonly expressed in milliseconds.
            return numeric / 1000.0 if numeric > 100 else numeric

        return normalize(start), normalize(end)

    @staticmethod
    def _format_time(seconds: float) -> str:
        total = max(0, int(seconds))
        minutes, secs = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
