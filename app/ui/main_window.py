import os
import psutil
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout,QLabel,QMainWindow,QPushButton,QStackedWidget,QVBoxLayout,QWidget
from app.ui.pages.home_page import HomePage
from app.ui.pages.files_page import FilesPage
from app.ui.pages.live_page import LivePage
from app.ui.pages.settings_page import SettingsPage
from app.ui.styles import APP_STYLE

class MainWindow(QMainWindow):
    def __init__(self, config_service):
        super().__init__(); self.config_service=config_service
        self.setWindowTitle("AUDITOR IA - TRANSCRIPTOR"); self.setMinimumSize(1100,700); self.resize(1280,780); self.setStyleSheet(APP_STYLE)
        self.stack=QStackedWidget(); self.status=QLabel("ESTADO: LISTO"); self.performance=QLabel("CPU: -- % | RAM: -- MB")
        self.build_ui(); self.timer=QTimer(self); self.timer.timeout.connect(self.update_performance); self.timer.start(1500)
    def build_ui(self):
        central=QWidget(); root=QHBoxLayout(central); root.setContentsMargins(0,0,0,0); root.setSpacing(0)
        sidebar=QWidget(); sidebar.setObjectName("Sidebar"); sidebar.setFixedWidth(240); sl=QVBoxLayout(sidebar); sl.setContentsMargins(18,22,18,22)
        brand=QLabel("AUDITOR IA\n- TRANSCRIPTOR"); brand.setObjectName("BrandTitle"); version=QLabel("VERSION 0.1.0 ALPHA"); version.setObjectName("BrandVersion")
        sl.addWidget(brand); sl.addWidget(version); sl.addSpacing(24)
        pages=[("INICIO",HomePage()),("ARCHIVOS",FilesPage()),("EN VIVO",LivePage()),("CONFIGURACION",SettingsPage(self.config_service))]
        self.buttons=[]
        for i,(label,page) in enumerate(pages):
            b=QPushButton(label); b.setObjectName("NavButton"); b.setCheckable(True); b.clicked.connect(lambda checked=False, idx=i:self.select_page(idx)); self.buttons.append(b); sl.addWidget(b); self.stack.addWidget(page)
        sl.addStretch(1)
        content=QWidget(); content.setObjectName("ContentArea"); cl=QVBoxLayout(content); cl.setContentsMargins(0,0,0,0); cl.addWidget(self.stack)
        root.addWidget(sidebar); root.addWidget(content,1); self.setCentralWidget(central); self.statusBar().addWidget(self.status); self.statusBar().addPermanentWidget(self.performance); self.select_page(0)
    def select_page(self,index):
        self.stack.setCurrentIndex(index)
        for i,b in enumerate(self.buttons): b.setChecked(i==index)
    def update_performance(self):
        p=psutil.Process(os.getpid()); ram=p.memory_info().rss/(1024*1024); cpu=p.cpu_percent(None); self.performance.setText(f"CPU: {cpu:.1f} % | RAM: {ram:.0f} MB")
