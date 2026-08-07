import psutil

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
from app.services.paths_service import AppPaths
from app.services.diarization_service import DiarizationService
from app.ui.pages.common import create_page_header


class SettingsPage(QFrame):
    status_changed = Signal(str)
    profile_changed = Signal(str)

    def __init__(self, config_service: ConfigService) -> None:
        super().__init__()
        self._service = config_service
        self._settings = self._service.load()

        page, layout = create_page_header(
            "CONFIGURACIÓN",
            "AJUSTA FIDELIDAD, TEXTO Y NOMBRES DE LOS HABLANTES.",
        )

        recommendation = QFrame()
        recommendation.setObjectName("RecommendationCard")
        recommendation_layout = QVBoxLayout(recommendation)

        ram = psutil.virtual_memory().total / (1024**3)
        recommended = (
            "RÁPIDO"
            if ram < 8
            else "BALANCEADO"
            if ram < 16
            else "PRECISO"
        )

        recommendation_title = QLabel(
            f"RECOMENDACIÓN PARA ESTE EQUIPO: {recommended}"
        )
        recommendation_title.setObjectName("Recommendation")

        recommendation_text = QLabel(
            "LOS MODELOS BASE Y SMALL VIENEN INCLUIDOS. "
            "NO SE DESCARGAN DURANTE EL USO."
        )
        recommendation_text.setWordWrap(True)
        recommendation_text.setObjectName("Muted")
        recommendation_layout.addWidget(recommendation_title)
        recommendation_layout.addWidget(recommendation_text)

        self.model_status = QLabel()
        self.model_status.setWordWrap(True)
        self.model_status.setObjectName("Recommendation")

        verify_button = QPushButton("VERIFICAR MODELOS INSTALADOS")
        verify_button.clicked.connect(self._refresh_model_status)

        recommendation_layout.addWidget(self.model_status)
        recommendation_layout.addWidget(verify_button)

        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        form = QFormLayout()

        self.language = QComboBox()
        self.language.addItems(["ES", "AUTO", "EN"])

        self.engine = QComboBox()
        self.engine.addItems(
            ["FASTER-WHISPER — RECOMENDADO PARA ARCHIVOS"]
        )
        self.engine.setEnabled(False)

        self.profile = QComboBox()
        self.profile.addItems(["RÁPIDO", "BALANCEADO"])

        self.uppercase = QCheckBox(
            "TRANSCRIBIR SIEMPRE EN MAYÚSCULAS"
        )
        self.first = QCheckBox(
            "EL PRIMER HABLANTE CORRESPONDE A LA ETIQUETA 1"
        )
        self.timestamps = QCheckBox("MOSTRAR MARCAS DE TIEMPO")
        self.diarization = QCheckBox(
            "IDENTIFICAR AUTOMÁTICAMENTE AGENTE Y CLIENTE EN AUDIO MONO"
        )

        self.speaker_one = QLineEdit()
        self.speaker_one.setPlaceholderText("EJ.: AGENTE O ENCUESTADOR")
        self.speaker_two = QLineEdit()
        self.speaker_two.setPlaceholderText("EJ.: CLIENTE O ENTREVISTADO")

        form.addRow("IDIOMA", self.language)
        form.addRow("MOTOR DE ARCHIVOS", self.engine)
        form.addRow("PERFIL", self.profile)
        form.addRow("ETIQUETA HABLANTE 1", self.speaker_one)
        form.addRow("ETIQUETA HABLANTE 2", self.speaker_two)
        form.addRow("", self.uppercase)
        form.addRow("", self.first)
        form.addRow("", self.timestamps)
        form.addRow("", self.diarization)

        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setObjectName("Muted")
        self.profile.currentTextChanged.connect(self._update_note)

        save_button = QPushButton("GUARDAR CONFIGURACIÓN")
        save_button.setObjectName("PrimaryButton")
        save_button.clicked.connect(self._save)

        card_layout.addLayout(form)
        card_layout.addWidget(self.note)
        card_layout.addWidget(save_button)
        card_layout.addStretch()

        layout.addWidget(recommendation)
        layout.addWidget(card)
        layout.addStretch()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(page)

        self.language.setCurrentText(self._settings.language)
        self.profile.setCurrentText(self._settings.file_profile)
        self.uppercase.setChecked(self._settings.uppercase)
        self.first.setChecked(self._settings.first_speaker_agent)
        self.timestamps.setChecked(self._settings.show_timestamps)
        self.diarization.setChecked(self._settings.diarization_enabled)
        self.speaker_one.setText(self._settings.speaker_one_label)
        self.speaker_two.setText(self._settings.speaker_two_label)
        self._update_note()
        self._refresh_model_status()

    def _update_note(self) -> None:
        notes = {
            "RÁPIDO": (
                "MODELO BASE: MENOR CONSUMO, PERO PUEDE PERDER FIDELIDAD."
            ),
            "BALANCEADO": (
                "MODELO SMALL: RECOMENDADO PARA ARCHIVOS Y EQUIPOS DE 8 GB."
            ),
        }
        self.note.setText(notes[self.profile.currentText()])

    def _refresh_model_status(self) -> None:
        paths = AppPaths()
        required = (
            "model.bin",
            "config.json",
            "tokenizer.json",
        )

        states = []

        for label, folder in (
            ("BASE / RÁPIDO", paths.models / "base"),
            ("SMALL / BALANCEADO", paths.models / "small"),
        ):
            ready = all(
                (folder / filename).is_file()
                and (folder / filename).stat().st_size > 0
                for filename in required
            )
            state = "LISTO" if ready else "NO DISPONIBLE"
            states.append(f"{label}: {state}")

        voice_ready = DiarizationService().is_ready()
        voice_state = (
            "LISTO"
            if voice_ready
            else "NO DISPONIBLE"
        )
        states.append(
            f"VOCES / AGENTE-CLIENTE: {voice_state}"
        )

        self.model_status.setText(
            "MODELOS INSTALADOS — " + " · ".join(states)
        )

    def _save(self) -> None:
        label_one = self.speaker_one.text().strip()
        label_two = self.speaker_two.text().strip()
        if not label_one or not label_two:
            QMessageBox.warning(
                self,
                "ETIQUETAS INCOMPLETAS",
                "AMBAS ETIQUETAS DE HABLANTES SON OBLIGATORIAS.",
            )
            return
        if label_one.casefold() == label_two.casefold():
            QMessageBox.warning(
                self,
                "ETIQUETAS REPETIDAS",
                "LAS DOS ETIQUETAS DEBEN SER DIFERENTES.",
            )
            return

        settings = AppSettings(
            language=self.language.currentText(),
            transcription_engine="FASTER-WHISPER",
            file_profile=self.profile.currentText(),
            live_profile=self._settings.live_profile,
            uppercase=self.uppercase.isChecked(),
            first_speaker_agent=self.first.isChecked(),
            show_timestamps=self.timestamps.isChecked(),
            speaker_one_label=label_one,
            speaker_two_label=label_two,
            diarization_enabled=self.diarization.isChecked(),
        )
        self._service.save(settings)
        self._settings = settings
        self.profile_changed.emit(settings.file_profile)
        self.status_changed.emit("CONFIGURACIÓN GUARDADA")
        QMessageBox.information(
            self,
            "CONFIGURACIÓN",
            "LA CONFIGURACIÓN FUE GUARDADA CORRECTAMENTE.",
        )
