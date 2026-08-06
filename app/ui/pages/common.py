from PySide6.QtWidgets import QLabel,QVBoxLayout,QWidget

def create_page_header(title,subtitle):
    page=QWidget(); layout=QVBoxLayout(page); layout.setContentsMargins(34,30,34,30); layout.setSpacing(14)
    t=QLabel(title); t.setObjectName("PageTitle"); s=QLabel(subtitle); s.setObjectName("PageSubtitle"); s.setWordWrap(True)
    layout.addWidget(t); layout.addWidget(s); return page,layout
