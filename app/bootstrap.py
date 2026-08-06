import logging
import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from app.services.logging_service import configure_logging
from app.services.config_service import ConfigService
from app.ui.main_window import MainWindow

def run_app():
    configure_logging()
    logger = logging.getLogger(__name__)
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("AUDITOR IA - TRANSCRIPTOR")
        window = MainWindow(ConfigService())
        window.show()
        sys.exit(app.exec())
    except Exception:
        logger.exception("ERROR CRITICO")
        QMessageBox.critical(None, "ERROR", "NO FUE POSIBLE INICIAR LA APLICACION. REVISE LA CARPETA LOGS.")
        raise
