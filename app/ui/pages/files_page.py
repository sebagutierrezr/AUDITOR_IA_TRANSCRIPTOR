from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.services.config_service import ConfigService
from app.services.export_service import ExportService
from app.services.history_service import HistoryService
from app.services.openai_key_service import OpenAIKeyService
from app.ui.pages.common import create_page_header
from app.ui.widgets.drop_zone import DropZone
from app.workers.transcription_worker import TranscriptionWorker


class FilesPage(QWidget):
    status_changed = Signal(str)
    history_changed = Signal()

    SUPPORTED = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg"}
    MAX_MB = 25.0

    def __init__(self, config_service: ConfigService, parent=None) -> None:
        super().__init__(parent)
        self._config = config_service
        self._history = HistoryService()
        self._export = ExportService()
        self._key_service = OpenAIKeyService()
        self._audio_path: Path | None = None
        self._current_history_id: str | None = None
        self._thread: QThread | None = None
        self._worker: TranscriptionWorker | None = None

        page, layout = create_page_header(
            "TRANSCRIBIR",
            "Alta precisión para entrevistas: transcripción y separación de hablantes en una sola operación.",
        )

        top_card = QFrame()
        top_card.setObjectName("Card")
        top_layout = QVBoxLayout(top_card)
        top_layout.setContentsMargins(22, 22, 22, 22)
        top_layout.setSpacing(14)

        self.drop_zone = DropZone()
        self.drop_zone.file_dropped.connect(self._set_file)
        top_layout.addWidget(self.drop_zone)

        actions = QHBoxLayout()
        self.select_btn = QPushButton("SELECCIONAR ARCHIVO")
        self.select_btn.setObjectName("SecondaryButton")
        self.select_btn.clicked.connect(self._choose_file)

        self.file_label = QLabel("NINGÚN ARCHIVO SELECCIONADO")
        self.file_label.setObjectName("FileName")
        self.file_label.setWordWrap(True)

        self.transcribe_btn = QPushButton("TRANSCRIBIR")
        self.transcribe_btn.setObjectName("PrimaryButton")
        self.transcribe_btn.clicked.connect(self._start)

        actions.addWidget(self.select_btn)
        actions.addWidget(self.file_label, 1)
        actions.addWidget(self.transcribe_btn)
        top_layout.addLayout(actions)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress_label = QLabel("LISTO")
        self.progress_label.setObjectName("Muted")
        top_layout.addWidget(self.progress)
        top_layout.addWidget(self.progress_label)

        layout.addWidget(top_card)

        transcript_card = QFrame()
        transcript_card.setObjectName("Card")
        transcript_layout = QVBoxLayout(transcript_card)
        transcript_layout.setContentsMargins(22, 22, 22, 22)
        transcript_layout.setSpacing(12)

        heading_row = QHBoxLayout()
        transcript_title = QLabel("TRANSCRIPCIÓN")
        transcript_title.setObjectName("SectionTitle")
        self.quality_badge = QLabel("SIN PROCESAR")
        self.quality_badge.setObjectName("BadgeNeutral")
        heading_row.addWidget(transcript_title)
        heading_row.addStretch()
        heading_row.addWidget(self.quality_badge)
        transcript_layout.addLayout(heading_row)

        self.editor = QPlainTextEdit()
        self.editor.setObjectName("TranscriptEditor")
        self.editor.setPlaceholderText("La transcripción aparecerá aquí...")
        self.editor.textChanged.connect(self._persist_edit)
        transcript_layout.addWidget(self.editor, 1)

        manual_row = QHBoxLayout()
        agent_btn = QPushButton("MARCAR AGENTE")
        agent_btn.setObjectName("AgentButton")
        agent_btn.clicked.connect(lambda: self._relabel_current_line("AGENTE"))
        client_btn = QPushButton("MARCAR CLIENTE")
        client_btn.setObjectName("ClientButton")
        client_btn.clicked.connect(lambda: self._relabel_current_line("CLIENTE"))
        manual_row.addWidget(agent_btn)
        manual_row.addWidget(client_btn)
        manual_row.addStretch()
        transcript_layout.addLayout(manual_row)

        export_row = QHBoxLayout()
        copy_btn = QPushButton("COPIAR")
        copy_btn.clicked.connect(self._copy)
        txt_btn = QPushButton("EXPORTAR TXT")
        txt_btn.clicked.connect(self._export_txt)
        word_btn = QPushButton("EXPORTAR WORD")
        word_btn.clicked.connect(self._export_word)
        clear_btn = QPushButton("LIMPIAR")
        clear_btn.setObjectName("DangerGhostButton")
        clear_btn.clicked.connect(self._clear)
        for btn in (copy_btn, txt_btn, word_btn):
            btn.setObjectName("SecondaryButton")
            export_row.addWidget(btn)
        export_row.addStretch()
        export_row.addWidget(clear_btn)
        transcript_layout.addLayout(export_row)

        layout.addWidget(transcript_card, 1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page)

    def refresh(self) -> None:
        pass

    def _choose_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar audio",
            "",
            "Audio (*.mp3 *.mp4 *.mpeg *.mpga *.m4a *.wav *.webm *.ogg);;Todos (*.*)",
            options=QFileDialog.Option.DontUseNativeDialog,
        )
        if path:
            self._set_file(path)

    def _set_file(self, path: str) -> None:
        candidate = Path(path)
        if not candidate.is_file():
            QMessageBox.warning(self, "Archivo", "EL ARCHIVO NO EXISTE.")
            return
        if candidate.suffix.lower() not in self.SUPPORTED:
            QMessageBox.warning(self, "Formato", "FORMATO DE AUDIO NO COMPATIBLE.")
            return
        size_mb = candidate.stat().st_size / (1024 * 1024)
        if size_mb > self.MAX_MB:
            QMessageBox.warning(
                self,
                "Archivo demasiado grande",
                f"EL ARCHIVO PESA {size_mb:.1f} MB. EL LÍMITE ACTUAL ES {self.MAX_MB:.0f} MB.",
            )
            return
        self._audio_path = candidate
        self._current_history_id = None
        self.file_label.setText(f"{candidate.name}  ·  {size_mb:.1f} MB")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress_label.setText("LISTO PARA TRANSCRIBIR")
        self.quality_badge.setText("ALTA PRECISIÓN")
        self.quality_badge.setObjectName("BadgeReady")
        self.quality_badge.style().unpolish(self.quality_badge)
        self.quality_badge.style().polish(self.quality_badge)

    def _start(self) -> None:
        if self._thread is not None:
            return
        if self._audio_path is None:
            QMessageBox.information(self, "Archivo", "SELECCIONA PRIMERO UN ARCHIVO DE AUDIO.")
            return

        api_key = self._key_service.get_key()
        if not api_key:
            QMessageBox.warning(
                self,
                "Configura la API",
                "FALTA LA API KEY. VE A AJUSTES, GUÁRDALA Y VALIDA LA CONEXIÓN.",
            )
            return

        settings = self._config.load()
        self._set_busy(True)
        self.editor.clear()
        self.quality_badge.setText("PROCESANDO")
        self.progress.setRange(0, 0)
        self.progress_label.setText("ENVIANDO AUDIO A ALTA PRECISIÓN...")
        self.status_changed.emit("PROCESANDO AUDIO")

        self._thread = QThread(self)
        self._worker = TranscriptionWorker(
            audio_path=self._audio_path,
            settings=settings,
            api_key=api_key,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.completed.connect(self._on_completed)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._thread_finished)
        self._thread.start()

    def _on_progress(self, value: int, message: str) -> None:
        if value < 0:
            self.progress.setRange(0, 0)
        else:
            if self.progress.maximum() == 0:
                self.progress.setRange(0, 100)
            self.progress.setValue(max(0, min(100, value)))
        self.progress_label.setText(message)
        self.status_changed.emit(message)

    def _on_completed(self, conversation) -> None:
        self.editor.blockSignals(True)
        self.editor.setPlainText(conversation.text)
        self.editor.blockSignals(False)

        count = int(getattr(conversation, "speaker_count", 0) or 0)
        confidence = float(getattr(conversation, "role_confidence", 0.0) or 0.0)
        warning = str(getattr(conversation, "warning", "") or "").strip()

        if count >= 2:
            self.quality_badge.setText(f"{count} HABLANTES · ROLES {confidence:.0%}")
            self.quality_badge.setObjectName("BadgeSuccess")
        else:
            self.quality_badge.setText("REVISAR HABLANTES")
            self.quality_badge.setObjectName("BadgeWarning")
        self.quality_badge.style().unpolish(self.quality_badge)
        self.quality_badge.style().polish(self.quality_badge)

        if self._audio_path is not None:
            entry = self._history.add_entry(
                source_path=str(self._audio_path),
                text=conversation.text,
                profile="ALTA PRECISIÓN",
                language=conversation.language,
            )
            self._current_history_id = entry.get("id")
            self.history_changed.emit()

        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.progress_label.setText("TRANSCRIPCIÓN FINALIZADA")
        self.status_changed.emit("TRANSCRIPCIÓN FINALIZADA")
        self._set_busy(False)

        if warning:
            QMessageBox.information(self, "Resultado", warning)

    def _on_failed(self, message: str) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress_label.setText("NO SE PUDO COMPLETAR")
        self.quality_badge.setText("ERROR")
        self.quality_badge.setObjectName("BadgeWarning")
        self.quality_badge.style().unpolish(self.quality_badge)
        self.quality_badge.style().polish(self.quality_badge)
        self.status_changed.emit("ERROR DE TRANSCRIPCIÓN")
        self._set_busy(False)
        QMessageBox.critical(self, "Transcripción", message)

    def _thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        self.transcribe_btn.setEnabled(not busy)
        self.select_btn.setEnabled(not busy)
        self.transcribe_btn.setText("PROCESANDO..." if busy else "TRANSCRIBIR")

    def _relabel_current_line(self, role: str) -> None:
        text = self.editor.toPlainText()
        if not text.strip():
            return
        cursor = self.editor.textCursor()
        block = cursor.block()
        line = block.text()
        if not line.strip():
            return

        settings = self._config.load()
        label = settings.speaker_one_label if role == "AGENTE" else settings.speaker_two_label
        prefix_match = re.match(r"^(\s*\[[^\]]+\]\s*)?([^:\n]{1,50}:\s*)?(.*)$", line)
        if not prefix_match:
            return
        timestamp = prefix_match.group(1) or ""
        body = prefix_match.group(3).strip()
        replacement = f"{timestamp}{label}: {body}"

        block_cursor = QTextCursor(block)
        block_cursor.select(QTextCursor.SelectionType.BlockUnderCursor)
        block_cursor.insertText(replacement)
        self._persist_edit()

    def _persist_edit(self) -> None:
        if self._current_history_id:
            self._history.update_text(self._current_history_id, self.editor.toPlainText())

    def _copy(self) -> None:
        text = self.editor.toPlainText().strip()
        if text:
            QApplication.clipboard().setText(text)
            self.status_changed.emit("TRANSCRIPCIÓN COPIADA")

    def _export_txt(self) -> None:
        text = self.editor.toPlainText().strip()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar TXT", "transcripcion.txt", "Texto (*.txt)")
        if path:
            self._export.export_txt(Path(path), text)
            self.status_changed.emit("TXT EXPORTADO")

    def _export_word(self) -> None:
        text = self.editor.toPlainText().strip()
        if not text:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Word", "transcripcion.docx", "Word (*.docx)")
        if path:
            source = self._audio_path.name if self._audio_path else ""
            self._export.export_docx(Path(path), text, source)
            self.status_changed.emit("WORD EXPORTADO")

    def _clear(self) -> None:
        self.editor.clear()
        self._audio_path = None
        self._current_history_id = None
        self.file_label.setText("NINGÚN ARCHIVO SELECCIONADO")
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress_label.setText("LISTO")
        self.quality_badge.setText("SIN PROCESAR")
        self.status_changed.emit("LISTO")

    def load_history_entry(self, entry: dict) -> None:
        self._current_history_id = entry.get("id")
        source = entry.get("source_path", "")
        self._audio_path = Path(source) if source else None
        self.file_label.setText(entry.get("source_name", "HISTORIAL"))
        self.editor.blockSignals(True)
        self.editor.setPlainText(entry.get("text", ""))
        self.editor.blockSignals(False)
        self.quality_badge.setText("CARGADO DEL HISTORIAL")
        self.progress_label.setText("EDICIÓN DISPONIBLE")
