from pathlib import Path
import sys

from PySide6.QtCore import Qt
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
from app.ui.pages.live_page import LivePage
from app.ui.pages.history_page import HistoryPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.styles import APP_STYLE


class MainWindow(QMainWindow):
    def __init__(
        self,
        config_service: ConfigService,
    ):
        super().__init__()

        self._config_service = config_service
        self._history_service = HistoryService()
        self._engine = FasterWhisperEngine("ALTA")

        self.setWindowTitle(
            "AUDITOR IA - TRANSCRIPTOR"
        )
        self.setMinimumSize(1100, 700)
        self.resize(1360, 840)
        self.setStyleSheet(APP_STYLE)

        resource_root = (
            Path(getattr(sys, "_MEIPASS"))
            if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parents[2]
        )

        icon = resource_root / "resources" / "logo.svg"
        self.setWindowIcon(QIcon(str(icon)))

        self._stack = QStackedWidget()
        self._build(icon)

    def _build(self, icon: Path) -> None:
        central = QWidget()
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(215)

        side = QVBoxLayout(sidebar)
        side.setContentsMargins(18, 22, 18, 20)
        side.setSpacing(8)

        logo = QLabel()
        logo.setPixmap(
            QPixmap(str(icon)).scaled(
                46,
                46,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        brand = QLabel("AUDITOR IA")
        brand.setObjectName("BrandTitle")

        version = QLabel(
            "TRANSCRIPTOR · 7.1.3"
        )
        version.setObjectName("BrandVersion")

        side.addWidget(logo)
        side.addWidget(brand)
        side.addWidget(version)
        side.addSpacing(20)

        self._files_page = FilesPage(
            self._config_service,
            self._engine,
            self._history_service,
        )
        self._live_page = LivePage(
            self._config_service,
            self._engine,
            self._history_service,
        )
        self._history_page = HistoryPage(
            self._history_service
        )
        self._settings_page = SettingsPage(
            self._config_service
        )

        self._files_page.history_changed.connect(
            self._history_page.refresh
        )
        self._live_page.history_changed.connect(
            self._history_page.refresh
        )
        self._history_page.open_requested.connect(
            self._open_history_entry
        )
        self._settings_page.profile_changed.connect(
            self._engine.set_profile
        )

        self._status = QLabel("Listo")
        self._status.setObjectName("SidebarStatus")

        self._files_page.status_changed.connect(
            self._set_status
        )
        self._live_page.status_changed.connect(
            self._set_status
        )
        self._history_page.status_changed.connect(
            self._set_status
        )
        self._settings_page.status_changed.connect(
            self._set_status
        )

        pages = [
            ("Transcribir", self._files_page),
            ("En vivo", self._live_page),
            ("Historial", self._history_page),
            ("Ajustes", self._settings_page),
        ]

        self._buttons = []

        for index, (name, page) in enumerate(pages):
            button = QPushButton(name)
            button.setObjectName("NavButton")
            button.setCheckable(True)
            button.clicked.connect(
                lambda checked=False, i=index:
                self._select(i)
            )

            self._buttons.append(button)
            side.addWidget(button)
            self._stack.addWidget(page)

        side.addStretch()

        local_badge = QLabel(
            "100 % local\nSin API · Sin pagos"
        )
        local_badge.setObjectName("SidebarFooter")

        side.addWidget(self._status)
        side.addWidget(local_badge)

        content = QWidget()
        content.setObjectName("ContentArea")

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(self._stack)

        root.addWidget(sidebar)
        root.addWidget(content, 1)

        self.setCentralWidget(central)
        self._select(0)

    def _select(self, index: int) -> None:
        self._stack.setCurrentIndex(index)

        for i, button in enumerate(self._buttons):
            button.setChecked(i == index)

        if index == 1:
            self._live_page.refresh_labels()
        elif index == 2:
            self._history_page.refresh()

    def _open_history_entry(
        self,
        entry: dict,
    ) -> None:
        self._files_page.load_history_entry(entry)
        self._select(0)

    def _set_status(self, message: str) -> None:
        clean = (message or "Listo").strip()
        self._status.setText(clean[:48])
