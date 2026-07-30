from PySide6.QtWidgets import QFrame,QHBoxLayout,QLabel,QPlainTextEdit,QPushButton,QVBoxLayout
from app.ui.pages.common import create_page_header
class FilesPage(QFrame):
    def __init__(self):
        super().__init__(); page,layout=create_page_header("TRANSCRIPCION DE ARCHIVOS","SELECCIONA UN ARCHIVO PARA PREPARAR SU TRANSCRIPCION.")
        card=QFrame(); card.setObjectName("Card"); cl=QVBoxLayout(card); cl.setContentsMargins(22,22,22,22)
        drop=QLabel("ARRASTRA UN AUDIO AQUI O PRESIONA SELECCIONAR ARCHIVO"); drop.setObjectName("Muted"); drop.setMinimumHeight(90)
        buttons=QHBoxLayout(); select=QPushButton("SELECCIONAR ARCHIVO"); select.setObjectName("SecondaryButton"); trans=QPushButton("TRANSCRIBIR"); trans.setObjectName("PrimaryButton"); trans.setEnabled(False); buttons.addWidget(select); buttons.addWidget(trans); buttons.addStretch(1)
        editor=QPlainTextEdit(); editor.setPlaceholderText("LA TRANSCRIPCION APARECERA AQUI EN MAYUSCULAS."); editor.setMinimumHeight(330)
        cl.addWidget(drop); cl.addLayout(buttons); cl.addWidget(editor); layout.addWidget(card); layout.addStretch(1); outer=QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.addWidget(page)
