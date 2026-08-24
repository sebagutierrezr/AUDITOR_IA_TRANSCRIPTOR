from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app.services.config_service import ConfigService
from app.services.logging_service import configure_logging
from app.ui.main_window import MainWindow
from app.ui.styles import APP_STYLE


def run_app() -> int:
    configure_logging()
    logger = logging.getLogger(__name__)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("AUDITOR IA - TRANSCRIPTOR")
    app.setOrganizationName("AUDITOR IA")
    app.setStyleSheet(APP_STYLE)

    try:
        window = MainWindow(ConfigService())
        window.show()
        return app.exec()
    except Exception:
        logger.exception("ERROR CRÍTICO")
        QMessageBox.critical(
            None,
            "AUDITOR IA",
            "NO FUE POSIBLE INICIAR LA APLICACIÓN. REVISA EL ARCHIVO app.log EN LA CARPETA DE DATOS DEL USUARIO.",
        )
        raise
