from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSlider,
    QTextEdit,
    QVBoxLayout,
)

from app.services.audio_device_service import AudioDeviceService
from app.services.export_service import ExportService
from app.services.paths_service import AppPaths
from app.ui.pages.common import create_page_header
from app.workers.audio_test_worker import AudioTestWorker
from app.workers.unified_audio_worker import UnifiedAudioWorker


class LivePage(QFrame):
    status_changed = Signal(str)
    history_changed = Signal()

    MODE_BOTH = "AGENTE + CLIENTE"
    MODE_AGENT = "SOLO AGENTE"
    MODE_CLIENT = "SOLO CLIENTE"

    def __init__(self, config_service, engine, history_service) -> None:
        super().__init__()

        self.config = config_service
        self.engine = engine
        self.history = history_service
        self.export = ExportService()
        self.paths = AppPaths()

        self.thread = None
        self.worker = None
        self.test_thread = None
        self.test_worker = None
        self.recording_path = None
        self.history_id = None
        self.original_profile = None
        self.paused = False
        self.last_speaker = ""

        self.agent_target = 0
        self.client_target = 0
        self.agent_display = 0.0
        self.client_display = 0.0

        page, layout = create_page_header(
            "Transcripción en vivo",
            "Captura por separado tu micrófono y el audio del cliente.",
        )
        layout.setSpacing(9)

        # ==============================================================
        # CONFIGURACIÓN DE AUDIO — FORMATO COMPACTO
        # ==============================================================
        setup = QFrame()
        setup.setObjectName("V41SetupCard")
        setup_box = QVBoxLayout(setup)
        setup_box.setContentsMargins(18, 13, 18, 14)
        setup_box.setSpacing(10)

        setup_header = QHBoxLayout()
        setup_title_box = QVBoxLayout()
        setup_title_box.setSpacing(1)

        setup_title = QLabel("CONFIGURACIÓN DE AUDIO")
        setup_title.setObjectName("V41SectionTitle")
        setup_subtitle = QLabel(
            "Los dispositivos predeterminados se seleccionan automáticamente."
        )
        setup_subtitle.setObjectName("V41SectionSubtitle")

        setup_title_box.addWidget(setup_title)
        setup_title_box.addWidget(setup_subtitle)
        setup_header.addLayout(setup_title_box)
        setup_header.addStretch(1)

        self.refresh_btn = QPushButton("ACTUALIZAR DISPOSITIVOS")
        self.refresh_btn.setObjectName("V41GhostButton")
        self.refresh_btn.clicked.connect(self.load_devices)
        setup_header.addWidget(self.refresh_btn)
        setup_box.addLayout(setup_header)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)

        mode_label = QLabel("MODO")
        mode_label.setObjectName("V41FieldLabel")
        mode_row.addWidget(mode_label)

        self.mode = QComboBox()
        self.mode.setObjectName("V41ModeCombo")
        self.mode.addItems(
            [self.MODE_BOTH, self.MODE_AGENT, self.MODE_CLIENT]
        )
        self.mode.setMinimumWidth(245)
        self.mode.currentTextChanged.connect(self.mode_changed)
        mode_row.addWidget(self.mode)
        mode_row.addStretch(1)

        auto_badge = QLabel("SELECCIÓN AUTOMÁTICA")
        auto_badge.setObjectName("V41AutoBadge")
        mode_row.addWidget(auto_badge)
        setup_box.addLayout(mode_row)

        device_grid = QGridLayout()
        device_grid.setHorizontalSpacing(10)
        device_grid.setVerticalSpacing(8)
        device_grid.setColumnStretch(1, 1)
        device_grid.setColumnStretch(5, 1)

        # AGENTE
        agent_icon = QLabel("A")
        agent_icon.setObjectName("V41AgentBadge")
        agent_icon.setFixedSize(30, 30)

        agent_names = QVBoxLayout()
        agent_names.setSpacing(0)
        agent_title = QLabel("AGENTE")
        agent_title.setObjectName("V41SourceTitle")
        agent_help = QLabel("Micrófono por el que hablas")
        agent_help.setObjectName("V41SourceHelp")
        agent_names.addWidget(agent_title)
        agent_names.addWidget(agent_help)

        self.agent_combo = QComboBox()
        self.agent_combo.setObjectName("V41DeviceCombo")
        self.agent_status = QLabel("SIN CONFIGURAR")
        self.agent_status.setObjectName("V41StatusNeutral")
        self.agent_test = QPushButton("PROBAR")
        self.agent_test.setObjectName("V41TestButton")
        self.agent_test.clicked.connect(self.test_agent)

        device_grid.addWidget(agent_icon, 0, 0)
        device_grid.addLayout(agent_names, 0, 1)
        device_grid.addWidget(self.agent_status, 0, 2)
        device_grid.addWidget(self.agent_combo, 1, 0, 1, 3)
        device_grid.addWidget(self.agent_test, 1, 3)

        # CLIENTE
        client_icon = QLabel("C")
        client_icon.setObjectName("V41ClientBadge")
        client_icon.setFixedSize(30, 30)

        client_names = QVBoxLayout()
        client_names.setSpacing(0)
        client_title = QLabel("CLIENTE")
        client_title.setObjectName("V41SourceTitle")
        client_help = QLabel("Audio que escuchas en el headset")
        client_help.setObjectName("V41SourceHelp")
        client_names.addWidget(client_title)
        client_names.addWidget(client_help)

        self.client_combo = QComboBox()
        self.client_combo.setObjectName("V41DeviceCombo")
        self.client_status = QLabel("SIN CONFIGURAR")
        self.client_status.setObjectName("V41StatusNeutral")
        self.client_test = QPushButton("PROBAR")
        self.client_test.setObjectName("V41TestButton")
        self.client_test.clicked.connect(self.test_client)

        device_grid.addWidget(client_icon, 0, 4)
        device_grid.addLayout(client_names, 0, 5)
        device_grid.addWidget(self.client_status, 0, 6)
        device_grid.addWidget(self.client_combo, 1, 4, 1, 3)
        device_grid.addWidget(self.client_test, 1, 7)

        # MEDIDORES
        agent_level_row = QHBoxLayout()
        agent_level_row.setSpacing(8)
        agent_level_label = QLabel("NIVEL")
        agent_level_label.setObjectName("V41MeterLabel")
        self.agent_bar = self.level_bar("#1685A1")
        agent_level_row.addWidget(agent_level_label)
        agent_level_row.addWidget(self.agent_bar, 1)

        client_level_row = QHBoxLayout()
        client_level_row.setSpacing(8)
        client_level_label = QLabel("NIVEL")
        client_level_label.setObjectName("V41MeterLabel")
        self.client_bar = self.level_bar("#15906D")
        client_level_row.addWidget(client_level_label)
        client_level_row.addWidget(self.client_bar, 1)

        device_grid.addLayout(agent_level_row, 2, 0, 1, 4)
        device_grid.addLayout(client_level_row, 2, 4, 1, 4)

        agent_sensitivity_row = QHBoxLayout()
        agent_sensitivity_row.setSpacing(8)
        agent_sensitivity_label = QLabel("SENSIBILIDAD")
        agent_sensitivity_label.setObjectName("V47SensitivityLabel")
        self.agent_sensitivity = QSlider(Qt.Orientation.Horizontal)
        self.agent_sensitivity.setObjectName("V47SensitivitySlider")
        self.agent_sensitivity.setRange(0, 100)
        self.agent_sensitivity.setValue(75)
        self.agent_sensitivity_value = QLabel("75 %")
        self.agent_sensitivity_value.setObjectName("V47SensitivityValue")
        self.agent_sensitivity.valueChanged.connect(
            self.agent_sensitivity_changed
        )
        agent_sensitivity_row.addWidget(agent_sensitivity_label)
        agent_sensitivity_row.addWidget(self.agent_sensitivity, 1)
        agent_sensitivity_row.addWidget(self.agent_sensitivity_value)

        client_sensitivity_row = QHBoxLayout()
        client_sensitivity_row.setSpacing(8)
        client_sensitivity_label = QLabel("SENSIBILIDAD")
        client_sensitivity_label.setObjectName("V47SensitivityLabel")
        self.client_sensitivity = QSlider(Qt.Orientation.Horizontal)
        self.client_sensitivity.setObjectName("V47SensitivitySlider")
        self.client_sensitivity.setRange(0, 100)
        self.client_sensitivity.setValue(70)
        self.client_sensitivity_value = QLabel("70 %")
        self.client_sensitivity_value.setObjectName("V47SensitivityValue")
        self.client_sensitivity.valueChanged.connect(
            self.client_sensitivity_changed
        )
        client_sensitivity_row.addWidget(client_sensitivity_label)
        client_sensitivity_row.addWidget(self.client_sensitivity, 1)
        client_sensitivity_row.addWidget(self.client_sensitivity_value)

        device_grid.addLayout(agent_sensitivity_row, 3, 0, 1, 4)
        device_grid.addLayout(client_sensitivity_row, 3, 4, 1, 4)

        noise_filter_row = QHBoxLayout()
        noise_filter_row.setSpacing(8)
        noise_filter_label = QLabel("FILTRO DE RUIDO")
        noise_filter_label.setObjectName("V472NoiseLabel")
        noise_filter_help = QLabel("BAJO")
        noise_filter_help.setObjectName("V472NoiseHint")
        self.noise_filter = QSlider(Qt.Orientation.Horizontal)
        self.noise_filter.setObjectName("V472NoiseSlider")
        self.noise_filter.setRange(0, 100)
        self.noise_filter.setValue(35)
        self.noise_filter_value = QLabel("35 %")
        self.noise_filter_value.setObjectName("V472NoiseValue")
        self.noise_filter.valueChanged.connect(self.noise_filter_changed)

        noise_filter_row.addWidget(noise_filter_label)
        noise_filter_row.addWidget(noise_filter_help)
        noise_filter_row.addWidget(self.noise_filter, 1)
        noise_filter_row.addWidget(self.noise_filter_value)

        device_grid.addLayout(noise_filter_row, 4, 0, 1, 8)
        setup_box.addLayout(device_grid)
        self.setup_card = setup
        layout.addWidget(setup)

        # ==============================================================
        # SESIÓN
        # ==============================================================
        session = QFrame()
        session.setObjectName("V41SessionCard")
        session_row = QHBoxLayout(session)
        session_row.setContentsMargins(14, 9, 14, 9)
        session_row.setSpacing(9)

        self.state = self.metric(session_row, "ESTADO", "LISTO")
        self.time = self.metric(session_row, "TIEMPO", "00:00")
        self.sources_label = self.metric(
            session_row, "FUENTES", "LISTAS PARA INICIAR", wide=True
        )

        session_row.addStretch(1)

        self.start_btn = QPushButton("INICIAR TRANSCRIPCIÓN")
        self.start_btn.setObjectName("V41PrimaryButton")
        self.start_btn.clicked.connect(self.start)

        self.pause_btn = QPushButton("PAUSAR")
        self.pause_btn.setObjectName("V41ControlButton")
        self.pause_btn.clicked.connect(self.toggle_pause)

        self.stop_btn = QPushButton("DETENER")
        self.stop_btn.setObjectName("V41StopButton")
        self.stop_btn.clicked.connect(self.stop)

        session_row.addWidget(self.start_btn)
        session_row.addWidget(self.pause_btn)
        session_row.addWidget(self.stop_btn)
        self.session_card = session
        layout.addWidget(session)

        # ==============================================================
        # TRANSCRIPCIÓN — ÁREA PRINCIPAL
        # ==============================================================
        transcript = QFrame()
        transcript.setObjectName("V41TranscriptCard")
        transcript.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        transcript_box = QVBoxLayout(transcript)
        transcript_box.setContentsMargins(16, 12, 16, 12)
        transcript_box.setSpacing(8)

        transcript_header = QHBoxLayout()
        transcript_title_box = QVBoxLayout()
        transcript_title_box.setSpacing(0)

        transcript_title = QLabel("TRANSCRIPCIÓN")
        transcript_title.setObjectName("V41SectionTitle")
        transcript_help = QLabel(
            "Revisa, corrige y exporta la conversación desde este espacio."
        )
        transcript_help.setObjectName("V41SectionSubtitle")

        transcript_title_box.addWidget(transcript_title)
        transcript_title_box.addWidget(transcript_help)
        transcript_header.addLayout(transcript_title_box)
        transcript_header.addStretch(1)

        self.expand_button = QPushButton("AMPLIAR TRANSCRIPCIÓN")
        self.expand_button.setObjectName("V471ExpandButton")
        self.expand_button.setCheckable(True)
        self.expand_button.toggled.connect(self.toggle_transcript_view)
        transcript_header.addWidget(self.expand_button)

        self.agent_tag = QPushButton("AGENTE")
        self.client_tag = QPushButton("CLIENTE")
        for button in (self.agent_tag, self.client_tag):
            button.setObjectName("V41InlineButton")

        self.agent_tag.clicked.connect(lambda: self.change_speaker(True))
        self.client_tag.clicked.connect(lambda: self.change_speaker(False))

        transcript_header.addWidget(self.agent_tag)
        transcript_header.addWidget(self.client_tag)
        transcript_box.addLayout(transcript_header)

        self.editor = QTextEdit()
        self.editor.setObjectName("V46LiveEditor")
        self.editor.setMinimumHeight(560)
        self.editor.setPlaceholderText(
            "LA TRANSCRIPCIÓN APARECERÁ AQUÍ AL INICIAR LA SESIÓN."
        )
        self.editor.textChanged.connect(self.update_buttons)
        transcript_box.addWidget(self.editor, 1)

        export_row = QHBoxLayout()
        export_row.setSpacing(8)

        self.clear_btn = QPushButton("LIMPIAR TEXTO")
        self.clear_btn.setObjectName("V46ClearButton")
        self.clear_btn.clicked.connect(self.clear)
        export_row.addWidget(self.clear_btn)

        export_row.addStretch(1)

        self.hist_btn = QPushButton("ACTUALIZAR HISTORIAL")
        self.txt_btn = QPushButton("EXPORTAR TXT")
        self.word_btn = QPushButton("EXPORTAR WORD")

        for button in (
            self.hist_btn,
            self.txt_btn,
            self.word_btn,
        ):
            button.setObjectName("V46ExportButton")
            export_row.addWidget(button)

        self.hist_btn.clicked.connect(self.update_history)
        self.txt_btn.clicked.connect(self.save_txt)
        self.word_btn.clicked.connect(self.save_docx)

        transcript_box.addLayout(export_row)
        layout.addWidget(transcript, 1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page)

        self.animation = QTimer(self)
        self.animation.setInterval(45)
        self.animation.timeout.connect(self.animate)
        self.animation.start()

        QTimer.singleShot(200, self.load_devices)
        self.update_buttons()

    @staticmethod
    def level_bar(color):
        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(0)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        bar.setStyleSheet(
            "QProgressBar{background:#E7EDF4;border:0;border-radius:4px;}"
            f"QProgressBar::chunk{{background:{color};border-radius:4px;}}"
        )
        return bar

    @staticmethod
    def metric(layout, caption, value, wide=False):
        frame = QFrame()
        frame.setObjectName("V41Metric")
        if wide:
            frame.setMinimumWidth(205)
        else:
            frame.setMinimumWidth(105)

        box = QVBoxLayout(frame)
        box.setContentsMargins(10, 4, 10, 4)
        box.setSpacing(0)

        label = QLabel(caption)
        label.setObjectName("V41MetricLabel")
        result = QLabel(value)
        result.setObjectName("V41MetricValue")

        box.addWidget(label)
        box.addWidget(result)
        layout.addWidget(frame)
        return result

    def toggle_transcript_view(
        self,
        expanded: bool,
    ) -> None:
        self.setup_card.setVisible(not expanded)
        self.session_card.setVisible(not expanded)
        self.expand_button.setText(
            "VOLVER AL PANEL"
            if expanded
            else "AMPLIAR TRANSCRIPCIÓN"
        )

    def refresh_labels(self):
        pass

    def load_devices(self):
        if self.is_running():
            return
        try:
            self.agent_combo.clear()
            self.client_combo.clear()
            inputs = AudioDeviceService.list_inputs()
            outputs = AudioDeviceService.list_outputs()
            for device in inputs:
                label = device.display_name
                if device.is_default:
                    label += "  ·  Predeterminado"
                self.agent_combo.addItem(label, device.__dict__)

            for device in outputs:
                label = device.display_name
                if device.is_default:
                    label += "  ·  Predeterminado"
                self.client_combo.addItem(label, device.__dict__)
            self.agent_status.setText("LISTO" if inputs else "NO DISPONIBLE")
            self.client_status.setText("LISTO" if outputs else "NO DISPONIBLE")
            self.agent_status.setObjectName("V41StatusOk" if inputs else "V41StatusError")
            self.client_status.setObjectName("V41StatusOk" if outputs else "V41StatusError")
            self.agent_status.style().unpolish(self.agent_status)
            self.agent_status.style().polish(self.agent_status)
            self.client_status.style().unpolish(self.client_status)
            self.client_status.style().polish(self.client_status)
            self.mode_changed(self.mode.currentText())
            self.status_changed.emit("DISPOSITIVOS LISTOS")
        except Exception as exc:
            detail = str(exc).strip() or repr(exc)
            QMessageBox.warning(
                self,
                "DISPOSITIVOS DE AUDIO",
                "No fue posible leer los dispositivos de audio.\n\n" + detail,
            )

    def mode_changed(self, mode):
        busy = self.is_running() or self.is_testing()
        use_agent = mode in (self.MODE_BOTH, self.MODE_AGENT)
        use_client = mode in (self.MODE_BOTH, self.MODE_CLIENT)
        self.agent_combo.setEnabled(use_agent and not busy)
        self.agent_test.setEnabled(use_agent and not busy and bool(self.agent_combo.currentData()))
        self.client_combo.setEnabled(use_client and not busy)
        self.client_test.setEnabled(use_client and not busy and bool(self.client_combo.currentData()))
        self.update_buttons()

    def test_agent(self):
        device = self.agent_combo.currentData()
        if device:
            self.start_test("agent", device, None)

    def test_client(self):
        device = self.client_combo.currentData()
        if device:
            self.start_test("client", None, device)

    def start_test(self, mode, agent, client):
        if self.is_running() or self.is_testing():
            return
        self.test_thread = QThread(self)
        self.test_worker = AudioTestWorker(
            mode=mode,
            input_index=agent.get("index") if agent else None,
            input_rate=agent.get("sample_rate", 48000) if agent else 48000,
            output_id=client.get("id", "") if client else "",
            output_name=client.get("raw_name", "") if client else "",
        )
        self.test_worker.moveToThread(self.test_thread)
        if mode == "agent":
            self.test_worker.level_changed.connect(self.set_agent_target)
        else:
            self.test_worker.level_changed.connect(self.set_client_target)
        self.test_thread.started.connect(self.test_worker.run)
        self.test_worker.completed.connect(self.test_completed)
        self.test_worker.failed.connect(self.test_failed)
        self.test_worker.finished.connect(self.test_thread.quit)
        self.test_worker.finished.connect(self.test_worker.deleteLater)
        self.test_thread.finished.connect(self.test_done)
        self.test_thread.finished.connect(self.test_thread.deleteLater)
        self.state.setText("PROBANDO")
        self.test_thread.start()
        self.update_buttons()

    def test_completed(self, message):
        self.state.setText("LISTO")
        QMessageBox.information(self, "PRUEBA DE AUDIO", message)

    def test_failed(self, detail):
        self.state.setText("ERROR")
        QMessageBox.critical(
            self,
            "PRUEBA DE AUDIO",
            "No fue posible completar la prueba.\n\nDetalle técnico: " + detail,
        )

    def test_done(self):
        self.test_thread = None
        self.test_worker = None
        self.update_buttons()

    def agent_sensitivity_changed(self, value: int) -> None:
        self.agent_sensitivity_value.setText(f"{value} %")

        if self.worker is not None:
            self.worker.set_agent_sensitivity(value)

    def client_sensitivity_changed(self, value: int) -> None:
        self.client_sensitivity_value.setText(f"{value} %")

        if self.worker is not None:
            self.worker.set_client_sensitivity(value)

    def noise_filter_changed(self, value: int) -> None:
        self.noise_filter_value.setText(f"{value} %")

        if self.worker is not None:
            self.worker.set_noise_filter(value)

    def scroll_to_latest(self) -> None:
        scrollbar = self.editor.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def start(self):
        if self.is_running() or self.is_testing():
            return
        mode = self.mode.currentText()
        capture_agent = mode in (self.MODE_BOTH, self.MODE_AGENT)
        capture_client = mode in (self.MODE_BOTH, self.MODE_CLIENT)
        agent = self.agent_combo.currentData()
        client = self.client_combo.currentData()
        if capture_agent and not agent:
            QMessageBox.warning(self, "AGENTE", "Selecciona el micrófono del agente.")
            return
        if capture_client and not client:
            QMessageBox.warning(self, "CLIENTE", "Selecciona el audio de la llamada.")
            return

        settings = self.config.load()
        recordings = self.paths.root / "recordings"
        recordings.mkdir(parents=True, exist_ok=True)
        self.recording_path = recordings / (
            "LLAMADA_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".wav"
        )
        self.editor.clear()
        self.history_id = None
        self.time.setText("00:00")
        self.state.setText("INICIANDO")
        self.sources_label.setText("ABRIENDO")
        self.last_speaker = ""
        self.paused = False
        self.pause_btn.setText("PAUSAR")
        self.original_profile = self.engine.profile
        self.engine.set_profile("ALTA")

        self.thread = QThread(self)
        self.worker = UnifiedAudioWorker(
            engine=self.engine,
            base_path=self.recording_path,
            capture_agent=capture_agent,
            capture_client=capture_client,
            input_index=agent.get("index") if agent else None,
            input_rate=agent.get("sample_rate", 48000) if agent else 48000,
            output_id=client.get("id", "") if client else "",
            output_name=client.get("raw_name", "") if client else "",
            language=settings.language,
            uppercase=settings.uppercase,
            agent_label=settings.speaker_one_label,
            client_label=settings.speaker_two_label,
            agent_sensitivity=self.agent_sensitivity.value(),
            client_sensitivity=self.client_sensitivity.value(),
            noise_filter=self.noise_filter.value(),
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.agent_level.connect(self.set_agent_target)
        self.worker.client_level.connect(self.set_client_target)
        self.worker.elapsed.connect(self.set_elapsed)
        self.worker.state.connect(self.set_state)
        self.worker.sources.connect(self.sources_label.setText)
        self.worker.phrase.connect(self.append_phrase)
        self.worker.completed.connect(self.completed)
        self.worker.failed.connect(self.failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread_done)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
        self.update_buttons()

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.state.setText("FINALIZANDO")

    def toggle_pause(self):
        if not self.worker:
            return
        self.paused = not self.paused
        self.worker.set_paused(self.paused)
        self.pause_btn.setText("CONTINUAR" if self.paused else "PAUSAR")
        self.state.setText("PAUSADO" if self.paused else "ESCUCHANDO")

    def failed(self, detail):
        self.state.setText("ERROR")
        QMessageBox.critical(
            self,
            "ERROR DE AUDIO",
            detail or "No fue posible iniciar la captura de audio.",
        )

    def completed(self, agent_path, client_path):
        text = self.editor.toPlainText().strip()
        settings = self.config.load()
        candidates = [Path(path) for path in (agent_path, client_path) if Path(path).exists()]
        if candidates:
            self.recording_path = candidates[0]
        if text and self.recording_path:
            entry = self.history.add_entry(
                source_path=str(self.recording_path),
                text=text,
                profile=settings.live_profile,
                language=settings.language,
            )
            self.history_id = entry["id"]
            self.history_changed.emit()
        self.state.setText("FINALIZADO")

    def thread_done(self):
        self.thread = None
        self.worker = None
        if self.original_profile:
            self.engine.set_profile(self.original_profile)
            self.original_profile = None
        self.agent_target = 0
        self.client_target = 0
        self.update_buttons()

    def set_agent_target(self, value):
        self.agent_target = max(0, min(100, int(value)))

    def set_client_target(self, value):
        self.client_target = max(0, min(100, int(value)))

    def animate(self):
        self.agent_display = self.smooth(self.agent_display, self.agent_target)
        self.client_display = self.smooth(self.client_display, self.client_target)
        self.agent_bar.setValue(int(self.agent_display))
        self.client_bar.setValue(int(self.client_display))
        self.agent_target = int(self.agent_target * 0.80)
        self.client_target = int(self.client_target * 0.80)

    @staticmethod
    def smooth(current, target):
        factor = 0.50 if target > current else 0.14
        value = current + (target - current) * factor
        return 0.0 if value < 0.5 else value

    def set_elapsed(self, seconds):
        minutes, remainder = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        self.time.setText(
            f"{hours:02d}:{minutes:02d}:{remainder:02d}"
            if hours
            else f"{minutes:02d}:{remainder:02d}"
        )

    def set_state(self, state):
        if not self.paused:
            self.state.setText(state)
        self.status_changed.emit(state)

    def append_phrase(
        self,
        speaker,
        text,
        started_at,
        ended_at,
    ):
        settings = self.config.load()
        is_agent = (
            speaker.upper()
            == settings.speaker_one_label.upper()
        )

        cursor = self.editor.textCursor()
        cursor.movePosition(
            QTextCursor.MoveOperation.End
        )

        if self.editor.toPlainText().strip():
            cursor.insertBlock()
            cursor.insertBlock()

        timestamp_format = QTextCharFormat()
        timestamp_format.setForeground(
            QColor("#73839A")
        )
        timestamp_format.setFontPointSize(10)

        speaker_format = QTextCharFormat()
        speaker_format.setForeground(
            QColor(
                "#167F9C"
                if is_agent
                else "#138B68"
            )
        )
        speaker_format.setFontWeight(
            QFont.Weight.Bold
        )
        speaker_format.setFontPointSize(11)

        body_format = QTextCharFormat()
        body_format.setForeground(
            QColor("#10213D")
        )
        body_format.setBackground(
            QColor(
                "#EDF7FA"
                if is_agent
                else "#EDF8F3"
            )
        )
        body_format.setFontPointSize(13)

        timestamp = (
            f"{self.format_time(started_at)}"
            f" – {self.format_time(ended_at)}"
        )

        cursor.insertText(
            timestamp,
            timestamp_format,
        )
        cursor.insertText(
            f"   {speaker}",
            speaker_format,
        )
        cursor.insertBlock()
        cursor.insertText(
            f"  {text}  ",
            body_format,
        )

        self.editor.setTextCursor(cursor)
        self.editor.ensureCursorVisible()
        self.last_speaker = speaker

        # Forzar seguimiento del último bloque después de que Qt actualice
        # la altura del documento y la barra de desplazamiento.
        QTimer.singleShot(0, self.scroll_to_latest)
        QTimer.singleShot(60, self.scroll_to_latest)

    @staticmethod
    def format_time(seconds):
        total = max(0, int(seconds))
        hours, remainder = divmod(total, 3600)
        minutes, secs = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"

    def change_speaker(self, first):
        cursor = self.editor.textCursor()
        cursor.select(cursor.SelectionType.BlockUnderCursor)
        source = cursor.selectedText()
        if not source.strip():
            return
        settings = self.config.load()
        label = settings.speaker_one_label if first else settings.speaker_two_label
        body = re.sub(r"^(AGENTE|CLIENTE)\s*:\s*", "", source, flags=re.IGNORECASE)
        cursor.insertText(f"{label}: {body}")

    def update_history(self):
        if self.history_id:
            self.history.update_text(self.history_id, self.editor.toPlainText())
            self.history_changed.emit()

    def save_txt(self):
        text = self.editor.toPlainText().strip()
        if not text:
            return
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "GUARDAR TXT",
            str(self.default_export(".txt")),
            "ARCHIVO DE TEXTO (*.txt)",
        )
        if destination:
            path = Path(destination).with_suffix(".txt")
            self.export.export_txt(path, text)

    def save_docx(self):
        text = self.editor.toPlainText().strip()
        if not text:
            return
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "GUARDAR WORD",
            str(self.default_export(".docx")),
            "DOCUMENTO WORD (*.docx)",
        )
        if destination:
            path = Path(destination).with_suffix(".docx")
            self.export.export_docx(
                path,
                text,
                self.recording_path.name if self.recording_path else "LLAMADA",
            )

    def default_export(self, suffix):
        stem = self.recording_path.stem if self.recording_path else "LLAMADA"
        return self.paths.exports / f"{stem}_TRANSCRIPCION{suffix}"

    def clear(self):
        if self.is_running():
            return
        self.editor.clear()
        self.recording_path = None
        self.history_id = None
        self.time.setText("00:00")
        self.state.setText("LISTO")
        self.sources_label.setText("LISTAS")
        self.update_buttons()

    def is_running(self):
        return bool(self.thread and self.thread.isRunning())

    def is_testing(self):
        return bool(self.test_thread and self.test_thread.isRunning())

    def update_buttons(self):
        running = self.is_running()
        testing = self.is_testing()
        busy = running or testing
        mode = self.mode.currentText()
        agent_ok = bool(self.agent_combo.currentData())
        client_ok = bool(self.client_combo.currentData())
        text = bool(self.editor.toPlainText().strip())
        use_agent = mode in (self.MODE_BOTH, self.MODE_AGENT)
        use_client = mode in (self.MODE_BOTH, self.MODE_CLIENT)
        self.mode.setEnabled(not busy)
        self.refresh_btn.setEnabled(not busy)
        self.agent_sensitivity.setEnabled(not testing)
        self.client_sensitivity.setEnabled(not testing)
        self.noise_filter.setEnabled(not testing)
        self.agent_combo.setEnabled(not busy and use_agent)
        self.client_combo.setEnabled(not busy and use_client)
        self.agent_test.setEnabled(not busy and use_agent and agent_ok)
        self.client_test.setEnabled(not busy and use_client and client_ok)
        self.start_btn.setEnabled(
            not busy
            and (not use_agent or agent_ok)
            and (not use_client or client_ok)
        )
        self.pause_btn.setEnabled(running)
        self.stop_btn.setEnabled(running)
        self.agent_tag.setEnabled(not busy and text)
        self.client_tag.setEnabled(not busy and text)
        self.hist_btn.setEnabled(not busy and text and bool(self.history_id))
        self.txt_btn.setEnabled(not busy and text)
        self.word_btn.setEnabled(not busy and text)
        self.clear_btn.setEnabled(not busy and (text or self.recording_path is not None))
