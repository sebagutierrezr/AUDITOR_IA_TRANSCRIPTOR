import logging
import os
import threading
from pathlib import Path

from faster_whisper import WhisperModel

from app.engines.base_speech_engine import ProgressCallback, SpeechEngine
from app.models.conversation import Conversation, Segment
from app.services.paths_service import AppPaths


class FasterWhisperEngine(SpeechEngine):
    """Motor local para archivos y transcripción en vivo."""

    MODEL_MAP = {
        "RÁPIDO": "base",
        "BALANCEADO": "small",
        "PRECISO": "medium",
    }

    def __init__(self, profile: str = "BALANCEADO") -> None:
        self._profile = (
            profile if profile in self.MODEL_MAP else "BALANCEADO"
        )
        self._model_name = self.MODEL_MAP[self._profile]
        self._model: WhisperModel | None = None
        self._model_lock = threading.RLock()
        self._paths = AppPaths()
        self._logger = logging.getLogger(__name__)

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def profile(self) -> str:
        return self._profile

    def is_ready(self) -> bool:
        return True

    def set_profile(self, profile: str) -> None:
        normalized = (
            profile if profile in self.MODEL_MAP else "BALANCEADO"
        )
        new_name = self.MODEL_MAP[normalized]

        if new_name != self._model_name:
            self.release()

        self._profile = normalized
        self._model_name = new_name

    def _load_model(
        self,
        callback: ProgressCallback | None,
    ) -> WhisperModel:
        with self._model_lock:
            if self._model is not None:
                return self._model

            if callback:
                callback(
                    3,
                    f"CARGANDO MODELO {self._model_name.upper()}...",
                )

            available = max(
                1,
                os.cpu_count() or 2,
            )
            threads = max(
                1,
                min(
                    6,
                    available - 1,
                ),
            )

            self._model = WhisperModel(
                self._model_name,
                device="cpu",
                compute_type="int8",
                cpu_threads=threads,
                num_workers=1,
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
            None if language == "AUTO" else language.lower()
        )
        beam_size = 7 if self._model_name == "medium" else 5

        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language_code,
            task="transcribe",
            beam_size=beam_size,
            best_of=5,
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
            word_timestamps=False,
        )

        duration = float(
            getattr(info, "duration", 0.0) or 0.0
        )
        segments: list[Segment] = []

        for item in segments_iter:
            text = item.text.strip()
            if not text:
                continue

            if uppercase:
                text = text.upper()

            if show_timestamps:
                text = (
                    f"[{self._format_time(item.start)} - "
                    f"{self._format_time(item.end)}] {text}"
                )

            segments.append(
                Segment(
                    start=float(item.start),
                    end=float(item.end),
                    text=text,
                )
            )

            if progress_callback and duration > 0:
                ratio = min(float(item.end) / duration, 1.0)
                progress_callback(
                    10 + int(ratio * 79),
                    f"TRANSCRIBIENDO... {int(ratio * 100)} %",
                )

        if progress_callback:
            progress_callback(90, "TRANSCRIPCIÓN FINALIZADA")

        detected = str(
            getattr(info, "language", language_code or "AUTO")
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
        """
        Transcribe una frase completa del modo En vivo.

        No se utiliza initial_prompt porque, con señales débiles, Whisper podía
        devolver parte de esas instrucciones como si fueran conversación real.
        """
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

        beam_size = (
            5
            if self._model_name != "medium"
            else 7
        )

        segments_iter, info = model.transcribe(
            str(audio_path),
            language=language_code,
            task="transcribe",
            beam_size=beam_size,
            best_of=5,
            vad_filter=False,
            condition_on_previous_text=False,
            temperature=0.0,
            no_speech_threshold=0.58,
            compression_ratio_threshold=2.35,
            log_prob_threshold=-1.0,
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
            text = " ".join(
                item.text.strip().split()
            )

            if not text:
                continue

            lowered = text.lower()

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
        hours, remainder = divmod(
            total,
            3600,
        )
        minutes, secs = divmod(
            remainder,
            60,
        )

        if hours:
            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{secs:02d}"
            )

        return f"{minutes:02d}:{secs:02d}"
