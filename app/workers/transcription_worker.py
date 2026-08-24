from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from app.services.high_precision_transcription_service import (
    HighPrecisionTranscriptionService,
)


class TranscriptionWorker(QObject):
    progress = Signal(int, str)
    completed = Signal(object)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, audio_path: Path, api_key: str, settings) -> None:
        super().__init__()
        self.audio_path = audio_path
        self.api_key = api_key
        self.settings = settings
        self.service = HighPrecisionTranscriptionService()
        self.logger = logging.getLogger(__name__)

    @Slot()
    def run(self) -> None:
        try:
            conversation = self.service.transcribe(
                audio_path=self.audio_path,
                api_key=self.api_key,
                language=self.settings.language,
                uppercase=self.settings.uppercase,
                show_timestamps=self.settings.show_timestamps,
                agent_label=self.settings.speaker_one_label,
                client_label=self.settings.speaker_two_label,
                role_model=self.settings.role_model,
                agent_reference_path=self.settings.agent_reference_path,
                progress_callback=self.progress.emit,
            )
            self.completed.emit(conversation)
        except Exception as exc:
            self.logger.exception("ERROR EN TRANSCRIPCIÓN DE ALTA PRECISIÓN")
            self.failed.emit(f"{type(exc).__name__}: {exc}")
        finally:
            self.finished.emit()
