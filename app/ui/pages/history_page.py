from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
)

from app.services.history_service import HistoryService
from app.ui.pages.common import create_page_header


class HistoryPage(QFrame):
    status_changed = Signal(str)
    open_requested = Signal(dict)

    def __init__(self, history_service: HistoryService) -> None:
        super().__init__()
        self._history_service = history_service
        self._entries: list[dict] = []

        page, layout = create_page_header(
            "Historial",
            "Revisa, recupera o elimina transcripciones anteriores.",
        )

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        actions = QHBoxLayout()
        refresh = QPushButton("ACTUALIZAR")
        refresh.setObjectName("SecondaryButton")
        refresh.clicked.connect(self.refresh)

        self._open_button = QPushButton("ABRIR EN ARCHIVOS")
        self._open_button.setObjectName("PrimaryButton")
        self._open_button.setEnabled(False)
        self._open_button.clicked.connect(self._open_selected)

        self._delete_button = QPushButton("ELIMINAR REGISTRO")
        self._delete_button.setObjectName("SecondaryButton")
        self._delete_button.setEnabled(False)
        self._delete_button.clicked.connect(self._delete_selected)

        clear = QPushButton("VACIAR HISTORIAL")
        clear.setObjectName("SecondaryButton")
        clear.clicked.connect(self._clear_history)

        actions.addWidget(refresh)
        actions.addWidget(self._open_button)
        actions.addWidget(self._delete_button)
        actions.addStretch(1)
        actions.addWidget(clear)

        splitter = QSplitter()
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._show_entry)

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setPlaceholderText(
            "SELECCIONA UNA TRANSCRIPCIÓN DEL HISTORIAL."
        )

        splitter.addWidget(self._list)
        splitter.addWidget(self._preview)
        splitter.setSizes([360, 650])

        card_layout.addLayout(actions)
        card_layout.addWidget(splitter)

        layout.addWidget(card)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page)

        self.refresh()

    def refresh(self) -> None:
        self._entries = self._history_service.list_entries()
        self._list.clear()
        for entry in self._entries:
            created = entry.get("created_at", "")
            try:
                date_text = datetime.fromisoformat(created).strftime(
                    "%d-%m-%Y %H:%M"
                )
            except ValueError:
                date_text = created
            name = entry.get("source_name", "SIN NOMBRE")
            profile = entry.get("profile", "")
            item = QListWidgetItem(
                f"{name}\n{date_text} · {profile}"
            )
            self._list.addItem(item)

        self._preview.clear()
        self._open_button.setEnabled(False)
        self._delete_button.setEnabled(False)
        self.status_changed.emit(
            f"HISTORIAL: {len(self._entries)} REGISTROS"
        )

    def _show_entry(self, row: int) -> None:
        valid = 0 <= row < len(self._entries)
        self._open_button.setEnabled(valid)
        self._delete_button.setEnabled(valid)
        if not valid:
            self._preview.clear()
            return
        self._preview.setPlainText(
            str(self._entries[row].get("text", ""))
        )

    def _open_selected(self) -> None:
        row = self._list.currentRow()
        if 0 <= row < len(self._entries):
            self.open_requested.emit(self._entries[row])

    def _delete_selected(self) -> None:
        row = self._list.currentRow()
        if not 0 <= row < len(self._entries):
            return
        answer = QMessageBox.question(
            self,
            "ELIMINAR REGISTRO",
            "¿DESEAS ELIMINAR ESTA TRANSCRIPCIÓN DEL HISTORIAL?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._history_service.delete_entry(
            self._entries[row].get("id", "")
        )
        self.refresh()

    def _clear_history(self) -> None:
        if not self._entries:
            return
        answer = QMessageBox.question(
            self,
            "VACIAR HISTORIAL",
            "¿DESEAS ELIMINAR TODO EL HISTORIAL?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._history_service.clear()
        self.refresh()
