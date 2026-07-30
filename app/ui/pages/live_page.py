from PySide6.QtWidgets import QFrame,QGridLayout,QHBoxLayout,QLabel,QPlainTextEdit,QPushButton,QVBoxLayout
from app.ui.pages.common import create_page_header
class LivePage(QFrame):
    def __init__(self):
        super().__init__(); page,layout=create_page_header("TRANSCRIPCION EN VIVO","EL MICROFONO IDENTIFICARA AL AGENTE Y EL AUDIO DEL SISTEMA AL CLIENTE.")
        grid=QGridLayout()
        for col,(title,state) in enumerate([("AGENTE - MICROFONO","NO CONFIGURADO"),("CLIENTE - AUDIO DEL SISTEMA","NO CONFIGURADO")]):
            card=QFrame(); card.setObjectName("Card"); cl=QVBoxLayout(card); cl.addWidget(QLabel(title)); v=QLabel(state); v.setObjectName("MetricValue"); cl.addWidget(v); grid.addWidget(card,0,col)
        controls=QHBoxLayout()
        for label,obj in [("INICIAR","PrimaryButton"),("PAUSAR","SecondaryButton"),("DETENER","SecondaryButton")]:
            b=QPushButton(label); b.setObjectName(obj); b.setEnabled(False); controls.addWidget(b)
        controls.addStretch(1); editor=QPlainTextEdit(); editor.setReadOnly(True); editor.setPlaceholderText("LA TRANSCRIPCION EN VIVO APARECERA AQUI."); editor.setMinimumHeight(300)
        layout.addLayout(grid); layout.addLayout(controls); layout.addWidget(editor); layout.addStretch(1); outer=QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.addWidget(page)
