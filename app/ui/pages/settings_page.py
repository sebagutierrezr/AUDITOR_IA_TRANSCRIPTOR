from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.settings import AppSettings
from app.services.agent_reference_service import AgentReferenceService
from app.services.config_service import ConfigService
from app.services.high_precision_transcription_service import HighPrecisionTranscriptionService
from app.services.openai_key_service import OpenAIKeyService
from app.ui.pages.common import create_page_header


class SettingsPage(QWidget):
    status_changed = Signal(str)

    def __init__(self, config_service: ConfigService, parent=None) -> None:
        super().__init__(parent)
        self._config = config_service
        self._key_service = OpenAIKeyService()
        self._reference_service = AgentReferenceService()
        self._transcription_service = HighPrecisionTranscriptionService()

        page, layout = create_page_header(
            "AJUSTES",
            "Configura la conexión, las etiquetas y una referencia opcional de la voz del agente.",
        )

        api_card = QFrame()
        api_card.setObjectName("Card")
        api_layout = QVBoxLayout(api_card)
        api_layout.setContentsMargins(22, 22, 22, 22)
        api_layout.setSpacing(12)

        title = QLabel("CONEXIÓN DE ALTA PRECISIÓN")
        title.setObjectName("SectionTitle")
        api_layout.addWidget(title)
        description = QLabel(
            "Usa gpt-4o-transcribe-diarize para separar hablantes y una segunda clasificación semántica para decidir AGENTE/CLIENTE. Requiere Internet y una API key de OpenAI."
        )
        description.setObjectName("Muted")
        description.setWordWrap(True)
        api_layout.addWidget(description)

        self.key_status = QLabel()
        self.key_status.setObjectName("BadgeNeutral")
        api_layout.addWidget(self.key_status)

        key_row = QHBoxLayout()
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("Pega aquí tu API key")
        save_key = QPushButton("GUARDAR")
        save_key.setObjectName("PrimaryButton")
        save_key.clicked.connect(self._save_key)
        validate_key = QPushButton("VALIDAR")
        validate_key.setObjectName("SecondaryButton")
        validate_key.clicked.connect(self._validate_key)
        delete_key = QPushButton("BORRAR")
        delete_key.setObjectName("DangerGhostButton")
        delete_key.clicked.connect(self._delete_key)
        key_row.addWidget(self.key_input, 1)
        key_row.addWidget(save_key)
        key_row.addWidget(validate_key)
        key_row.addWidget(delete_key)
        api_layout.addLayout(key_row)
        layout.addWidget(api_card)

        voice_card = QFrame()
        voice_card.setObjectName("Card")
        voice_layout = QVBoxLayout(voice_card)
        voice_layout.setContentsMargins(22, 22, 22, 22)
        voice_layout.setSpacing(10)
        voice_title = QLabel("MUESTRA DE VOZ DEL AGENTE · OPCIONAL")
        voice_title.setObjectName("SectionTitle")
        voice_text = QLabel(
            "Si tienes una muestra limpia de 2–10 segundos de la voz del ejecutivo, el servicio puede usarla como hablante conocido. Esto ayuda a fijar el rol AGENTE sin depender solo del texto."
        )
        voice_text.setObjectName("Muted")
        voice_text.setWordWrap(True)
        self.reference_status = QLabel("SIN MUESTRA")
        voice_actions = QHBoxLayout()
        choose_ref = QPushButton("SELECCIONAR MUESTRA")
        choose_ref.setObjectName("SecondaryButton")
        choose_ref.clicked.connect(self._choose_reference)
        remove_ref = QPushButton("QUITAR")
        remove_ref.setObjectName("DangerGhostButton")
        remove_ref.clicked.connect(self._remove_reference)
        voice_actions.addWidget(choose_ref)
        voice_actions.addWidget(remove_ref)
        voice_actions.addStretch()
        voice_layout.addWidget(voice_title)
        voice_layout.addWidget(voice_text)
        voice_layout.addWidget(self.reference_status)
        voice_layout.addLayout(voice_actions)
        layout.addWidget(voice_card)

        prefs_card = QFrame()
        prefs_card.setObjectName("Card")
        prefs_layout = QVBoxLayout(prefs_card)
        prefs_layout.setContentsMargins(22, 22, 22, 22)
        prefs_title = QLabel("PREFERENCIAS")
        prefs_title.setObjectName("SectionTitle")
        prefs_layout.addWidget(prefs_title)
        form = QFormLayout()
        self.language = QComboBox()
        self.language.addItems(["ES", "AUTO", "EN"])
        self.agent_label = QLineEdit()
        self.client_label = QLineEdit()
        self.uppercase = QCheckBox("Transcribir en mayúsculas")
        self.timestamps = QCheckBox("Mostrar marcas de tiempo")
        form.addRow("Idioma", self.language)
        form.addRow("Etiqueta agente", self.agent_label)
        form.addRow("Etiqueta cliente", self.client_label)
        form.addRow("", self.uppercase)
        form.addRow("", self.timestamps)
        prefs_layout.addLayout(form)
        save = QPushButton("GUARDAR PREFERENCIAS")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self._save_preferences)
        prefs_layout.addWidget(save)
        layout.addWidget(prefs_card)
        layout.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page)
        self.refresh()

    def refresh(self) -> None:
        settings = self._config.load()
        self.language.setCurrentText(settings.language)
        self.agent_label.setText(settings.speaker_one_label)
        self.client_label.setText(settings.speaker_two_label)
        self.uppercase.setChecked(settings.uppercase)
        self.timestamps.setChecked(settings.show_timestamps)
        self._refresh_key_status()
        reference = Path(settings.agent_reference_path) if settings.agent_reference_path else None
        self.reference_status.setText(
            f"ACTIVA · {reference.name}" if reference and reference.is_file() else "SIN MUESTRA"
        )

    def _refresh_key_status(self) -> None:
        key = self._key_service.get_key()
        if key:
            self.key_status.setText(f"API KEY CONFIGURADA · {self._key_service.masked(key)}")
            self.key_status.setObjectName("BadgeSuccess")
        else:
            self.key_status.setText("API KEY NO CONFIGURADA")
            self.key_status.setObjectName("BadgeWarning")
        self.key_status.style().unpolish(self.key_status)
        self.key_status.style().polish(self.key_status)

    def _save_key(self) -> None:
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "API Key", "PEGA UNA API KEY ANTES DE GUARDAR.")
            return
        try:
            self._key_service.save_key(key)
        except Exception as exc:
            QMessageBox.critical(self, "API Key", str(exc))
            return
        self.key_input.clear()
        self._refresh_key_status()
        self.status_changed.emit("API KEY GUARDADA")

    def _validate_key(self) -> None:
        key = self.key_input.text().strip() or self._key_service.get_key()
        if not key:
            QMessageBox.warning(self, "API Key", "NO HAY UNA CLAVE PARA VALIDAR.")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            ok, message = self._transcription_service.validate_key(key)
            if ok:
                QMessageBox.information(self, "Conexión", message)
            else:
                QMessageBox.warning(self, "Conexión", message)
        except Exception as exc:
            QMessageBox.critical(self, "Conexión", str(exc))
        finally:
            QApplication.restoreOverrideCursor()

    def _delete_key(self) -> None:
        self._key_service.delete_key()
        self.key_input.clear()
        self._refresh_key_status()
        self.status_changed.emit("API KEY ELIMINADA")

    def _choose_reference(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar muestra de voz del agente",
            "",
            "Audio (*.mp3 *.mp4 *.mpeg *.mpga *.m4a *.wav *.webm *.ogg)",
        )
        if not path:
            return
        try:
            stored = self._reference_service.save_reference(Path(path))
            settings = self._config.load()
            settings.agent_reference_path = str(stored)
            self._config.save(settings)
            self.reference_status.setText(f"ACTIVA · {stored.name}")
            self.status_changed.emit("MUESTRA DE VOZ GUARDADA")
        except Exception as exc:
            QMessageBox.critical(self, "Muestra de voz", str(exc))

    def _remove_reference(self) -> None:
        self._reference_service.delete_reference()
        settings = self._config.load()
        settings.agent_reference_path = ""
        self._config.save(settings)
        self.reference_status.setText("SIN MUESTRA")
        self.status_changed.emit("MUESTRA DE VOZ ELIMINADA")

    def _save_preferences(self) -> None:
        agent = self.agent_label.text().strip()
        client = self.client_label.text().strip()
        if not agent or not client or agent.casefold() == client.casefold():
            QMessageBox.warning(self, "Etiquetas", "AGENTE Y CLIENTE DEBEN TENER ETIQUETAS DIFERENTES.")
            return
        previous = self._config.load()
        settings = AppSettings(
            language=self.language.currentText(),
            uppercase=self.uppercase.isChecked(),
            show_timestamps=self.timestamps.isChecked(),
            speaker_one_label=agent,
            speaker_two_label=client,
            agent_reference_path=previous.agent_reference_path,
            role_model="gpt-5.6-luna",
        )
        self._config.save(settings)
        self.status_changed.emit("PREFERENCIAS GUARDADAS")
        QMessageBox.information(self, "Ajustes", "PREFERENCIAS GUARDADAS.")
