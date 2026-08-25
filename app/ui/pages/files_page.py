from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

from PySide6.QtCore import (
    QProcess,
    QProcessEnvironment,
    QThread,
    Qt,
    Signal,
)
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

from app.models.conversation import Conversation, Segment
from app.services.config_service import ConfigService
from app.services.export_service import ExportService
from app.services.history_service import HistoryService
from app.services.paths_service import AppPaths
from app.workers.export_worker import ExportWorker


EVENT_PREFIX = "AUDITOR_EVENT|"


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
        history_service: HistoryService,
    ) -> None:
        super().__init__()

        self._config_service = config_service
        self._history_service = history_service
        self._paths = AppPaths()
        self._export = ExportService()

        self._selected_file: Path | None = None
        self._history_id: str | None = None

        self._process: QProcess | None = None
        self._stdout_buffer = ""
        self._job_path: Path | None = None
        self._result_path: Path | None = None
        self._completed_event = False

        self._export_thread = None
        self._export_worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 28)
        root.setSpacing(16)

        title = QLabel("Transcribir entrevista")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Procesamiento local aislado · la interfaz permanece disponible mientras trabaja la IA"
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
        self._drop_zone.file_dropped.connect(
            lambda value: self._load_file(Path(value))
        )
        source_layout.addWidget(self._drop_zone)

        row = QHBoxLayout()

        self._select_button = QPushButton("Seleccionar archivo")
        self._select_button.setObjectName("SecondaryButton")
        self._select_button.clicked.connect(self._select_file)

        self._file_name = QLabel("Ningún archivo seleccionado")
        self._file_name.setObjectName("FileName")

        self._transcribe_button = QPushButton("Transcribir")
        self._transcribe_button.setObjectName("PrimaryButton")
        self._transcribe_button.setEnabled(False)
        self._transcribe_button.clicked.connect(self._start_transcription)

        self._cancel_button = QPushButton("Cancelar")
        self._cancel_button.setObjectName("SecondaryButton")
        self._cancel_button.setVisible(False)
        self._cancel_button.clicked.connect(self._cancel_processing)

        row.addWidget(self._select_button)
        row.addWidget(self._file_name, 1)
        row.addWidget(self._transcribe_button)
        row.addWidget(self._cancel_button)
        source_layout.addLayout(row)

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

        self._process_detail = QLabel(
            "El procesamiento pesado se ejecuta fuera de la interfaz."
        )
        self._process_detail.setObjectName("Muted")
        self._process_detail.setWordWrap(True)
        source_layout.addWidget(self._process_detail)

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
        self._agent_button.clicked.connect(
            lambda: self._change_current_speaker(True)
        )

        self._client_button = QPushButton("Marcar Cliente")
        self._client_button.setObjectName("ClientButton")
        self._client_button.clicked.connect(
            lambda: self._change_current_speaker(False)
        )

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
        """Solo guarda la ruta. No abre audio, no lee metadata y no carga modelos."""
        if self._is_busy():
            return

        suffix = path.suffix.lower()
        if suffix not in self.SUPPORTED_EXTENSIONS:
            QMessageBox.warning(
                self,
                "Archivo",
                "Selecciona un archivo de audio compatible.",
            )
            return

        self._selected_file = path
        self._history_id = None
        self._file_name.setText(path.name)
        self._file_detail.setText(
            f"{suffix.lstrip('.').upper()} · listo para procesar"
        )
        self._progress.setValue(0)
        self._progress.setFormat("Archivo cargado")
        self._process_detail.setText(
            "Presiona Transcribir. La ventana seguirá respondiendo durante todo el proceso."
        )
        self._update_buttons()

    def _start_transcription(self) -> None:
        if self._selected_file is None or self._is_busy():
            return

        settings = self._config_service.load()
        self._editor.clear()
        self._history_id = None
        self._completed_event = False
        self._stdout_buffer = ""

        job_id = uuid.uuid4().hex
        self._job_path = self._paths.temp / f"job_{job_id}.json"
        self._result_path = self._paths.temp / f"result_{job_id}.json"

        job = {
            "audio_path": str(self._selected_file),
            "result_path": str(self._result_path),
            "language": settings.language,
            "uppercase": settings.uppercase,
            "show_timestamps": settings.show_timestamps,
            "speaker_one_label": settings.speaker_one_label,
            "speaker_two_label": settings.speaker_two_label,
            "first_speaker_is_one": settings.first_speaker_agent,
        }
        self._job_path.write_text(
            json.dumps(job, ensure_ascii=False),
            encoding="utf-8",
        )

        process = QProcess(self)
        process.setProcessChannelMode(
            QProcess.ProcessChannelMode.MergedChannels
        )

        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYANNOTE_METRICS_ENABLED", "0")
        environment.insert("HF_HUB_DISABLE_TELEMETRY", "1")
        environment.insert("HF_HUB_OFFLINE", "1")
        environment.insert("TOKENIZERS_PARALLELISM", "false")
        process.setProcessEnvironment(environment)

        if getattr(sys, "frozen", False):
            program = sys.executable
            arguments = ["--file-worker", str(self._job_path)]
        else:
            root = Path(__file__).resolve().parents[3]
            program = sys.executable
            arguments = [
                str(root / "main.py"),
                "--file-worker",
                str(self._job_path),
            ]

        process.setProgram(program)
        process.setArguments(arguments)
        process.setWorkingDirectory(str(self._paths.root))
        process.readyReadStandardOutput.connect(self._read_process_output)
        process.started.connect(self._process_started)
        process.finished.connect(self._process_finished)
        process.errorOccurred.connect(self._process_error)

        self._process = process
        self._set_busy(True)
        self._progress.setValue(0)
        self._progress.setFormat("Iniciando proceso...")
        self._process_detail.setText(
            "La IA está ejecutándose en un proceso independiente."
        )
        process.start()

    def _process_started(self) -> None:
        self.status_changed.emit("PROCESANDO ARCHIVO")

    def _read_process_output(self) -> None:
        if self._process is None:
            return

        data = bytes(
            self._process.readAllStandardOutput()
        ).decode("utf-8", errors="replace")
        self._stdout_buffer += data

        while "\n" in self._stdout_buffer:
            line, self._stdout_buffer = self._stdout_buffer.split("\n", 1)
            self._handle_process_line(line.strip())

    def _handle_process_line(self, line: str) -> None:
        if not line.startswith(EVENT_PREFIX):
            return

        try:
            event = json.loads(line[len(EVENT_PREFIX):])
        except json.JSONDecodeError:
            return

        kind = event.get("type")

        if kind == "progress":
            value = max(0, min(100, int(event.get("value", 0))))
            message = str(event.get("message", "Procesando..."))
            self._progress.setValue(value)
            self._progress.setFormat(message)
            self._process_detail.setText(message)
            self.status_changed.emit(message)

        elif kind == "completed":
            self._completed_event = True
            self._load_worker_result()

        elif kind == "failed":
            self._completed_event = True
            error_type = str(event.get("error_type", "Error"))
            message = str(event.get("message", "Error desconocido."))
            self._show_processing_error(f"{error_type}: {message}")

    def _load_worker_result(self) -> None:
        if self._result_path is None or not self._result_path.is_file():
            self._show_processing_error(
                "El proceso terminó pero no generó el resultado."
            )
            return

        try:
            payload = json.loads(
                self._result_path.read_text(encoding="utf-8")
            )
            segments = [
                Segment(
                    start=float(row.get("start", 0.0)),
                    end=float(row.get("end", 0.0)),
                    text=str(row.get("text", "")),
                    speaker=str(row.get("speaker", "HABLANTE")),
                    confidence=row.get("confidence"),
                    words=list(row.get("words", []) or []),
                )
                for row in payload.get("segments", [])
            ]
            conversation = Conversation(
                source_path=str(
                    payload.get("source_path", self._selected_file or "")
                ),
                language=str(payload.get("language", "ES")),
                segments=segments,
            )
        except Exception as exc:
            self._show_processing_error(
                f"No fue posible abrir el resultado: {type(exc).__name__}: {exc}"
            )
            return

        self._on_completed(conversation)

    def _process_finished(self, exit_code: int, exit_status) -> None:
        self._read_process_output()

        if (
            not self._completed_event
            and exit_code == 0
            and self._result_path is not None
            and self._result_path.is_file()
        ):
            self._load_worker_result()
            self._completed_event = True
        elif not self._completed_event and exit_code != 0:
            self._show_processing_error(
                "El proceso de IA terminó inesperadamente. "
                f"Código: {exit_code}"
            )

        self._cleanup_process_files()
        self._process = None
        self._set_busy(False)

    def _process_error(self, error) -> None:
        if self._completed_event:
            return
        self._completed_event = True
        self._show_processing_error(
            "Windows no pudo iniciar o mantener el proceso aislado de transcripción."
        )

    def _cancel_processing(self) -> None:
        if self._process is None:
            return
        self._process_detail.setText("Cancelando...")
        self._process.kill()

    def _show_processing_error(self, message: str) -> None:
        self._progress.setValue(0)
        self._progress.setFormat("Error")
        self._process_detail.setText(message)
        self.status_changed.emit("ERROR")
        QMessageBox.critical(self, "Transcripción", message)

    def _cleanup_process_files(self) -> None:
        for path in (self._job_path, self._result_path):
            if path is not None:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
        self._job_path = None
        self._result_path = None

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
        self._process_detail.setText("Transcripción finalizada.")
        self.status_changed.emit("LISTO")
        self._update_buttons()

    def _set_busy(self, busy: bool) -> None:
        self._select_button.setEnabled(not busy)
        self._drop_zone.setEnabled(not busy)
        self._transcribe_button.setEnabled(
            not busy and self._selected_file is not None
        )
        self._cancel_button.setVisible(busy)
        self._cancel_button.setEnabled(busy)
        self._clear_button.setEnabled(not busy)
        self._update_buttons()

    def _is_busy(self) -> bool:
        return (
            self._process is not None
            and self._process.state() != QProcess.ProcessState.NotRunning
        )

    def _clear(self) -> None:
        if self._is_busy():
            return
        self._selected_file = None
        self._history_id = None
        self._file_name.setText("Ningún archivo seleccionado")
        self._file_detail.setText(
            "WAV, MP3, M4A, FLAC, OGG, AAC, WMA, MP4 y WEBM"
        )
        self._editor.clear()
        self._progress.setValue(0)
        self._progress.setFormat("Listo")
        self._process_detail.setText(
            "El procesamiento pesado se ejecuta fuera de la interfaz."
        )
        self._update_buttons()

    def load_history_entry(self, entry: dict) -> None:
        source_path = str(entry.get("source_path", ""))
        self._selected_file = Path(source_path) if source_path else None
        self._history_id = str(entry.get("id", "")) or None
        self._file_name.setText(
            str(entry.get("source_name", "Transcripción recuperada"))
        )
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

        replacement = self._replace_speaker_labels(
            source,
            new_label,
            agent,
            client,
        )
        cursor.insertText(replacement)
        self._editor.setTextCursor(cursor)

    @staticmethod
    def _replace_speaker_labels(
        text: str,
        new_label: str,
        agent_label: str,
        client_label: str,
    ) -> str:
        labels = (
            rf"(?:{re.escape(agent_label)}|{re.escape(client_label)})"
        )
        output = []

        for line in text.splitlines():
            if not line.strip():
                output.append(line)
                continue

            timestamp_match = re.match(r"^\s*(\[[^\]]+\])\s*", line)
            timestamp = (
                f"{timestamp_match.group(1)} "
                if timestamp_match
                else ""
            )
            body = re.sub(r"^\s*\[[^\]]+\]\s*", "", line)
            body = re.sub(
                rf"^\s*{labels}\s*:\s*",
                "",
                body,
                flags=re.I,
            )
            output.append(f"{timestamp}{new_label}: {body.strip()}")

        return "\n".join(output)

    def _update_buttons(self) -> None:
        has_text = bool(self._editor.toPlainText().strip())
        busy = self._is_busy()

        self._transcribe_button.setEnabled(
            not busy and self._selected_file is not None
        )
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
        self._history_service.update_text(
            self._history_id,
            self._editor.toPlainText(),
        )
        self.history_changed.emit()
        self.status_changed.emit("CAMBIOS GUARDADOS")

    def _start_export(self, kind: str) -> None:
        text = self._editor.toPlainText().strip()
        if not text:
            return

        self._export_thread = QThread(self)
        self._export_worker = ExportWorker(
            export_service=self._export,
            kind=kind,
            text=text,
            source_path=str(self._selected_file or ""),
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
        QMessageBox.information(
            self,
            "Exportación",
            f"Archivo guardado:\n{path}",
        )

    def _export_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Exportación", message)
