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
from app.services.system_profile_service import SystemProfileService
from app.version import APP_VERSION


class FasterWhisperEngine(SpeechEngine):
    """Motor local con modelos verificados dentro de la aplicación."""

    MODEL_MAP = {"ALTA": "small"}
    ECO_MODEL = "base"

    REQUIRED_MODEL_FILES = (
        "model.bin",
        "config.json",
        "tokenizer.json",
    )

    def __init__(self, profile: str = "ALTA", performance_mode: str = "AUTO") -> None:
        self._paths = AppPaths()
        self._profile = (
            profile
            if profile in self.MODEL_MAP
            else "ALTA"
        )
        self._model: WhisperModel | None = None
        self._model_lock = threading.RLock()
        self._logger = logging.getLogger(__name__)
        self._performance_mode = performance_mode
        self._system_profile = SystemProfileService.detect(performance_mode)
        self._model_name = self._desired_model_name()

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def profile(self) -> str:
        return self._profile

    @property
    def model_path(self) -> Path:
        return self._paths.models / self._model_name

    def _desired_model_name(self) -> str:
        if self._system_profile.tuning.profile == "ECO":
            return self.ECO_MODEL
        return self.MODEL_MAP.get(self._profile, "small")

    def model_status(self) -> dict[str, bool]:
        return {
            "BASE": self._model_files_ready(self._paths.models / self.ECO_MODEL),
            "ALTA": self._model_files_ready(self._paths.models / "small"),
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
        normalized = profile if profile in self.MODEL_MAP else "ALTA"
        self._profile = normalized
        new_name = self._desired_model_name()
        if new_name != self._model_name:
            self.release()
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
                    f"REINSTALA AUDITOR IA {APP_VERSION}."
                )
                self._logger.error(message)
                raise RuntimeError(message)

            if callback:
                callback(
                    3,
                    f"VERIFICANDO MODELO "
                    f"{self._model_name.upper()}...",
                )

            # Perfil adaptativo: deja recursos libres para Windows y Qt.
            self._system_profile = SystemProfileService.detect(self._performance_mode)
            threads = self._system_profile.tuning.cpu_threads

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

    def warmup(self) -> None:
        """Carga el modelo sin bloquear la interfaz Qt."""
        self._load_model(None)

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
            beam_size=self._system_profile.tuning.file_beam_size,
            best_of=self._system_profile.tuning.file_beam_size,
            vad_filter=False,
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
            beam_size=self._system_profile.tuning.live_beam_size,
            best_of=self._system_profile.tuning.live_beam_size,
            vad_filter=True,
            vad_parameters={
                "min_silence_duration_ms": 260,
                "speech_pad_ms": 180,
            },
            condition_on_previous_text=False,
            temperature=0.0,
            no_speech_threshold=0.48,
            compression_ratio_threshold=2.20,
            log_prob_threshold=-0.85,

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
            "suscríbete",
            "suscribete",
            "suscríbete al canal",
            "suscribete al canal",
            "dale like",
            "activa la campanita",
        )

        segments: list[Segment] = []

        for item in segments_iter:
            text = item.text.strip()

            if not text:
                continue

            lowered = text.casefold()
            no_speech_prob = float(getattr(item, "no_speech_prob", 0.0) or 0.0)
            avg_logprob = float(getattr(item, "avg_logprob", 0.0) or 0.0)
            compression_ratio = float(getattr(item, "compression_ratio", 0.0) or 0.0)
            duration = max(0.0, float(item.end) - float(item.start))

            # En vivo preferimos omitir una frase dudosa antes que inventar
            # texto. Estos metadatos vienen del propio decoder de Whisper.
            if no_speech_prob >= 0.58:
                continue
            if avg_logprob < -0.92:
                continue
            if compression_ratio > 2.25:
                continue
            if duration < 0.45 and len(text.split()) <= 2:
                continue

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

    def set_performance_mode(self, mode: str) -> None:
        normalized = str(mode or "AUTO").upper()
        if normalized != self._performance_mode:
            old_model = self._model_name
            self._performance_mode = normalized
            self._system_profile = SystemProfileService.detect(normalized)
            new_model = self._desired_model_name()
            if new_model != old_model:
                self.release()
                self._model_name = new_model

    @property
    def system_profile(self):
        return self._system_profile

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
