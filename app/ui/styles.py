APP_STYLE = r"""
* {
    font-family: "Segoe UI";
    font-size: 10pt;
}

QMainWindow, QWidget#Root, QStackedWidget {
    background: #F5F7FA;
    color: #172033;
}

QFrame#Sidebar {
    background: #111827;
    border: none;
}

QLabel#Brand {
    color: #FFFFFF;
    font-size: 20pt;
    font-weight: 800;
    padding: 0 10px;
}

QLabel#Product {
    color: #94A3B8;
    font-size: 9pt;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 0 10px 8px 10px;
}

QLabel#OnlineBadge {
    color: #5EEAD4;
    background: #134E4A;
    border-radius: 8px;
    padding: 8px 10px;
    margin: 0 4px;
    font-size: 8.5pt;
    font-weight: 700;
}

QLabel#Version {
    color: #64748B;
    padding: 8px 10px;
    font-size: 8.5pt;
}

QPushButton#NavButton {
    background: transparent;
    color: #CBD5E1;
    border: none;
    border-radius: 8px;
    text-align: left;
    padding: 12px 14px;
    font-weight: 700;
}

QPushButton#NavButton:hover {
    background: #1F2937;
    color: #FFFFFF;
}

QPushButton#NavButton[active="true"] {
    background: #0F766E;
    color: #FFFFFF;
}

QLabel#PageTitle {
    color: #111827;
    font-size: 22pt;
    font-weight: 800;
}

QLabel#PageSubtitle, QLabel#Muted {
    color: #64748B;
}

QLabel#SectionTitle {
    color: #111827;
    font-size: 12pt;
    font-weight: 800;
}

QLabel#FileName {
    color: #334155;
    font-weight: 600;
}

QFrame#Card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
}

QFrame#DropZone {
    background: #F8FAFC;
    border: 2px dashed #CBD5E1;
    border-radius: 12px;
}

QFrame#DropZone[active="true"] {
    background: #F0FDFA;
    border-color: #0F766E;
}

QLabel#DropTitle {
    color: #334155;
    font-size: 13pt;
    font-weight: 800;
}

QPushButton {
    min-height: 34px;
    border-radius: 8px;
    padding: 5px 14px;
    font-weight: 700;
}

QPushButton#PrimaryButton {
    background: #0F766E;
    color: #FFFFFF;
    border: 1px solid #0F766E;
}
QPushButton#PrimaryButton:hover { background: #115E59; }
QPushButton#PrimaryButton:disabled { background: #94A3B8; border-color: #94A3B8; }

QPushButton#SecondaryButton {
    background: #FFFFFF;
    color: #334155;
    border: 1px solid #CBD5E1;
}
QPushButton#SecondaryButton:hover { background: #F8FAFC; border-color: #94A3B8; }

QPushButton#DangerGhostButton {
    background: transparent;
    color: #B91C1C;
    border: 1px solid #FECACA;
}
QPushButton#DangerGhostButton:hover { background: #FEF2F2; }

QPushButton#AgentButton {
    background: #EFF6FF;
    color: #1D4ED8;
    border: 1px solid #BFDBFE;
}
QPushButton#ClientButton {
    background: #ECFDF5;
    color: #047857;
    border: 1px solid #A7F3D0;
}

QLineEdit, QComboBox, QPlainTextEdit, QListWidget {
    background: #FFFFFF;
    color: #172033;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 8px;
    selection-background-color: #CCFBF1;
    selection-color: #134E4A;
}

QPlainTextEdit#TranscriptEditor {
    font-family: "Segoe UI";
    font-size: 10.5pt;
    line-height: 1.35;
    padding: 14px;
}

QPlainTextEdit#HistoryPreview {
    background: #F8FAFC;
}

QListWidget::item {
    padding: 10px 8px;
    border-bottom: 1px solid #F1F5F9;
}
QListWidget::item:selected {
    background: #CCFBF1;
    color: #134E4A;
    border-radius: 6px;
}

QProgressBar {
    min-height: 8px;
    max-height: 8px;
    background: #E2E8F0;
    border: none;
    border-radius: 4px;
}
QProgressBar::chunk {
    background: #14B8A6;
    border-radius: 4px;
}

QLabel#BadgeNeutral, QLabel#BadgeReady, QLabel#BadgeSuccess, QLabel#BadgeWarning {
    border-radius: 7px;
    padding: 5px 9px;
    font-size: 8.5pt;
    font-weight: 800;
}
QLabel#BadgeNeutral { background: #F1F5F9; color: #475569; }
QLabel#BadgeReady { background: #ECFEFF; color: #0E7490; }
QLabel#BadgeSuccess { background: #ECFDF5; color: #047857; }
QLabel#BadgeWarning { background: #FFF7ED; color: #C2410C; }

QStatusBar {
    background: #FFFFFF;
    color: #64748B;
    border-top: 1px solid #E2E8F0;
}
QStatusBar QLabel { padding-left: 8px; }

QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
