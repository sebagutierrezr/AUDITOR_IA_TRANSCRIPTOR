from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from app.models.settings import AppSettings
from app.services.config_service import ConfigService
from app.services.diagnostic_service import DiagnosticService
from app.services.system_profile_service import SystemProfileService


class SettingsPage(QFrame):
    status_changed = Signal(str)
    profile_changed = Signal(str)
    performance_changed = Signal(str)

    def __init__(self, config_service: ConfigService) -> None:
        super().__init__()
        self._service = config_service
        self._settings = self._service.load()

        root = QVBoxLayout(self)
        root.setContentsMargins(34, 28, 34, 28)
        root.setSpacing(14)

        title = QLabel("Ajustes")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Configuración universal del equipo, audio y transcripción.")
        subtitle.setObjectName("PageSubtitle")
        root.addWidget(title)
        root.addWidget(subtitle)

        system_card = QFrame()
        system_card.setObjectName("InfoCard")
        system_layout = QVBoxLayout(system_card)
        system_layout.setContentsMargins(18, 16, 18, 16)
        system_title = QLabel("MODO DE RENDIMIENTO")
        system_title.setObjectName("SectionTitle")
        system_form = QFormLayout()
        self.performance = QComboBox()
        self.performance.addItems(["AUTO", "ECO", "BALANCEADO", "CALIDAD"])
        self.performance.setCurrentText(self._settings.performance_mode)
        self.audio_backend = QComboBox()
        self.audio_backend.addItems(["AUTO", "PYAUDIOWPATCH", "SOUNDCARD"])
        self.audio_backend.setCurrentText(self._settings.audio_backend)
        system_form.addRow("Rendimiento", self.performance)
        system_form.addRow("Captura audio del PC", self.audio_backend)
        profile = SystemProfileService.detect(self._settings.performance_mode)
        self.profile_info = QLabel(
            f"Detección actual: {profile.tuning.profile} · {profile.physical_cores} núcleos físicos · "
            f"{profile.ram_gb:.1f} GB RAM. CPU es el modo base; GPU no es requisito."
        )
        self.profile_info.setObjectName("Muted")
        self.profile_info.setWordWrap(True)
        system_layout.addWidget(system_title)
        system_layout.addLayout(system_form)
        system_layout.addWidget(self.profile_info)
        root.addWidget(system_card)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        form = QFormLayout()
        self.language = QComboBox()
        self.language.addItems(["ES", "AUTO", "EN"])
        self.speaker_one = QLineEdit()
        self.speaker_two = QLineEdit()
        self.uppercase = QCheckBox("Texto en mayúsculas")
        self.timestamps = QCheckBox("Mostrar marcas de tiempo")
        self.first = QCheckBox("Si el rol queda ambiguo, considerar al primer hablante como etiqueta 1")
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

        diag = QFrame()
        diag.setObjectName("InfoCard")
        diag_layout = QVBoxLayout(diag)
        diag_layout.setContentsMargins(18, 16, 18, 16)
        row = QHBoxLayout()
        diag_title = QLabel("DIAGNÓSTICO DEL EQUIPO")
        diag_title.setObjectName("SectionTitle")
        self.diag_button = QPushButton("ACTUALIZAR DIAGNÓSTICO")
        self.diag_button.setObjectName("SecondaryButton")
        self.diag_button.clicked.connect(self._refresh_diagnostics)
        row.addWidget(diag_title)
        row.addStretch(1)
        row.addWidget(self.diag_button)
        self.diag_text = QLabel()
        self.diag_text.setObjectName("Muted")
        self.diag_text.setWordWrap(True)
        diag_layout.addLayout(row)
        diag_layout.addWidget(self.diag_text)
        root.addWidget(diag)
        root.addStretch()

        self.language.setCurrentText(self._settings.language)
        self.speaker_one.setText(self._settings.speaker_one_label)
        self.speaker_two.setText(self._settings.speaker_two_label)
        self.uppercase.setChecked(self._settings.uppercase)
        self.timestamps.setChecked(self._settings.show_timestamps)
        self.first.setChecked(self._settings.first_speaker_agent)
        self._refresh_diagnostics()

    def _refresh_diagnostics(self) -> None:
        service = DiagnosticService(
            self.performance.currentText(),
            self.audio_backend.currentText(),
        )
        lines = []
        for item in service.run_quick():
            mark = "✓" if item.ok else ("!" if item.warning else "✕")
            lines.append(f"{mark} {item.name}: {item.detail}")
        self.diag_text.setText("\n".join(lines))

    def _save(self) -> None:
        one = self.speaker_one.text().strip()
        two = self.speaker_two.text().strip()
        if not one or not two or one.casefold() == two.casefold():
            QMessageBox.warning(self, "Etiquetas", "Las dos etiquetas deben existir y ser diferentes.")
            return

        # Conservar preferencias de En vivo y dispositivos de la instalación.
        previous = self._service.load()
        settings = AppSettings(
            language=self.language.currentText(),
            uppercase=self.uppercase.isChecked(),
            first_speaker_agent=self.first.isChecked(),
            show_timestamps=self.timestamps.isChecked(),
            speaker_one_label=one,
            speaker_two_label=two,
            diarization_enabled=True,
            performance_mode=self.performance.currentText(),
            audio_backend=self.audio_backend.currentText(),
            live_auto_follow=previous.live_auto_follow,
            live_agent_sensitivity=previous.live_agent_sensitivity,
            live_client_sensitivity=previous.live_client_sensitivity,
            live_noise_filter=previous.live_noise_filter,
            preferred_input_uid=previous.preferred_input_uid,
            preferred_output_uid=previous.preferred_output_uid,
        )
        self._service.save(settings)
        self._settings = settings
        self.profile_changed.emit("ALTA")
        self.performance_changed.emit(settings.performance_mode)
        self.status_changed.emit("AJUSTES GUARDADOS")
        self._refresh_diagnostics()
        QMessageBox.information(self, "Ajustes", "Configuración guardada.")
