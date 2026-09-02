import logging
import os
import threading
from pathlib import Path

from faster_whisper import WhisperModel

from app.engines.base_speech_engine import (
    ProgressCallback,
    SpeechEngine,
)
from app.models.conversation import Conversation, Segment
from app.services.paths_service import AppPaths


class FasterWhisperEngine(SpeechEngine):
    """Motor local con modelos verificados dentro de la aplicación."""

    MODEL_MAP = {"ALTA": "small"}

    REQUIRED_MODEL_FILES = (
        "model.bin",
        "config.json",
        "tokenizer.json",
    )

    def __init__(self, profile: str = "ALTA") -> None:
        self._paths = AppPaths()
        self._profile = (
            profile
            if profile in self.MODEL_MAP
            else "ALTA"
        )
        self._model_name = self.MODEL_MAP[self._profile]
        self._model: WhisperModel | None = None
        self._model_lock = threading.RLock()
        self._logger = logging.getLogger(__name__)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def profile(self) -> str:
        return self._profile

    @property
    def model_path(self) -> Path:
        return self._paths.models / self._model_name

    def model_status(self) -> dict[str, bool]:
        return {
            profile: self._model_files_ready(
                self._paths.models / model_name
            )
            for profile, model_name in self.MODEL_MAP.items()
        }

    def is_ready(self) -> bool:
        return self._model_files_ready(self.model_path)

    def readiness_message(self) -> str:
        status = self.model_status()
        ready = [
            profile
            for profile, available in status.items()
            if available
        ]
        missing = [
            profile
            for profile, available in status.items()
            if not available
        ]

        parts = []

        if ready:
            parts.append(
                "LISTOS: " + ", ".join(ready)
            )
        if missing:
            parts.append(
                "NO DISPONIBLES: " + ", ".join(missing)
            )

        return " · ".join(parts) or "SIN MODELOS"

    def set_profile(self, profile: str) -> None:
        normalized = (
            profile
            if profile in self.MODEL_MAP
            else "ALTA"
        )
        new_name = self.MODEL_MAP[normalized]

        if new_name != self._model_name:
            self.release()

        self._profile = normalized
        self._model_name = new_name

    def _model_files_ready(self, path: Path) -> bool:
        return all(
            (path / filename).is_file()
            and (path / filename).stat().st_size > 0
            for filename in self.REQUIRED_MODEL_FILES
        )

    def _load_model(
        self,
        callback: ProgressCallback | None,
    ) -> WhisperModel:
        with self._model_lock:
            if self._model is not None:
                return self._model

            if not self.is_ready():
                message = (
                    f"EL MODELO {self._model_name.upper()} "
                    "NO ESTÁ INSTALADO O ESTÁ INCOMPLETO. "
                    "REINSTALA AUDITOR IA 8.0.0."
                )
                self._logger.error(message)
                raise RuntimeError(message)

            if callback:
                callback(
                    3,
                    f"VERIFICANDO MODELO "
                    f"{self._model_name.upper()}...",
                )

            available = max(2, os.cpu_count() or 4)
            # Reservar CPU para Windows y la interfaz. La calidad no cambia.
            threads = max(
                2,
                min(4, available - 2),
            )

            if callback:
                callback(
                    5,
                    f"INICIANDO MODELO "
                    f"{self._model_name.upper()}...",
                )

            self._model = WhisperModel(
                str(self.model_path),
                device="cpu",
                compute_type="int8",
                cpu_threads=threads,
                num_workers=1,
                local_files_only=True,
            )

            if callback:
                callback(
                    7,
                    f"MODELO {self._model_name.upper()} LISTO",
                )

            return self._model

    def transcribe(
        self,
        audio_path: Path,
        language: str,
        uppercase: bool,
        show_timestamps: bool,
        progress_callback: ProgressCallback | None = None,
    ) -> Conversation:
        if not audio_path.exists():
            raise FileNotFoundError(
                "EL ARCHIVO SELECCIONADO NO EXISTE."
            )

        model = self._load_model(progress_callback)

        if progress_callback:
            progress_callback(8, "ANALIZANDO AUDIO...")

        language_code = (
            None
            if language == "AUTO"
            else language.lower()
        )

        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language_code,
            task="transcribe",
            beam_size=6,
            best_of=6,
            vad_filter=False,
            vad_parameters={
                "min_silence_duration_ms": 350,
                "speech_pad_ms": 250,
            },
            condition_on_previous_text=True,
            temperature=0.0,
            no_speech_threshold=0.55,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,

            # CLAVE SPEAKER V2:
            # conservar tiempos por palabra para que una frase de Whisper que
            # contenga a ambos participantes pueda separarse después.
            word_timestamps=True,
        )

        duration = float(
            getattr(info, "duration", 0.0) or 0.0
        )

        segments: list[Segment] = []

        for item in segments_iter:
            text = item.text.strip()

            if not text:
                continue

            raw_words = []
            for word in (getattr(item, "words", None) or []):
                word_text = str(
                    getattr(word, "word", "") or ""
                )
                if not word_text.strip():
                    continue

                if uppercase:
                    word_text = word_text.upper()

                raw_words.append(
                    {
                        "start": float(
                            getattr(word, "start", item.start)
                        ),
                        "end": float(
                            getattr(word, "end", item.end)
                        ),
                        "text": word_text,
                        "probability": float(
                            getattr(word, "probability", 0.0) or 0.0
                        ),
                    }
                )

            if uppercase:
                text = text.upper()

            display_text = text

            if show_timestamps:
                display_text = (
                    f"[{self._format_time(item.start)} - "
                    f"{self._format_time(item.end)}] {display_text}"
                )

            confidence = None
            if raw_words:
                probabilities = [
                    float(word["probability"])
                    for word in raw_words
                    if word.get("probability") is not None
                ]
                if probabilities:
                    confidence = sum(probabilities) / len(probabilities)

            segments.append(
                Segment(
                    start=float(item.start),
                    end=float(item.end),
                    text=display_text,
                    confidence=confidence,
                    words=raw_words,
                )
            )

            if progress_callback and duration > 0:
                ratio = min(
                    float(item.end) / duration,
                    1.0,
                )
                progress_callback(
                    10 + int(ratio * 79),
                    f"TRANSCRIBIENDO... "
                    f"{int(ratio * 100)} %",
                )

        if progress_callback:
            progress_callback(
                90,
                "TRANSCRIPCIÓN FINALIZADA",
            )

        detected = str(
            getattr(
                info,
                "language",
                language_code or "AUTO",
            )
        ).upper()

        return Conversation(
            source_path=str(audio_path),
            language=detected,
            segments=segments,
        )

    def transcribe_live(
        self,
        audio_path: Path,
        language: str,
        uppercase: bool,
    ) -> Conversation:
        if not audio_path.exists():
            raise FileNotFoundError(
                "EL FRAGMENTO DE AUDIO NO EXISTE."
            )

        model = self._load_model(None)

        language_code = (
            "es"
            if language in ("ES", "AUTO")
            else language.lower()
        )

        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language_code,
            task="transcribe",
            beam_size=6,
            best_of=6,
            vad_filter=False,
            condition_on_previous_text=False,
            temperature=0.0,
            no_speech_threshold=0.58,
            compression_ratio_threshold=2.35,
            log_prob_threshold=-1.0,

            # En vivo no necesita el coste adicional de alineación por palabra.
            word_timestamps=False,
        )

        forbidden_fragments = (
            "subtítulos por la comunidad",
            "subtitulos por la comunidad",
            "subtítulos realizados por",
            "subtitulos realizados por",
            "amara.org",
            "entrevista telefónica en español",
            "entrevista telefonica en español",
            "gracias por ver",
            "hasta la próxima",
            "hasta la proxima",
            "conciencia en español",
        )

        segments: list[Segment] = []

        for item in segments_iter:
            text = item.text.strip()

            if not text:
                continue

            lowered = text.casefold()

            if any(
                fragment in lowered
                for fragment in forbidden_fragments
            ):
                continue

            if uppercase:
                text = text.upper()

            segments.append(
                Segment(
                    start=float(item.start),
                    end=float(item.end),
                    text=text,
                )
            )

        detected = str(
            getattr(
                info,
                "language",
                language_code,
            )
        ).upper()

        return Conversation(
            source_path=str(audio_path),
            language=detected,
            segments=segments,
        )

    def release(self) -> None:
        with self._model_lock:
            self._model = None

    @staticmethod
    def _format_time(seconds: float) -> str:
        total = max(0, int(seconds))
        minutes, secs = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)

        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"

        return f"{minutes:02d}:{secs:02d}"
