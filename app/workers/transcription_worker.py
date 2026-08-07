from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from app.engines.base_speech_engine import SpeechEngine
from app.services.audio_conversion_service import AudioConversionService
from app.services.diarization_service import DiarizationService
from app.services.paths_service import AppPaths


class TranscriptionWorker(QObject):
    progress = Signal(int, str)
    completed = Signal(object)
    warning = Signal(str)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        engine: SpeechEngine,
        audio_path: Path,
        language: str,
        uppercase: bool,
        show_timestamps: bool,
        file_profile: str,
        diarization_enabled: bool,
        speaker_one_label: str,
        speaker_two_label: str,
        first_speaker_is_one: bool,
    ) -> None:
        super().__init__()
        self._engine = engine
        self._audio_path = audio_path
        self._language = language
        self._uppercase = uppercase
        self._show_timestamps = show_timestamps
        self._file_profile = file_profile
        self._diarization_enabled = diarization_enabled
        self._speaker_one_label = speaker_one_label
        self._speaker_two_label = speaker_two_label
        self._first_speaker_is_one = first_speaker_is_one
        self._converter = AudioConversionService(AppPaths())
        self._diarization = DiarizationService()
        self._logger = logging.getLogger(__name__)

    @Slot()
    def run(self) -> None:
        prepared_path: Path | None = None

        try:
            self.progress.emit(2, "VALIDANDO ARCHIVO...")

            prepared_path = self._converter.convert_to_mono_wav(
                self._audio_path,
                self.progress.emit,
            )

            set_profile = getattr(
                self._engine,
                "set_profile",
                None,
            )
            if callable(set_profile):
                set_profile(self._file_profile)

            self.progress.emit(20, "INICIANDO TRANSCRIPCIÓN...")

            conversation = self._engine.transcribe(
                prepared_path,
                self._language,
                self._uppercase,
                self._show_timestamps,
                self.progress.emit,
            )

            if not conversation.segments:
                raise RuntimeError(
                    "NO SE DETECTÓ VOZ EN EL ARCHIVO. "
                    "REVISA EL VOLUMEN Y QUE EL AUDIO SEA AUDIBLE."
                )

            if self._diarization_enabled:
                try:
                    self.progress.emit(
                        88,
                        "IDENTIFICANDO AGENTE Y CLIENTE...",
                    )
                    conversation = self._diarization.diarize(
                        conversation=conversation,
                        audio_path=prepared_path,
                        speaker_one_label=self._speaker_one_label,
                        speaker_two_label=self._speaker_two_label,
                        first_speaker_is_one=self._first_speaker_is_one,
                        progress_callback=self.progress.emit,
                    )
                except Exception as exc:
                    self._logger.exception(
                        "NO FUE POSIBLE IDENTIFICAR HABLANTES"
                    )
                    raise RuntimeError(
                        "LA TRANSCRIPCIÓN DE TEXTO TERMINÓ, PERO LA "
                        "IDENTIFICACIÓN AGENTE/CLIENTE FALLÓ. "
                        "NO SE ENTREGARÁ UNA TRANSCRIPCIÓN ETIQUETADA "
                        "DE FORMA INSEGURA.\n\n"
                        f"DETALLE: {type(exc).__name__}: {exc}"
                    ) from exc

            self.progress.emit(100, "TRANSCRIPCIÓN FINALIZADA")
            self.completed.emit(conversation)

        except Exception as exc:
            self._logger.exception("ERROR AL TRANSCRIBIR ARCHIVO")
            detail = str(exc).strip() or type(exc).__name__
            self.failed.emit(
                f"{type(exc).__name__}: {detail}"
            )

        finally:
            if prepared_path is not None:
                prepared_path.unlink(missing_ok=True)
            self.finished.emit()
