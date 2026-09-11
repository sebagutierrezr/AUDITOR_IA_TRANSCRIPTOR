from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app.services.config_service import ConfigService
from app.services.logging_service import configure_logging
from app.services.paths_service import AppPaths
from app.ui.main_window import MainWindow
from app.version import APP_NAME, APP_VERSION


def run_app() -> int:
    configure_logging()
    logger = logging.getLogger(__name__)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("AUDITOR IA")

    try:
        window = MainWindow(ConfigService())
        window.show()
        return app.exec()
    except Exception as exc:
        logger.exception("ERROR CRITICO")
        log_path = AppPaths().logs / "app.log"
        QMessageBox.critical(
            None,
            "AUDITOR IA",
            "NO FUE POSIBLE INICIAR LA APLICACIÓN.\n\n"
            f"DETALLE: {type(exc).__name__}: {exc}\n\n"
            f"LOG: {log_path}",
        )
        return 1
