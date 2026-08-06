from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from app.services.config_service import ConfigService
from app.services.history_service import HistoryService
from app.ui.pages.common import create_page_header


class HomePage(QFrame):
    open_files_requested = Signal()
    open_live_requested = Signal()
    open_history_requested = Signal()

    def __init__(
        self,
        config_service: ConfigService,
        history_service: HistoryService,
    ) -> None:
        super().__init__()
        self._config_service = config_service
        self._history_service = history_service

        page, layout = create_page_header(
            "AUDITOR IA",
            "ACCESOS RÁPIDOS Y ESTADO DEL TRANSCRIPTOR.",
        )

        actions = QFrame()
        actions.setObjectName("Card")
        action_layout = QVBoxLayout(actions)
        action_layout.setContentsMargins(24, 22, 24, 22)

        title = QLabel("¿QUÉ QUIERES HACER?")
        title.setObjectName("MetricValue")

        buttons = QHBoxLayout()
        files = QPushButton("TRANSCRIBIR ARCHIVO")
        files.setObjectName("PrimaryButton")
        files.clicked.connect(self.open_files_requested.emit)

        live = QPushButton("GRABAR EN VIVO")
        live.setObjectName("SecondaryButton")
        live.clicked.connect(self.open_live_requested.emit)

        history = QPushButton("ABRIR HISTORIAL")
        history.setObjectName("SecondaryButton")
        history.clicked.connect(self.open_history_requested.emit)

        buttons.addWidget(files)
        buttons.addWidget(live)
        buttons.addWidget(history)
        buttons.addStretch(1)

        action_layout.addWidget(title)
        action_layout.addLayout(buttons)
        layout.addWidget(actions)

        grid = QGridLayout()
        self._profile = self._metric(grid, 0, 0, "PERFIL ACTUAL")
        self._speakers = self._metric(grid, 0, 1, "HABLANTES")
        self._history = self._metric(
            grid, 1, 0, "TRANSCRIPCIONES GUARDADAS"
        )
        self._last = self._metric(grid, 1, 1, "ÚLTIMO ARCHIVO")
        layout.addLayout(grid)
        layout.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page)
        self.refresh()

    def _metric(
        self,
        grid: QGridLayout,
        row: int,
        column: int,
        title: str,
    ) -> QLabel:
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)

        label = QLabel(title)
        label.setObjectName("Muted")
        value = QLabel("--")
        value.setObjectName("MetricValue")
        value.setWordWrap(True)

        card_layout.addWidget(label)
        card_layout.addWidget(value)
        grid.addWidget(card, row, column)
        return value

    def refresh(self) -> None:
        settings = self._config_service.load()
        entries = self._history_service.list_entries()

        self._profile.setText(settings.file_profile)
        self._speakers.setText(
            f"{settings.speaker_one_label} / {settings.speaker_two_label}"
        )
        self._history.setText(str(len(entries)))
        self._last.setText(
            str(entries[0].get("source_name", "SIN NOMBRE"))
            if entries
            else "SIN TRANSCRIPCIONES"
        )
