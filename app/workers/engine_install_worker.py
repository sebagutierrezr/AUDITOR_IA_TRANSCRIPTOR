import logging

from PySide6.QtCore import QObject, Signal, Slot

from app.services.engine_install_service import EngineInstallService


class EngineInstallWorker(QObject):
    progress = Signal(int, str)
    completed = Signal(str)
    failed = Signal(str)
    finished = Signal()

    def __init__(
        self,
        service: EngineInstallService,
        profile: str,
    ) -> None:
        super().__init__()
        self._service = service
        self._profile = profile
        self._logger = logging.getLogger(__name__)

    @Slot()
    def run(self) -> None:
        try:
            model_name = self._service.install(
                self._profile,
                self.progress.emit,
            )
            self.completed.emit(model_name)
        except Exception as exc:
            self._logger.exception("ERROR INSTALANDO EL MOTOR")
            self.failed.emit(str(exc))
        finally:
            self.finished.emit()
