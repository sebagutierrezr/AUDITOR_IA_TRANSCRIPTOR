from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.models.settings import AppSettings
from app.services.config_service import ConfigService
from app.services.diarization_service import DiarizationService
from app.services.speaker_rescue_service import SpeakerRescueService


class SettingsPage(QFrame):
    status_changed = Signal(str)
    profile_changed = Signal(str)

    def __init__(self, config_service: ConfigService) -> None:
        super().__init__()
        self._service = config_service
        self._settings = self._service.load()

        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 28)
        root.setSpacing(16)

        title = QLabel("Ajustes")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Solo las opciones que afectan el resultado.")
        subtitle.setObjectName("PageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        info = QFrame()
        info.setObjectName("InfoCard")
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(18, 16, 18, 16)
        info_title = QLabel("Alta precisión local")
        info_title.setObjectName("SectionTitle")
        info_text = QLabel(
            "Transcripción: Faster-Whisper Small\n"
            "Hablantes: Community-1 + ECAPA Rescue\n"
            "Funcionamiento: local, sin API y sin pagos por uso."
        )
        info_text.setObjectName("Muted")
        self._model_status = QLabel()
        self._model_status.setObjectName("ModelStatus")
        info_layout.addWidget(info_title)
        info_layout.addWidget(info_text)
        info_layout.addWidget(self._model_status)
        root.addWidget(info)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        form = QFormLayout()

        self.language = QComboBox()
        self.language.addItems(["ES", "AUTO", "EN"])
        self.speaker_one = QLineEdit()
        self.speaker_two = QLineEdit()
        self.uppercase = QCheckBox("Texto en mayúsculas")
        self.timestamps = QCheckBox("Mostrar marcas de tiempo")
        self.first = QCheckBox(
            "Si el rol queda ambiguo, considerar al primer hablante como etiqueta 1"
        )

        form.addRow("Idioma", self.language)
        form.addRow("Etiqueta 1", self.speaker_one)
        form.addRow("Etiqueta 2", self.speaker_two)
        form.addRow("", self.uppercase)
        form.addRow("", self.timestamps)
        form.addRow("", self.first)

        save = QPushButton("Guardar ajustes")
        save.setObjectName("PrimaryButton")
        save.clicked.connect(self._save)
        card_layout.addLayout(form)
        card_layout.addWidget(save)
        root.addWidget(card)
        root.addStretch()

        self.language.setCurrentText(self._settings.language)
        self.speaker_one.setText(self._settings.speaker_one_label)
        self.speaker_two.setText(self._settings.speaker_two_label)
        self.uppercase.setChecked(self._settings.uppercase)
        self.timestamps.setChecked(self._settings.show_timestamps)
        self.first.setChecked(self._settings.first_speaker_agent)
        self._refresh_status()

    def _refresh_status(self) -> None:
        community = DiarizationService().is_ready()
        rescue = SpeakerRescueService().is_ready()
        self._model_status.setText(
            "Community-1: " + ("LISTO" if community else "FALTA")
            + "  ·  ECAPA: " + ("LISTO" if rescue else "FALTA")
        )

    def _save(self) -> None:
        one = self.speaker_one.text().strip()
        two = self.speaker_two.text().strip()
        if not one or not two or one.casefold() == two.casefold():
            QMessageBox.warning(
                self, "Etiquetas", "Las dos etiquetas deben existir y ser diferentes."
            )
            return

        settings = AppSettings(
            language=self.language.currentText(),
            uppercase=self.uppercase.isChecked(),
            first_speaker_agent=self.first.isChecked(),
            show_timestamps=self.timestamps.isChecked(),
            speaker_one_label=one,
            speaker_two_label=two,
            diarization_enabled=True,
        )
        self._service.save(settings)
        self._settings = settings
        self.profile_changed.emit("ALTA")
        self.status_changed.emit("AJUSTES GUARDADOS")
        QMessageBox.information(self, "Ajustes", "Configuración guardada.")
