from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from app.services.config_service import ConfigService
from app.ui.pages.files_page import FilesPage
from app.ui.pages.history_page import HistoryPage
from app.ui.pages.settings_page import SettingsPage


class MainWindow(QMainWindow):
    VERSION = "7.0.0"

    def __init__(self, config_service: ConfigService) -> None:
        super().__init__()
        self._config = config_service
        self.setWindowTitle("AUDITOR IA - TRANSCRIPTOR")
        self.resize(1380, 860)
        self.setMinimumSize(1080, 700)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(214)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(12, 20, 12, 18)
        side.setSpacing(6)

        brand = QLabel("AUDITOR IA")
        brand.setObjectName("Brand")
        side.addWidget(brand)
        product = QLabel("TRANSCRIPTOR")
        product.setObjectName("Product")
        side.addWidget(product)

        online = QLabel("●  ALTA PRECISIÓN ONLINE")
        online.setObjectName("OnlineBadge")
        side.addWidget(online)
        side.addSpacing(18)

        self.stack = QStackedWidget()
        self.files_page = FilesPage(config_service)
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage(config_service)
        self.pages = [self.files_page, self.history_page, self.settings_page]
        for page in self.pages:
            self.stack.addWidget(page)

        nav = [
            ("TRANSCRIBIR", 0),
            ("HISTORIAL", 1),
            ("AJUSTES", 2),
        ]
        self.nav_buttons = []
        for text, index in nav:
            btn = QPushButton(text)
            btn.setObjectName("NavButton")
            btn.setProperty("active", index == 0)
            btn.clicked.connect(lambda checked=False, i=index: self.navigate(i))
            side.addWidget(btn)
            self.nav_buttons.append(btn)

        side.addStretch()
        version = QLabel(f"VERSIÓN {self.VERSION}\nWINDOWS INSTALLER")
        version.setObjectName("Version")
        side.addWidget(version)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.stack, 1)

        status = QStatusBar()
        status.setSizeGripEnabled(False)
        self.status_label = QLabel("LISTO")
        status.addWidget(self.status_label)
        self.setStatusBar(status)

        self.files_page.status_changed.connect(self._set_status)
        self.files_page.history_changed.connect(self.history_page.refresh)
        self.history_page.status_changed.connect(self._set_status)
        self.history_page.open_entry.connect(self._open_history)
        self.settings_page.status_changed.connect(self._set_status)

    def navigate(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setProperty("active", i == index)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        page = self.pages[index]
        if hasattr(page, "refresh"):
            page.refresh()

    def _open_history(self, entry: dict) -> None:
        self.files_page.load_history_entry(entry)
        self.navigate(0)
        self._set_status("TRANSCRIPCIÓN CARGADA DESDE HISTORIAL")

    def _set_status(self, message: str) -> None:
        self.status_label.setText(message)
