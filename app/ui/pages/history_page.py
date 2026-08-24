from __future__ import annotations

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
    QWidget,
)

from app.services.history_service import HistoryService
from app.ui.pages.common import create_page_header


class HistoryPage(QWidget):
    open_entry = Signal(dict)
    status_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._service = HistoryService()
        self._entries: list[dict] = []

        page, layout = create_page_header(
            "HISTORIAL",
            "Revisa, recupera o elimina las transcripciones procesadas.",
        )

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)

        splitter = QSplitter()
        self.list_widget = QListWidget()
        self.list_widget.currentRowChanged.connect(self._preview)
        self.list_widget.itemDoubleClicked.connect(lambda _: self._open())

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(16, 0, 0, 0)
        self.meta = QLabel("Selecciona una transcripción")
        self.meta.setObjectName("SectionTitle")
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setObjectName("HistoryPreview")

        buttons = QHBoxLayout()
        open_btn = QPushButton("ABRIR")
        open_btn.setObjectName("PrimaryButton")
        open_btn.clicked.connect(self._open)
        delete_btn = QPushButton("ELIMINAR")
        delete_btn.setObjectName("DangerGhostButton")
        delete_btn.clicked.connect(self._delete)
        buttons.addWidget(open_btn)
        buttons.addWidget(delete_btn)
        buttons.addStretch()

        right_layout.addWidget(self.meta)
        right_layout.addWidget(self.preview, 1)
        right_layout.addLayout(buttons)

        splitter.addWidget(self.list_widget)
        splitter.addWidget(right)
        splitter.setSizes([340, 760])
        card_layout.addWidget(splitter)
        layout.addWidget(card, 1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page)
        self.refresh()

    def refresh(self) -> None:
        self._entries = self._service.list_entries()
        self.list_widget.clear()
        for entry in self._entries:
            raw = entry.get("created_at", "")
            try:
                date = datetime.fromisoformat(raw).strftime("%d-%m-%Y  %H:%M")
            except Exception:
                date = raw
            item = QListWidgetItem(f"{entry.get('source_name', 'Audio')}\n{date}")
            self.list_widget.addItem(item)
        if self._entries:
            self.list_widget.setCurrentRow(0)
        else:
            self.meta.setText("Sin transcripciones guardadas")
            self.preview.clear()

    def _preview(self, row: int) -> None:
        if row < 0 or row >= len(self._entries):
            return
        entry = self._entries[row]
        self.meta.setText(
            f"{entry.get('source_name', '')}  ·  {entry.get('profile', '')}  ·  {entry.get('language', '')}"
        )
        self.preview.setPlainText(entry.get("text", ""))

    def _open(self) -> None:
        row = self.list_widget.currentRow()
        if 0 <= row < len(self._entries):
            self.open_entry.emit(self._entries[row])

    def _delete(self) -> None:
        row = self.list_widget.currentRow()
        if not (0 <= row < len(self._entries)):
            return
        if QMessageBox.question(self, "Eliminar", "¿ELIMINAR ESTA TRANSCRIPCIÓN DEL HISTORIAL?") != QMessageBox.StandardButton.Yes:
            return
        self._service.delete_entry(self._entries[row].get("id", ""))
        self.status_changed.emit("TRANSCRIPCIÓN ELIMINADA")
        self.refresh()
