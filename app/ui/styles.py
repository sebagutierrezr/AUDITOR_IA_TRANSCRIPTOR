APP_STYLE = """
QMainWindow { background: #F5F7FB; }
QWidget { font-family: "Segoe UI"; font-size: 13px; color: #172033; }
#Sidebar { background: #111827; border: none; }
#BrandTitle { color: #FFFFFF; font-size: 18px; font-weight: 750; }
#BrandVersion { color: #98A6B9; font-size: 10.5px; }
#SidebarFooter { color: #7F8DA3; font-size: 10.5px; padding-top: 10px; }
QPushButton#NavButton { background: transparent; color: #C8D1DF; border: none; border-radius: 8px; text-align: left; padding: 12px 14px; font-weight: 650; }
QPushButton#NavButton:hover { background: #1F2937; color: #FFFFFF; }
QPushButton#NavButton:checked { background: #1D4ED8; color: #FFFFFF; }
#ContentArea { background: #F5F7FB; }
QLabel#PageTitle { color: #111827; font-size: 26px; font-weight: 750; }
QLabel#PageSubtitle, QLabel#Muted { color: #667085; }
QFrame#Card { background: #FFFFFF; border: 1px solid #E3E8EF; border-radius: 12px; }
QFrame#InfoCard { background: #EEF4FF; border: 1px solid #C7D7FE; border-radius: 12px; }
QFrame#DropZone { background: #FAFBFC; border: 2px dashed #C8D2E0; border-radius: 11px; }
QLabel#DropTitle { color: #344054; font-size: 15px; font-weight: 700; }
QLabel#DropSubtitle { color: #98A2B3; }
QLabel#FileName { color: #344054; font-weight: 650; }
QLabel#SectionTitle { color: #111827; font-size: 16px; font-weight: 700; }
QLabel#ModelStatus { color: #175CD3; font-weight: 650; }
QPushButton#PrimaryButton { background: #1D4ED8; color: #FFFFFF; border: none; border-radius: 8px; padding: 10px 18px; font-weight: 700; }
QPushButton#PrimaryButton:hover { background: #1E40AF; }
QPushButton#PrimaryButton:disabled { background: #AAB7CF; }
QPushButton#SecondaryButton { background: #FFFFFF; color: #344054; border: 1px solid #D0D5DD; border-radius: 8px; padding: 9px 14px; font-weight: 600; }
QPushButton#SecondaryButton:hover { background: #F8FAFC; }
QPushButton#AgentButton { background: #EFF8FF; color: #175CD3; border: 1px solid #B2DDFF; border-radius: 8px; padding: 8px 13px; font-weight: 650; }
QPushButton#ClientButton { background: #ECFDF3; color: #067647; border: 1px solid #ABEFC6; border-radius: 8px; padding: 8px 13px; font-weight: 650; }
QPlainTextEdit { background: #FFFFFF; color: #172033; border: 1px solid #D0D5DD; border-radius: 9px; padding: 12px; selection-background-color: #D1E9FF; }
QProgressBar { background: #EAECF0; border: none; border-radius: 6px; text-align: center; min-height: 20px; color: #344054; }
QProgressBar::chunk { background: #2E90FA; border-radius: 6px; }
QLineEdit, QComboBox { background: #FFFFFF; border: 1px solid #D0D5DD; border-radius: 7px; padding: 8px; }
QCheckBox { spacing: 8px; }
QListWidget { background: #FFFFFF; border: 1px solid #E3E8EF; border-radius: 9px; padding: 4px; }
QListWidget::item { padding: 9px; border-radius: 6px; }
QListWidget::item:selected { background: #EAF2FF; color: #175CD3; }
QSplitter::handle { background: #EEF1F6; width: 1px; }
"""

APP_STYLE += r"""
/* ================================================================
   EN VIVO V4.1 — INTERFAZ PROFESIONAL
   ================================================================ */

QFrame#V41SetupCard,
QFrame#V41SessionCard,
QFrame#V41TranscriptCard {
    background: #FFFFFF;
    border: 1px solid #D8E1EC;
    border-radius: 13px;
}

QLabel#V41SectionTitle {
    color: #10213D;
    font-size: 14px;
    font-weight: 800;
    letter-spacing: 0.3px;
}

QLabel#V41SectionSubtitle {
    color: #6B7B91;
    font-size: 11px;
}

QLabel#V41FieldLabel {
    color: #41546C;
    font-size: 11px;
    font-weight: 750;
}

QLabel#V41AutoBadge {
    background: #E9F8F4;
    color: #087A67;
    border: 1px solid #B9E5DA;
    border-radius: 10px;
    padding: 4px 9px;
    font-size: 10px;
    font-weight: 750;
}

QLabel#V41AgentBadge {
    background: #1685A1;
    color: #FFFFFF;
    border-radius: 15px;
    font-size: 13px;
    font-weight: 800;
}

QLabel#V41ClientBadge {
    background: #15906D;
    color: #FFFFFF;
    border-radius: 15px;
    font-size: 13px;
    font-weight: 800;
}

QLabel#V41SourceTitle {
    color: #132743;
    font-size: 13px;
    font-weight: 800;
}

QLabel#V41SourceHelp {
    color: #74849A;
    font-size: 10px;
}

QLabel#V41MeterLabel {
    color: #7B899B;
    font-size: 9px;
    font-weight: 750;
}

QComboBox#V41ModeCombo,
QComboBox#V41DeviceCombo {
    background: #FFFFFF;
    color: #142844;
    border: 1px solid #C7D2E0;
    border-radius: 7px;
    padding: 7px 10px;
    min-height: 20px;
}

QComboBox#V41DeviceCombo:hover,
QComboBox#V41ModeCombo:hover {
    border-color: #8CA5BE;
}

QPushButton#V41GhostButton,
QPushButton#V41TestButton,
QPushButton#V41ControlButton,
QPushButton#V41ExportButton,
QPushButton#V41InlineButton {
    background: #FFFFFF;
    color: #263F5C;
    border: 1px solid #C2CFDD;
    border-radius: 7px;
    padding: 7px 11px;
    font-size: 11px;
    font-weight: 650;
}

QPushButton#V41GhostButton:hover,
QPushButton#V41TestButton:hover,
QPushButton#V41ControlButton:hover,
QPushButton#V41ExportButton:hover,
QPushButton#V41InlineButton:hover {
    background: #EEF3F8;
    border-color: #AABACA;
}

QPushButton#V41PrimaryButton {
    background: #137B8F;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 17px;
    font-size: 12px;
    font-weight: 800;
}

QPushButton#V41PrimaryButton:hover {
    background: #0F6677;
}

QPushButton#V41StopButton {
    background: #FFF4F3;
    color: #B4423D;
    border: 1px solid #E8C3C0;
    border-radius: 8px;
    padding: 9px 13px;
    font-size: 11px;
    font-weight: 750;
}

QPushButton#V41DangerButton {
    background: transparent;
    color: #A94742;
    border: 1px solid #E1C4C1;
    border-radius: 7px;
    padding: 7px 12px;
    font-size: 11px;
    font-weight: 650;
}

QLabel#V41StatusNeutral,
QLabel#V41StatusOk,
QLabel#V41StatusError {
    border-radius: 9px;
    padding: 3px 8px;
    font-size: 9px;
    font-weight: 800;
}

QLabel#V41StatusNeutral {
    background: #EEF2F6;
    color: #68788D;
}

QLabel#V41StatusOk {
    background: #E6F7F1;
    color: #087A67;
}

QLabel#V41StatusError {
    background: #FFF0EF;
    color: #B4423D;
}

QFrame#V41Metric {
    background: #F7F9FC;
    border: 1px solid #E1E7EF;
    border-radius: 7px;
}

QLabel#V41MetricLabel {
    color: #7B899C;
    font-size: 9px;
    font-weight: 750;
}

QLabel#V41MetricValue {
    color: #10213D;
    font-size: 14px;
    font-weight: 800;
}

QTextEdit#V41LiveEditor {
    background: #FFFFFF;
    color: #142844;
    border: 1px solid #C9D5E2;
    border-radius: 9px;
    padding: 13px;
    font-size: 13px;
    selection-background-color: #BFECE3;
}
"""


APP_STYLE += r"""
/* V4.6 — SOLO ÁREA DE TRANSCRIPCIÓN */
QTextEdit#V46LiveEditor {
    background: #FFFFFF;
    color: #132743;
    border: 1px solid #BFCEDF;
    border-radius: 10px;
    padding: 16px;
    font-size: 14px;
    selection-background-color: #BDECE2;
}

QTextEdit#V46LiveEditor:focus {
    border: 1px solid #6F9BB8;
}

QPushButton#V46ExportButton {
    background: #FFFFFF;
    color: #213B59;
    border: 1px solid #B9C8D8;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 11px;
    font-weight: 700;
}

QPushButton#V46ExportButton:hover {
    background: #EDF3F8;
    border-color: #91A8BE;
}

QPushButton#V46ClearButton {
    background: #FFF7F6;
    color: #A84642;
    border: 1px solid #E4C3C0;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 11px;
    font-weight: 700;
}

QPushButton#V46ClearButton:hover {
    background: #FDEDEC;
}
"""


APP_STYLE += r"""
QLabel#V47SensitivityLabel {
    color: #718097;
    font-size: 10px;
    font-weight: 700;
}

QLabel#V47SensitivityValue {
    color: #29445F;
    font-size: 10px;
    font-weight: 750;
    min-width: 34px;
}

QSlider#V47SensitivitySlider::groove:horizontal {
    height: 6px;
    background: #DFE7F0;
    border-radius: 3px;
}

QSlider#V47SensitivitySlider::sub-page:horizontal {
    background: #17849E;
    border-radius: 3px;
}

QSlider#V47SensitivitySlider::handle:horizontal {
    width: 15px;
    margin: -5px 0;
    background: #FFFFFF;
    border: 2px solid #17849E;
    border-radius: 7px;
}
"""


APP_STYLE += r"""
QPushButton#V471ExpandButton {
    background: #102C4C;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 8px 13px;
    font-size: 11px;
    font-weight: 750;
}

QPushButton#V471ExpandButton:hover,
QPushButton#V471ExpandButton:checked {
    background: #137B8F;
}

QTextEdit#V46LiveEditor {
    background: #FBFCFE;
    color: #10213D;
    border: 1px solid #B8C8D9;
    border-radius: 10px;
    padding: 18px;
    font-size: 14px;
}
"""


APP_STYLE += r"""
QLabel#V472NoiseLabel {
    color: #40556F;
    font-size: 10px;
    font-weight: 800;
}

QLabel#V472NoiseHint {
    color: #7B899C;
    font-size: 9px;
    font-weight: 650;
}

QLabel#V472NoiseValue {
    color: #29445F;
    font-size: 10px;
    font-weight: 750;
    min-width: 36px;
}

QSlider#V472NoiseSlider::groove:horizontal {
    height: 6px;
    background: #DFE7F0;
    border-radius: 3px;
}

QSlider#V472NoiseSlider::sub-page:horizontal {
    background: #586F89;
    border-radius: 3px;
}

QSlider#V472NoiseSlider::handle:horizontal {
    width: 15px;
    margin: -5px 0;
    background: #FFFFFF;
    border: 2px solid #586F89;
    border-radius: 7px;
}
"""
