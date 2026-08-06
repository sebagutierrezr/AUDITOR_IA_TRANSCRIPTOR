import logging
import shutil
import tempfile
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path


DownloadCallback = Callable[[int, str], None]


class DownloadService:
    USER_AGENT = "AUDITOR-IA-TRANSCRIPTOR/0.2"

    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    def download_file(
        self,
        url: str,
        destination: Path,
        callback: DownloadCallback | None = None,
    ) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".part")

        request = urllib.request.Request(
            url,
            headers={"User-Agent": self.USER_AGENT},
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                total = int(response.headers.get("Content-Length", "0"))
                downloaded = 0
                with temporary.open("wb") as target:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        target.write(chunk)
                        downloaded += len(chunk)
                        if callback and total > 0:
                            percent = min(100, int(downloaded * 100 / total))
                            callback(percent, f"DESCARGANDO: {percent} %")

            temporary.replace(destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            self._logger.exception("FALLO LA DESCARGA: %s", url)
            raise

    def download_and_extract_zip(
        self,
        url: str,
        destination: Path,
        callback: DownloadCallback | None = None,
    ) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as temp_dir:
            archive = Path(temp_dir) / "package.zip"
            self.download_file(url, archive, callback)
            if callback:
                callback(100, "EXTRAYENDO MOTOR...")
            with zipfile.ZipFile(archive, "r") as zip_file:
                zip_file.extractall(destination)
