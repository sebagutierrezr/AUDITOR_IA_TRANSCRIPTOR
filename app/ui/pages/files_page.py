from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from app.engines.faster_whisper_engine import FasterWhisperEngine
from app.models.conversation import Conversation
from app.services.config_service import ConfigService
from app.services.export_service import ExportService
from app.services.history_service import HistoryService
from app.services.diarization_service import DiarizationService
from app.services.paths_service import AppPaths
from app.ui.pages.common import create_page_header
from app.workers.transcription_worker import TranscriptionWorker
from app.workers.export_worker import ExportWorker


class FilesPage(QFrame):
    status_changed = Signal(str)
    history_changed = Signal()

    SUPPORTED_EXTENSIONS = {
        ".wav",
        ".mp3",
        ".m4a",
        ".flac",
        ".ogg",
        ".aac",
        ".wma",
        ".mp4",
        ".webm",
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
        self._paths = AppPaths()
        self._export = ExportService()

        self._selected_file: Path | None = None
        self._history_id: str | None = None
        self._thread: QThread | None = None
        self._worker: TranscriptionWorker | None = None
        self._export_thread: QThread | None = None
        self._export_worker: ExportWorker | None = None
        self._diarization_service = DiarizationService()

        page, layout = create_page_header(
            "TRANSCRIPCIÓN DE ARCHIVOS",
            "TRANSCRIBE AUDIO MONO O CONVIÉRTELO AUTOMÁTICAMENTE A MONO.",
        )
        layout.setSpacing(9)

        source_card = QFrame()
        source_card.setObjectName("MonoFileSourceCard")
        source_layout = QVBoxLayout(source_card)
        source_layout.setContentsMargins(16, 12, 16, 12)
        source_layout.setSpacing(9)

        source_header = QHBoxLayout()

        source_title_box = QVBoxLayout()
        source_title_box.setSpacing(0)

        source_title = QLabel("ARCHIVO DE AUDIO")
        source_title.setObjectName("MonoFileSectionTitle")

        source_help = QLabel(
            "WAV, MP3, M4A, FLAC, OGG, AAC, WMA, MP4 O WEBM."
        )
        source_help.setObjectName("MonoFileHelp")

        source_title_box.addWidget(source_title)
        source_title_box.addWidget(source_help)
        source_header.addLayout(source_title_box)
        source_header.addStretch(1)

        self._select_button = QPushButton("SELECCIONAR ARCHIVO")
        self._select_button.setObjectName("MonoFileSecondary")
        self._select_button.clicked.connect(self._select_file)
        source_header.addWidget(self._select_button)
        source_layout.addLayout(source_header)

        file_row = QHBoxLayout()
        file_row.setSpacing(10)

        file_label = QLabel("ARCHIVO")
        file_label.setObjectName("MonoFileLabel")
        file_label.setFixedWidth(70)

        self._file_name = QLabel("NINGÚN ARCHIVO SELECCIONADO")
        self._file_name.setObjectName("MonoFileValue")
        self._file_name.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._file_status = QLabel("PENDIENTE")
        self._file_status.setObjectName("MonoFileStatus")

        file_row.addWidget(file_label)
        file_row.addWidget(self._file_name, 1)
        file_row.addWidget(self._file_status)
        source_layout.addLayout(file_row)

        self._file_detail = QLabel(
            "La validación y conversión se ejecutarán en segundo plano."
        )
        self._file_detail.setObjectName("MonoFileDetail")
        self._file_detail.setWordWrap(True)
        source_layout.addWidget(self._file_detail)

        control_row = QHBoxLayout()
        control_row.setSpacing(9)

        self._transcribe_button = QPushButton("TRANSCRIBIR ARCHIVO")
        self._transcribe_button.setObjectName("MonoFilePrimary")
        self._transcribe_button.setEnabled(False)
        self._transcribe_button.clicked.connect(self._start_transcription)

        self._clear_button = QPushButton("LIMPIAR")
        self._clear_button.setObjectName("MonoFileDanger")
        self._clear_button.clicked.connect(self._clear)
        self._clear_button.setEnabled(False)

        control_row.addWidget(self._transcribe_button)
        control_row.addWidget(self._clear_button)
        control_row.addStretch(1)

        self._state_label = QLabel("ESTADO: LISTO")
        self._state_label.setObjectName("MonoFileState")
        control_row.addWidget(self._state_label)
        source_layout.addLayout(control_row)

        self._progress = QProgressBar()
        self._progress.setObjectName("MonoFileProgress")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("LISTO")
        source_layout.addWidget(self._progress)

        layout.addWidget(source_card)

        transcript_card = QFrame()
        transcript_card.setObjectName("MonoFileTranscriptCard")
        transcript_card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        transcript_layout = QVBoxLayout(transcript_card)
        transcript_layout.setContentsMargins(15, 11, 15, 11)
        transcript_layout.setSpacing(8)

        transcript_header = QHBoxLayout()

        transcript_title_box = QVBoxLayout()
        transcript_title_box.setSpacing(0)

        transcript_title = QLabel("TRANSCRIPCIÓN")
        transcript_title.setObjectName("MonoFileSectionTitle")

        transcript_help = QLabel(
            "Haz clic en una línea para cambiar su hablante."
        )
        transcript_help.setObjectName("MonoFileHelp")

        transcript_title_box.addWidget(transcript_title)
        transcript_title_box.addWidget(transcript_help)
        transcript_header.addLayout(transcript_title_box)
        transcript_header.addStretch(1)

        self._agent_button = QPushButton("MARCAR COMO AGENTE")
        self._agent_button.setObjectName("MonoFileAgentButton")
        self._agent_button.clicked.connect(
            lambda: self._change_current_speaker(True)
        )

        self._client_button = QPushButton("MARCAR COMO CLIENTE")
        self._client_button.setObjectName("MonoFileClientButton")
        self._client_button.clicked.connect(
            lambda: self._change_current_speaker(False)
        )

        transcript_header.addWidget(self._agent_button)
        transcript_header.addWidget(self._client_button)
        transcript_layout.addLayout(transcript_header)

        # Barra superior: nunca tapa el texto.
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self._update_history_button = QPushButton("ACTUALIZAR HISTORIAL")
        self._txt_button = QPushButton("EXPORTAR TXT")
        self._word_button = QPushButton("EXPORTAR WORD")
        self._open_exports_button = QPushButton("ABRIR CARPETA")
        self._open_exports_button.setObjectName("MonoFileSecondary")
        self._open_exports_button.clicked.connect(
            self._open_exports_folder
        )

        for button in (
            self._update_history_button,
            self._txt_button,
            self._word_button,
        ):
            button.setObjectName("MonoFileSecondary")
            button.setEnabled(False)

        self._update_history_button.clicked.connect(self._update_history)
        self._txt_button.clicked.connect(self._save_txt)
        self._word_button.clicked.connect(self._save_word)

        action_row.addStretch(1)
        action_row.addWidget(self._update_history_button)
        action_row.addWidget(self._txt_button)
        action_row.addWidget(self._word_button)
        action_row.addWidget(self._open_exports_button)
        transcript_layout.addLayout(action_row)

        self._editor = QPlainTextEdit()
        self._editor.setObjectName("MonoFileEditor")
        self._editor.setPlaceholderText(
            "LA TRANSCRIPCIÓN APARECERÁ AQUÍ."
        )
        self._editor.setMinimumHeight(300)
        self._editor.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._editor.textChanged.connect(self._update_buttons)
        self._editor.selectionChanged.connect(self._update_buttons)
        transcript_layout.addWidget(self._editor, 1)

        layout.addWidget(transcript_card, 1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page)

        self._update_buttons()

    def _select_file(self) -> None:
        """
        Selector interno estable.

        Se evita el diálogo nativo de Windows porque bloquea la interfaz
        en este equipo y provoca el estado "No responde".
        """
        dialog = QFileDialog(
            self,
            "SELECCIONAR ARCHIVO DE AUDIO",
        )
        dialog.setOption(
            QFileDialog.Option.DontUseNativeDialog,
            True,
        )
        dialog.setFileMode(
            QFileDialog.FileMode.ExistingFile
        )
        dialog.setAcceptMode(
            QFileDialog.AcceptMode.AcceptOpen
        )
        dialog.setNameFilters(
            [
                (
                    "Archivos de audio "
                    "(*.wav *.mp3 *.m4a *.flac *.ogg "
                    "*.aac *.wma *.mp4 *.webm)"
                ),
                "Todos los archivos (*)",
            ]
        )
        dialog.setViewMode(
            QFileDialog.ViewMode.Detail
        )
        dialog.resize(
            920,
            560,
        )

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected = dialog.selectedFiles()

        if selected:
            self._load_file(
                Path(selected[0])
            )

    def _load_file(self, path: Path) -> None:
        if self._is_busy():
            return

        if not path.exists() or not path.is_file():
            QMessageBox.critical(
                self,
                "ARCHIVO NO VÁLIDO",
                "EL ARCHIVO SELECCIONADO NO EXISTE.",
            )
            return

        extension = path.suffix.lower()

        if extension not in self.SUPPORTED_EXTENSIONS:
            QMessageBox.critical(
                self,
                "FORMATO NO COMPATIBLE",
                "USE WAV, MP3, M4A, FLAC, OGG, AAC, "
                "WMA, MP4 O WEBM.",
            )
            return

        try:
            size_mb = path.stat().st_size / 1024 / 1024
        except OSError as exc:
            QMessageBox.critical(
                self,
                "ARCHIVO NO DISPONIBLE",
                str(exc),
            )
            return

        self._selected_file = path
        self._history_id = None
        self._file_name.setText(path.name)
        self._file_status.setText("LISTO")
        self._file_detail.setText(
            f"FORMATO: {extension.lstrip('.').upper()}  ·  "
            f"TAMAÑO: {size_mb:.1f} MB  ·  "
            "SE CONVERTIRÁ A MONO 16 KHZ"
        )
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("ARCHIVO SELECCIONADO")
        self._state_label.setText("ESTADO: ARCHIVO LISTO")
        self.status_changed.emit("ARCHIVO LISTO")
        self._update_buttons()

    def _start_transcription(self) -> None:
        if self._selected_file is None or self._is_busy():
            return

        settings = self._config_service.load()
        self._engine.set_profile(settings.file_profile)

        if (
            settings.diarization_enabled
            and not self._diarization_service.is_ready()
        ):
            self._state_label.setText(
                "ESTADO: IDENTIFICADOR NO DISPONIBLE"
            )
            QMessageBox.critical(
                self,
                "IDENTIFICADOR DE VOCES NO DISPONIBLE",
                "EL MODELO PROFESIONAL PARA IDENTIFICAR "
                "AGENTE Y CLIENTE NO ESTÁ INSTALADO O ESTÁ "
                "INCOMPLETO.\n\n"
                "REINSTALA AUDITOR IA 6.1.0.",
            )
            return

        if not self._engine.is_ready():
            self._state_label.setText(
                "ESTADO: MODELO NO DISPONIBLE"
            )
            QMessageBox.critical(
                self,
                "MODELO NO DISPONIBLE",
                "EL MODELO NECESARIO NO ESTÁ INSTALADO "
                "O ESTÁ INCOMPLETO.\n\n"
                f"PERFIL: {settings.file_profile}\n"
                f"MODELO: {self._engine.model_name.upper()}\n\n"
                "REINSTALA AUDITOR IA 6.0.1.",
            )
            return
        self._history_id = None
        self._editor.clear()

        self._thread = QThread(self)
        self._worker = TranscriptionWorker(
            engine=self._engine,
            audio_path=self._selected_file,
            language=settings.language,
            uppercase=settings.uppercase,
            show_timestamps=settings.show_timestamps,
            file_profile=settings.file_profile,
            diarization_enabled=settings.diarization_enabled,
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
        self._progress.setRange(0, 100)
        self._progress.setValue(max(0, min(100, int(value))))
        self._progress.setFormat(message)
        self._state_label.setText(f"ESTADO: {message}")
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
            profile=settings.file_profile,
            language=settings.language,
        )
        self._history_id = entry["id"]
        self.history_changed.emit()

        self._progress.setValue(100)
        self._progress.setFormat("TRANSCRIPCIÓN FINALIZADA")
        self._state_label.setText("ESTADO: FINALIZADO")
        self.status_changed.emit("LISTO")
        self._update_buttons()

    def _on_warning(self, message: str) -> None:
        QMessageBox.warning(
            self,
            "IDENTIFICACIÓN DE HABLANTES",
            message,
        )

    def _on_failed(self, message: str) -> None:
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("ERROR")
        self._state_label.setText("ESTADO: ERROR")
        self.status_changed.emit("ERROR")

        QMessageBox.critical(
            self,
            "ERROR DE TRANSCRIPCIÓN",
            message,
        )

    def _thread_finished(self) -> None:
        self._thread = None
        self._worker = None
        self._set_busy(False)

    def _clear(self) -> None:
        if self._is_busy():
            return

        self._selected_file = None
        self._history_id = None
        self._file_name.setText("NINGÚN ARCHIVO SELECCIONADO")
        self._file_status.setText("PENDIENTE")
        self._file_detail.setText(
            "La validación y conversión se ejecutarán en segundo plano."
        )
        self._editor.clear()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setFormat("LISTO")
        self._state_label.setText("ESTADO: LISTO")
        self._update_buttons()

    def load_history_entry(self, entry: dict) -> None:
        source_path = str(entry.get("source_path", ""))
        self._selected_file = Path(source_path) if source_path else None
        self._history_id = str(entry.get("id", "")) or None
        self._file_name.setText(
            str(entry.get("source_name", "TRANSCRIPCIÓN RECUPERADA"))
        )
        self._file_status.setText("HISTORIAL")
        self._file_detail.setText(
            source_path or "ORIGEN NO DISPONIBLE"
        )
        self._editor.setPlainText(str(entry.get("text", "")))
        self._state_label.setText("ESTADO: RECUPERADO")
        self._progress.setValue(100)
        self._progress.setFormat("RECUPERADO DESDE HISTORIAL")
        self._update_buttons()

    def _change_current_speaker(self, use_agent: bool) -> None:
        cursor = self._editor.textCursor()
        settings = self._config_service.load()

        agent_label = settings.speaker_one_label
        client_label = settings.speaker_two_label
        new_label = agent_label if use_agent else client_label

        if cursor.hasSelection():
            source_text = cursor.selectedText().replace("\u2029", "\n")
        else:
            cursor.select(cursor.SelectionType.BlockUnderCursor)
            source_text = cursor.selectedText().replace("\u2029", "\n")

        if not source_text.strip():
            self.status_changed.emit("SELECCIONA UNA INTERVENCIÓN")
            return

        replacement = self._replace_speaker_labels(
            source_text,
            new_label,
            agent_label,
            client_label,
        )
        cursor.insertText(replacement)
        self._editor.setTextCursor(cursor)
        self.status_changed.emit(
            f"INTERVENCIÓN MARCADA COMO {new_label}"
        )
        self._update_buttons()

    @staticmethod
    def _replace_speaker_labels(
        text: str,
        new_label: str,
        agent_label: str,
        client_label: str,
    ) -> str:
        labels = (
            rf"(?:{re.escape(agent_label)}|"
            rf"{re.escape(client_label)})"
        )
        output: list[str] = []

        for line in text.splitlines():
            if not line.strip():
                output.append(line)
                continue

            timestamp_match = re.match(
                r"^\s*(\[[^\]]+\])\s*",
                line,
            )
            timestamp = (
                f"{timestamp_match.group(1)} "
                if timestamp_match
                else ""
            )

            without_timestamp = re.sub(
                r"^\s*\[[^\]]+\]\s*",
                "",
                line,
            )
            cleaned = re.sub(
                rf"^(?:{labels})\s*:\s*",
                "",
                without_timestamp,
                flags=re.IGNORECASE,
            ).strip()

            output.append(
                f"{timestamp}{new_label}: {cleaned}"
            )

        return "\n".join(output)

    def _update_history(self) -> None:
        if not self._history_id:
            return

        self._history_service.update_text(
            self._history_id,
            self._editor.toPlainText(),
        )
        self.history_changed.emit()

        QMessageBox.information(
            self,
            "HISTORIAL",
            "LA TRANSCRIPCIÓN FUE ACTUALIZADA.",
        )

    def _save_txt(self) -> None:
        self._start_export("txt")

    def _save_word(self) -> None:
        self._start_export("docx")

    def _start_export(
        self,
        export_type: str,
    ) -> None:
        if self._export_thread is not None:
            return

        content = self._editor.toPlainText().strip()

        if not content:
            return

        stem = (
            self._selected_file.stem
            if self._selected_file
            else "TRANSCRIPCION"
        )
        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
        extension = (
            ".txt"
            if export_type == "txt"
            else ".docx"
        )
        destination = (
            self._paths.exports
            / f"{stem}_TRANSCRIPCION_"
            f"{timestamp}{extension}"
        )

        source_name = (
            self._selected_file.name
            if self._selected_file
            else ""
        )

        self._export_thread = QThread(self)
        self._export_worker = ExportWorker(
            destination=destination,
            text=content,
            source_name=source_name,
            export_type=export_type,
        )
        self._export_worker.moveToThread(
            self._export_thread
        )

        self._export_thread.started.connect(
            self._export_worker.run
        )
        self._export_worker.completed.connect(
            self._export_completed
        )
        self._export_worker.failed.connect(
            self._export_failed
        )
        self._export_worker.finished.connect(
            self._export_thread.quit
        )
        self._export_worker.finished.connect(
            self._export_worker.deleteLater
        )
        self._export_thread.finished.connect(
            self._export_finished
        )
        self._export_thread.finished.connect(
            self._export_thread.deleteLater
        )

        self._state_label.setText(
            "ESTADO: EXPORTANDO..."
        )
        self._update_buttons()
        self._export_thread.start()

    def _export_completed(
        self,
        destination: str,
    ) -> None:
        self._state_label.setText(
            "ESTADO: ARCHIVO GUARDADO"
        )
        QMessageBox.information(
            self,
            "EXPORTACIÓN COMPLETADA",
            "EL ARCHIVO FUE GUARDADO EN:\n\n"
            f"{destination}",
        )

    def _export_failed(
        self,
        message: str,
    ) -> None:
        self._state_label.setText(
            "ESTADO: ERROR DE EXPORTACIÓN"
        )
        QMessageBox.critical(
            self,
            "ERROR DE EXPORTACIÓN",
            message,
        )

    def _export_finished(self) -> None:
        self._export_thread = None
        self._export_worker = None
        self._update_buttons()

    def _open_exports_folder(self) -> None:
        self._paths.exports.mkdir(
            parents=True,
            exist_ok=True,
        )

        try:
            os.startfile(
                str(self._paths.exports)
            )
        except AttributeError:
            QMessageBox.information(
                self,
                "CARPETA DE EXPORTACIONES",
                str(self._paths.exports),
            )
        except OSError as exc:
            QMessageBox.warning(
                self,
                "CARPETA DE EXPORTACIONES",
                f"NO FUE POSIBLE ABRIR LA CARPETA:\n\n{exc}",
            )

    def _is_busy(self) -> bool:
        transcription_busy = (
            self._thread is not None
            and self._thread.isRunning()
        )
        export_busy = (
            self._export_thread is not None
            and self._export_thread.isRunning()
        )
        return transcription_busy or export_busy

    def _set_busy(self, busy: bool) -> None:
        self._select_button.setEnabled(not busy)
        self._transcribe_button.setEnabled(
            not busy and self._selected_file is not None
        )
        self._clear_button.setEnabled(not busy)
        self._editor.setReadOnly(busy)
        self._update_buttons()

    def _update_buttons(self) -> None:
        busy = self._is_busy()
        has_file = self._selected_file is not None
        has_text = bool(self._editor.toPlainText().strip())

        self._select_button.setEnabled(not busy)
        self._transcribe_button.setEnabled(not busy and has_file)
        self._clear_button.setEnabled(
            not busy and (has_file or has_text)
        )
        self._agent_button.setEnabled(not busy and has_text)
        self._client_button.setEnabled(not busy and has_text)
        self._update_history_button.setEnabled(
            not busy
            and has_text
            and bool(self._history_id)
        )
        self._txt_button.setEnabled(not busy and has_text)
        self._word_button.setEnabled(not busy and has_text)
        self._open_exports_button.setEnabled(not busy)
