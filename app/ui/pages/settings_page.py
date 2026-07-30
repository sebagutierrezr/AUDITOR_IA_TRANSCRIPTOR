from PySide6.QtWidgets import QCheckBox,QComboBox,QFormLayout,QFrame,QMessageBox,QPushButton,QVBoxLayout
from app.models.settings import AppSettings
from app.ui.pages.common import create_page_header
class SettingsPage(QFrame):
    def __init__(self,service):
        super().__init__(); self.service=service; self.settings=service.load(); page,layout=create_page_header("CONFIGURACION","AJUSTES GENERALES DEL MOTOR Y DEL TEXTO.")
        card=QFrame(); card.setObjectName("Card"); cl=QVBoxLayout(card); cl.setContentsMargins(22,22,22,22); form=QFormLayout()
        self.language=QComboBox(); self.language.addItems(["ES","AUTO","EN"]); self.engine=QComboBox(); self.engine.addItems(["WHISPER.CPP","OPENAI WHISPER"]); self.file=QComboBox(); self.file.addItems(["RAPIDO","BALANCEADO","PRECISO"]); self.live=QComboBox(); self.live.addItems(["RAPIDO","BALANCEADO"]); self.upper=QCheckBox("TRANSCRIBIR SIEMPRE EN MAYUSCULAS"); self.first=QCheckBox("EL PRIMER HABLANTE ES EL AGENTE"); self.timestamps=QCheckBox("MOSTRAR MARCAS DE TIEMPO")
        for label,w in [("IDIOMA",self.language),("MOTOR",self.engine),("PERFIL DE ARCHIVOS",self.file),("PERFIL EN VIVO",self.live),("",self.upper),("",self.first),("",self.timestamps)]: form.addRow(label,w)
        save=QPushButton("GUARDAR CONFIGURACION"); save.setObjectName("PrimaryButton"); save.clicked.connect(self.save); cl.addLayout(form); cl.addWidget(save); layout.addWidget(card); layout.addStretch(1); outer=QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.addWidget(page); self.load_controls()
    def load_controls(self):
        s=self.settings; self.language.setCurrentText(s.language); self.engine.setCurrentText(s.transcription_engine); self.file.setCurrentText(s.file_profile); self.live.setCurrentText(s.live_profile); self.upper.setChecked(s.uppercase); self.first.setChecked(s.first_speaker_agent); self.timestamps.setChecked(s.show_timestamps)
    def save(self):
        s=AppSettings(self.language.currentText(),self.engine.currentText(),self.file.currentText(),self.live.currentText(),self.upper.isChecked(),self.first.isChecked(),self.timestamps.isChecked()); self.service.save(s); self.settings=s; QMessageBox.information(self,"CONFIGURACION","LA CONFIGURACION FUE GUARDADA CORRECTAMENTE.")
