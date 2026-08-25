from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from app.engines.faster_whisper_engine import FasterWhisperEngine
from app.models.conversation import Conversation
from app.services.config_service import ConfigService
from app.services.diarization_service import DiarizationService
from app.services.history_service import HistoryService
from app.services.speaker_rescue_service import SpeakerRescueService
from app.workers.export_worker import ExportWorker
from app.workers.transcription_worker import TranscriptionWorker


class DropZone(QFrame):
    file_dropped = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(5)

        title = QLabel("ARRASTRA AQUÍ EL AUDIO")
        title.setObjectName("DropTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("o selecciónalo desde tu equipo")
        subtitle.setObjectName("DropSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(subtitle)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls() and event.mimeData().urls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if path:
                self.file_dropped.emit(path)
        event.acceptProposedAction()


class FilesPage(QFrame):
    status_changed = Signal(str)
    history_changed = Signal()

    SUPPORTED_EXTENSIONS = {
        ".wav", ".mp3", ".m4a", ".flac", ".ogg",
        ".aac", ".wma", ".mp4", ".webm",
    }

    def __init__(
        self,
        config_service: ConfigService,
        engine: FasterWhisperEngine,
        history_service: HistoryService,
    ) -> None:
        super().__init__()
        self._config_service = config_service
        self._engine = engine
        self._history_service = history_service
        self._diarization = DiarizationService()
        self._rescue = SpeakerRescueService()

        self._selected_file: Path | None = None
        self._history_id: str | None = None
        self._thread = None
        self._worker = None
        self._export_thread = None
        self._export_worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 28)
        root.setSpacing(16)

        title = QLabel("Transcribir entrevista")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Procesamiento local · Faster-Whisper + doble verificación de hablantes"
        )
        subtitle.setObjectName("PageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        source_card = QFrame()
        source_card.setObjectName("Card")
        source_layout = QVBoxLayout(source_card)
        source_layout.setContentsMargins(20, 20, 20, 20)
        source_layout.setSpacing(12)

        self._drop_zone = DropZone()
        self._drop_zone.file_dropped.connect(lambda p: self._load_file(Path(p)))
        source_layout.addWidget(self._drop_zone)

        file_row = QHBoxLayout()
        self._select_button = QPushButton("Seleccionar archivo")
        self._select_button.setObjectName("SecondaryButton")
        self._select_button.clicked.connect(self._select_file)

        self._file_name = QLabel("Ningún archivo seleccionado")
        self._file_name.setObjectName("FileName")
        self._file_name.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self._transcribe_button = QPushButton("Transcribir")
        self._transcribe_button.setObjectName("PrimaryButton")
        self._transcribe_button.setEnabled(False)
        self._transcribe_button.clicked.connect(self._start_transcription)

        file_row.addWidget(self._select_button)
        file_row.addWidget(self._file_name, 1)
        file_row.addWidget(self._transcribe_button)
        source_layout.addLayout(file_row)

        self._file_detail = QLabel(
            "WAV, MP3, M4A, FLAC, OGG, AAC, WMA, MP4 y WEBM"
        )
        self._file_detail.setObjectName("Muted")
        source_layout.addWidget(self._file_detail)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("Listo")
        source_layout.addWidget(self._progress)
        root.addWidget(source_card)

        transcript_card = QFrame()
        transcript_card.setObjectName("Card")
        transcript_layout = QVBoxLayout(transcript_card)
        transcript_layout.setContentsMargins(20, 18, 20, 18)
        transcript_layout.setSpacing(10)

        header = QHBoxLayout()
        transcript_title = QLabel("Transcripción")
        transcript_title.setObjectName("SectionTitle")
        self._agent_button = QPushButton("Marcar Agente")
        self._agent_button.setObjectName("AgentButton")
        self._agent_button.clicked.connect(lambda: self._change_current_speaker(True))
        self._client_button = QPushButton("Marcar Cliente")
        self._client_button.setObjectName("ClientButton")
        self._client_button.clicked.connect(lambda: self._change_current_speaker(False))
        header.addWidget(transcript_title)
        header.addStretch()
        header.addWidget(self._agent_button)
        header.addWidget(self._client_button)
        transcript_layout.addLayout(header)

        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText("La transcripción aparecerá aquí.")
        self._editor.setMinimumHeight(360)
        self._editor.textChanged.connect(self._update_buttons)
        self._editor.selectionChanged.connect(self._update_buttons)
        transcript_layout.addWidget(self._editor, 1)

        actions = QHBoxLayout()
        self._txt_button = QPushButton("Exportar TXT")
        self._word_button = QPushButton("Exportar Word")
        self._update_history_button = QPushButton("Guardar cambios")
        self._clear_button = QPushButton("Limpiar")
        for button in (
            self._txt_button,
            self._word_button,
            self._update_history_button,
            self._clear_button,
        ):
            button.setObjectName("SecondaryButton")

        self._txt_button.clicked.connect(lambda: self._start_export("txt"))
        self._word_button.clicked.connect(lambda: self._start_export("docx"))
        self._update_history_button.clicked.connect(self._update_history)
        self._clear_button.clicked.connect(self._clear)
        actions.addWidget(self._txt_button)
        actions.addWidget(self._word_button)
        actions.addWidget(self._update_history_button)
        actions.addStretch()
        actions.addWidget(self._clear_button)
        transcript_layout.addLayout(actions)

        root.addWidget(transcript_card, 1)
        self._update_buttons()

    def _select_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar audio",
            "",
            "Audio (*.wav *.mp3 *.m4a *.flac *.ogg *.aac *.wma *.mp4 *.webm);;Todos (*.*)",
        )
        if path:
            self._load_file(Path(path))

    def _load_file(self, path: Path) -> None:
        if self._is_busy():
            return
        if not path.is_file() or path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            QMessageBox.warning(self, "Archivo", "Selecciona un archivo de audio compatible.")
            return

        self._selected_file = path
        self._history_id = None
        self._file_name.setText(path.name)
        size_mb = path.stat().st_size / (1024 * 1024)
        self._file_detail.setText(
            f"{path.suffix.lstrip('.').upper()} · {size_mb:.1f} MB · Alta precisión local"
        )
        self._progress.setValue(0)
        self._progress.setFormat("Archivo listo")
        self._update_buttons()

    def _start_transcription(self) -> None:
        if self._selected_file is None or self._is_busy():
            return

        settings = self._config_service.load()
        self._engine.set_profile("ALTA")

        if not self._engine.is_ready():
            QMessageBox.critical(
                self, "Modelo", "El modelo Faster-Whisper Small no está instalado."
            )
            return
        if not self._diarization.is_ready():
            QMessageBox.critical(
                self, "Hablantes", "Community-1 no está instalado o está incompleto."
            )
            return
        if not self._rescue.is_ready():
            QMessageBox.critical(
                self, "Hablantes", "La segunda capa ECAPA no está instalada o está incompleta."
            )
            return

        self._editor.clear()
        self._history_id = None
        self._thread = QThread(self)
        self._worker = TranscriptionWorker(
            engine=self._engine,
            audio_path=self._selected_file,
            language=settings.language,
            uppercase=settings.uppercase,
            show_timestamps=settings.show_timestamps,
            file_profile="ALTA",
            diarization_enabled=True,
            speaker_one_label=settings.speaker_one_label,
            speaker_two_label=settings.speaker_two_label,
            first_speaker_is_one=settings.first_speaker_agent,
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.progress.connect(self._on_progress)
        self._worker.completed.connect(self._on_completed)
        self._worker.warning.connect(self._on_warning)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self._thread_finished)
        self._set_busy(True)
        self._thread.start()

    def _on_progress(self, value: int, message: str) -> None:
        value = max(0, min(100, int(value)))
        self._progress.setValue(value)
        self._progress.setFormat(message)
        self.status_changed.emit(message)

    def _on_completed(self, conversation: Conversation) -> None:
        settings = self._config_service.load()
        text = conversation.text.strip()
        if settings.uppercase:
            text = text.upper()
        self._editor.setPlainText(text)

        entry = self._history_service.add_entry(
            source_path=str(self._selected_file or ""),
            text=text,
            profile="ALTA PRECISIÓN LOCAL",
            language=settings.language,
        )
        self._history_id = entry["id"]
        self.history_changed.emit()
        self._progress.setValue(100)
        self._progress.setFormat("Finalizado")
        self.status_changed.emit("LISTO")
        self._update_buttons()

    def _on_warning(self, message: str) -> None:
        QMessageBox.warning(self, "Identificación de hablantes", message)

    def _on_failed(self, message: str) -> None:
        self._progress.setValue(0)
        self._progress.setFormat("Error")
        self.status_changed.emit("ERROR")
        QMessageBox.critical(self, "Transcripción", message)

    def _thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._set_busy(False)

    def _set_busy(self, busy: bool) -> None:
        self._select_button.setEnabled(not busy)
        self._transcribe_button.setEnabled(not busy and self._selected_file is not None)
        self._clear_button.setEnabled(not busy)
        self._update_buttons()

    def _is_busy(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def _clear(self) -> None:
        if self._is_busy():
            return
        self._selected_file = None
        self._history_id = None
        self._file_name.setText("Ningún archivo seleccionado")
        self._file_detail.setText("WAV, MP3, M4A, FLAC, OGG, AAC, WMA, MP4 y WEBM")
        self._editor.clear()
        self._progress.setValue(0)
        self._progress.setFormat("Listo")
        self._update_buttons()

    def load_history_entry(self, entry: dict) -> None:
        source_path = str(entry.get("source_path", ""))
        self._selected_file = Path(source_path) if source_path else None
        self._history_id = str(entry.get("id", "")) or None
        self._file_name.setText(str(entry.get("source_name", "Transcripción recuperada")))
        self._file_detail.setText(source_path or "Origen no disponible")
        self._editor.setPlainText(str(entry.get("text", "")))
        self._progress.setValue(100)
        self._progress.setFormat("Recuperado del historial")
        self._update_buttons()

    def _change_current_speaker(self, use_agent: bool) -> None:
        cursor = self._editor.textCursor()
        settings = self._config_service.load()
        agent = settings.speaker_one_label
        client = settings.speaker_two_label
        new_label = agent if use_agent else client

        if cursor.hasSelection():
            source = cursor.selectedText().replace("\u2029", "\n")
        else:
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            source = cursor.selectedText().replace("\u2029", "\n")

        if not source.strip():
            return
        cursor.insertText(self._replace_speaker_labels(source, new_label, agent, client))
        self._editor.setTextCursor(cursor)

    @staticmethod
    def _replace_speaker_labels(
        text: str,
        new_label: str,
        agent_label: str,
        client_label: str,
    ) -> str:
        labels = rf"(?:{re.escape(agent_label)}|{re.escape(client_label)})"
        output = []
        for line in text.splitlines():
            if not line.strip():
                output.append(line)
                continue
            timestamp_match = re.match(r"^\s*(\[[^\]]+\])\s*", line)
            timestamp = f"{timestamp_match.group(1)} " if timestamp_match else ""
            body = re.sub(r"^\s*\[[^\]]+\]\s*", "", line)
            body = re.sub(rf"^\s*{labels}\s*:\s*", "", body, flags=re.I)
            output.append(f"{timestamp}{new_label}: {body.strip()}")
        return "\n".join(output)

    def _update_buttons(self) -> None:
        has_text = bool(self._editor.toPlainText().strip())
        busy = self._is_busy()
        self._transcribe_button.setEnabled(not busy and self._selected_file is not None)
        for button in (
            self._agent_button,
            self._client_button,
            self._txt_button,
            self._word_button,
            self._update_history_button,
        ):
            button.setEnabled(has_text and not busy)
        self._clear_button.setEnabled(
            not busy and (self._selected_file is not None or has_text)
        )

    def _update_history(self) -> None:
        if not self._history_id:
            return
        self._history_service.update_text(self._history_id, self._editor.toPlainText())
        self.history_changed.emit()
        self.status_changed.emit("CAMBIOS GUARDADOS")

    def _start_export(self, kind: str) -> None:
        text = self._editor.toPlainText().strip()
        if not text:
            return

        default_name = (
            (self._selected_file.stem if self._selected_file else "transcripcion")
            + (".txt" if kind == "txt" else ".docx")
        )
        if kind == "txt":
            destination, _ = QFileDialog.getSaveFileName(
                self, "Exportar TXT", default_name, "Texto (*.txt)"
            )
        else:
            destination, _ = QFileDialog.getSaveFileName(
                self, "Exportar Word", default_name, "Word (*.docx)"
            )
        if not destination:
            return

        self._export_thread = QThread(self)
        self._export_worker = ExportWorker(
            destination=Path(destination),
            text=text,
            source_name=self._selected_file.name if self._selected_file else "",
            export_type=kind,
        )
        self._export_worker.moveToThread(self._export_thread)
        self._export_thread.started.connect(self._export_worker.run)
        self._export_worker.completed.connect(self._export_done)
        self._export_worker.failed.connect(self._export_failed)
        self._export_worker.finished.connect(self._export_thread.quit)
        self._export_worker.finished.connect(self._export_worker.deleteLater)
        self._export_thread.finished.connect(self._export_thread.deleteLater)
        self._export_thread.start()

    def _export_done(self, path: str) -> None:
        QMessageBox.information(self, "Exportación", f"Archivo guardado:\n{path}")

    def _export_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Exportación", message)
