from abc import ABC, abstractmethod
from collections.abc import Callable
from pathlib import Path

from app.models.conversation import Conversation


ProgressCallback = Callable[[int, str], None]


class SpeechEngine(ABC):
    @abstractmethod
    def is_ready(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        language: str,
        uppercase: bool,
        show_timestamps: bool,
        progress_callback: ProgressCallback | None = None,
    ) -> Conversation:
        raise NotImplementedError
