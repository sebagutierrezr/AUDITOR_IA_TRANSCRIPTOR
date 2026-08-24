from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


def create_page_header(title: str, subtitle: str):
    page = QWidget()
    layout = QVBoxLayout(page)
    layout.setContentsMargins(30, 26, 30, 26)
    layout.setSpacing(16)

    title_label = QLabel(title)
    title_label.setObjectName("PageTitle")
    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("PageSubtitle")
    subtitle_label.setWordWrap(True)

    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)
    return page, layout
