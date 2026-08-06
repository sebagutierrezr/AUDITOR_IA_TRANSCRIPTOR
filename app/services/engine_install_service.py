import logging
import shutil
from pathlib import Path

from app.services.download_service import DownloadCallback, DownloadService
from app.services.paths_service import AppPaths


class EngineInstallService:
    # Versión fijada para obtener instalaciones reproducibles.
    WHISPER_CPP_VERSION = "v1.9.1"
    ENGINE_URL = (
        "https://github.com/ggml-org/whisper.cpp/releases/download/"
        f"{WHISPER_CPP_VERSION}/whisper-bin-x64.zip"
    )

    MODEL_URLS = {
        "RÁPIDO": (
            "ggml-tiny-q5_1.bin",
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"
            "ggml-tiny-q5_1.bin?download=true",
        ),
        "BALANCEADO": (
            "ggml-base-q5_1.bin",
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"
            "ggml-base-q5_1.bin?download=true",
        ),
        "PRECISO": (
            "ggml-small-q5_1.bin",
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/"
            "ggml-small-q5_1.bin?download=true",
        ),
    }

    def __init__(self, paths: AppPaths) -> None:
        self._paths = paths
        self._downloader = DownloadService()
        self._logger = logging.getLogger(__name__)

    def install(
        self,
        profile: str,
        callback: DownloadCallback | None = None,
    ) -> str:
        profile = profile if profile in self.MODEL_URLS else "BALANCEADO"
        model_name, model_url = self.MODEL_URLS[profile]

        if callback:
            callback(0, "DESCARGANDO MOTOR WHISPER.CPP...")

        self._paths.engines.mkdir(parents=True, exist_ok=True)
        self._downloader.download_and_extract_zip(
            self.ENGINE_URL,
            self._paths.engines,
            callback,
        )

        model_path = self._paths.models / model_name
        if not model_path.exists():
            if callback:
                callback(0, f"DESCARGANDO MODELO {profile}...")
            self._downloader.download_file(
                model_url,
                model_path,
                callback,
            )

        return model_name
