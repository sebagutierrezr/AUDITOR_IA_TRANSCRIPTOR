from pathlib import Path
import sys

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.engines.faster_whisper_engine import FasterWhisperEngine
from app.services.config_service import ConfigService
from app.services.history_service import HistoryService
from app.ui.pages.files_page import FilesPage
from app.ui.pages.history_page import HistoryPage
from app.ui.pages.home_page import HomePage
from app.ui.pages.live_page import LivePage
from app.ui.pages.settings_page import SettingsPage
from app.ui.styles import APP_STYLE


class MainWindow(QMainWindow):
    def __init__(self, config_service: ConfigService):
        super().__init__()
        self._config_service = config_service
        self._history_service = HistoryService()
        self._engine = FasterWhisperEngine(
            config_service.load().file_profile
        )

        self.setWindowTitle("AUDITOR IA - TRANSCRIPTOR")
        self.setMinimumSize(1100, 700)
        self.resize(1280, 780)
        self.setStyleSheet(APP_STYLE)

        resource_root = (
            Path(getattr(sys, "_MEIPASS"))
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parents[2]
        )
        icon = resource_root / "resources" / "logo.svg"
        self.setWindowIcon(QIcon(str(icon)))
        self._stack = QStackedWidget()
        self._status_label = QLabel("ESTADO: LISTO")
        self._performance_label = QLabel("CPU: -- % | RAM: -- MB")
        self._build(icon)
        self._start_monitor()

    def _build(self, icon: Path) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        side = QWidget()
        side.setObjectName("Sidebar")
        side.setFixedWidth(250)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(20, 22, 20, 22)
        side_layout.setSpacing(8)

        logo = QLabel()
        logo.setPixmap(
            QPixmap(str(icon)).scaled(
                54,
                54,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )
        side_layout.addWidget(logo)

        brand = QLabel("AUDITOR IA\nTRANSCRIPTOR")
        brand.setObjectName("BrandTitle")
        version = QLabel("VERSIÓN 6.1.0")
        version.setObjectName("BrandVersion")
        side_layout.addWidget(brand)
        side_layout.addWidget(version)
        side_layout.addSpacing(22)

        self._files_page = FilesPage(
            self._config_service,
            self._engine,
            self._history_service,
        )
        self._history_page = HistoryPage(self._history_service)
        self._live_page = LivePage(
            self._config_service,
            self._engine,
            self._history_service,
        )
        settings = SettingsPage(self._config_service)
        self._home_page = HomePage(
            self._config_service,
            self._history_service,
        )

        self._files_page.status_changed.connect(self._set_status)
        self._files_page.history_changed.connect(
            self._history_page.refresh
        )
        self._files_page.history_changed.connect(
            self._home_page.refresh
        )
        self._live_page.status_changed.connect(self._set_status)
        self._live_page.history_changed.connect(
            self._history_page.refresh
        )
        self._live_page.history_changed.connect(
            self._home_page.refresh
        )
        self._history_page.status_changed.connect(self._set_status)
        self._history_page.open_requested.connect(
            self._open_history_entry
        )
        settings.status_changed.connect(self._set_status)
        settings.profile_changed.connect(self._engine.set_profile)

        self._home_page.open_files_requested.connect(
            lambda: self._select(1)
        )
        self._home_page.open_history_requested.connect(
            lambda: self._select(2)
        )
        self._home_page.open_live_requested.connect(
            lambda: self._select(3)
        )

        pages = [
            ("INICIO", self._home_page),
            ("ARCHIVOS", self._files_page),
            ("HISTORIAL", self._history_page),
            ("EN VIVO", self._live_page),
            ("CONFIGURACIÓN", settings),
        ]

        self._buttons = []
        for index, (name, page) in enumerate(pages):
            button = QPushButton(name)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, page_index=index: self._select(
                    page_index
                )
            )
            self._buttons.append(button)
            side_layout.addWidget(button)
            self._stack.addWidget(page)

        side_layout.addStretch()

        content = QWidget()
        content.setObjectName("ContentArea")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self._stack)

        root.addWidget(side)
        root.addWidget(content, 1)
        self.setCentralWidget(central)
        self.statusBar().addWidget(self._status_label)
        self.statusBar().addPermanentWidget(
            self._performance_label
        )
        self._select(0)

    def _open_history_entry(self, entry: dict) -> None:
        self._files_page.load_history_entry(entry)
        self._select(1)

    def _select(self, index: int) -> None:
        if index == 0:
            self._home_page.refresh()
        if index == 3:
            self._live_page.refresh_labels()
        self._stack.setCurrentIndex(index)
        for button_index, button in enumerate(self._buttons):
            button.setChecked(button_index == index)

    def _set_status(self, message: str) -> None:
        self._status_label.setText(
            f"ESTADO: {message.upper()}"
        )

    def _start_monitor(self) -> None:
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)
        self._timer.start(1500)

    def _update(self) -> None:
        try:
            import os
            import psutil

            process = psutil.Process(os.getpid())
            self._performance_label.setText(
                f"CPU: {process.cpu_percent():.1f} % | "
                f"RAM: {process.memory_info().rss / (1024 * 1024):.0f} MB"
            )
        except Exception:
            self._performance_label.setText(
                "CPU: N/D | RAM: N/D"
            )
