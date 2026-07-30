from PySide6.QtWidgets import QFrame,QGridLayout,QLabel,QVBoxLayout
from app.ui.pages.common import create_page_header
class HomePage(QFrame):
    def __init__(self):
        super().__init__(); page,layout=create_page_header("INICIO","BASE FUNCIONAL DE AUDITOR IA - TRANSCRIPTOR.")
        grid=QGridLayout(); cards=[("MOTOR PREDETERMINADO","WHISPER.CPP"),("PERFIL DE ARCHIVOS","BALANCEADO"),("PERFIL EN VIVO","RAPIDO"),("ESTADO DEL SISTEMA","LISTO")]
        for i,(title,value) in enumerate(cards):
            card=QFrame(); card.setObjectName("Card"); cl=QVBoxLayout(card); a=QLabel(title); a.setObjectName("Muted"); b=QLabel(value); b.setObjectName("MetricValue"); cl.addWidget(a); cl.addWidget(b); grid.addWidget(card,i//2,i%2)
        layout.addLayout(grid); layout.addStretch(1); outer=QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.addWidget(page)
