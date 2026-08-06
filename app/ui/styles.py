APP_STYLE = """
QMainWindow { background: #081426; }
QWidget { font-family: "Segoe UI"; font-size: 14px; }
#Sidebar { background: #0B1830; border-right: 1px solid #1B2B47; }
#BrandTitle { color: #F4F8FF; font-size: 17px; font-weight: 700; }
#BrandVersion { color: #7F93B6; font-size: 11px; }
QPushButton#NavButton { background: transparent; color: #AFC0DB; text-align: left; padding: 13px 14px; border: none; border-radius: 9px; font-weight: 600; }
QPushButton#NavButton:hover { background: #132746; color: #FFFFFF; }
QPushButton#NavButton:checked { background: #123B55; color: #55E0C5; border-left: 3px solid #34CBB1; }
#ContentArea { background: #F3F6FA; }
QLabel#PageTitle { color: #12213A; font-size: 25px; font-weight: 750; }
QLabel#PageSubtitle { color: #61718B; }
QFrame#Card { background: #FFFFFF; border: 1px solid #DDE5EF; border-radius: 13px; }
QFrame#RecommendationCard { background: #EAFBF7; border: 1px solid #9DE8D8; border-radius: 12px; }
QLabel#CardTitle { color: #12213A; font-size: 17px; font-weight: 700; }
QLabel#MetricValue { color: #102039; font-size: 23px; font-weight: 750; }
QLabel#Muted { color: #65758E; }
QLabel#Recommendation { color: #087A67; font-weight: 700; }
QPushButton#PrimaryButton { background: #156F83; color: white; border: none; border-radius: 8px; padding: 11px 18px; font-weight: 700; }
QPushButton#PrimaryButton:hover { background: #105D6F; }
QPushButton#SecondaryButton { background: #FFFFFF; color: #18304F; border: 1px solid #BFCBDD; border-radius: 8px; padding: 10px 16px; font-weight: 600; }
QPushButton#SecondaryButton:hover { background: #EDF3F8; }
QComboBox { background: white; color: #12213A; border: 1px solid #C7D2E0; border-radius: 7px; padding: 8px; min-height: 20px; }
QCheckBox { color: #172A45; spacing: 8px; }
QPlainTextEdit { background: #FFFFFF; color: #172A45; border: 1px solid #CAD5E3; border-radius: 9px; padding: 10px; selection-background-color: #98E5D8; }
QProgressBar { background: #E3EAF2; border: none; border-radius: 6px; text-align: center; color: #18304F; min-height: 20px; }
QProgressBar::chunk { background: #21B89F; border-radius: 6px; }
QStatusBar { background: #0B1830; color: #B8C8DE; }
"""

APP_STYLE += r"""

QFrame#LiveSetupCard,QFrame#LiveSessionCard,QFrame#LiveTranscriptCard{background:#FFFFFF;border:1px solid #D8E2ED;border-radius:14px}
QLabel#LiveSectionTitle{color:#10213D;font-size:14px;font-weight:800} QLabel#LiveSectionSubtitle{color:#6A7A91;font-size:12px}
QLabel#LiveAutoBadge{background:#E7F8F3;color:#087A67;border:1px solid #B4E8DC;border-radius:12px;padding:5px 10px;font-size:11px;font-weight:700}
QLabel#LiveFieldLabel{color:#253A56;font-size:12px;font-weight:750} QFrame#LiveSourceCard{background:#F8FAFC;border:1px solid #DDE5EF;border-radius:12px}
QLabel#LiveSourceTitle{color:#142844;font-size:14px;font-weight:800} QLabel#LiveSourceDesc{color:#74849A;font-size:11px}
QFrame#LiveMetric{background:#F7F9FC;border:1px solid #E1E7EF;border-radius:8px} QLabel#LiveMetricLabel{color:#7A899D;font-size:10px;font-weight:700} QLabel#LiveMetricValue{color:#10213D;font-size:16px;font-weight:800}
QPushButton#LivePrimaryButton{background:#13788C;color:white;border:0;border-radius:9px;padding:11px 18px;font-weight:800} QPushButton#LivePrimaryButton:hover{background:#0E6577}
QPushButton#LiveControlButton{background:white;color:#213B59;border:1px solid #BCCADB;border-radius:9px;padding:10px 14px;font-weight:700} QPushButton#LiveStopButton{background:#FFF5F4;color:#B3423E;border:1px solid #EAC5C2;border-radius:9px;padding:10px 14px;font-weight:700}
QTextEdit#LiveEditor{background:#FFFFFF;color:#142844;border:1px solid #CDD8E5;border-radius:10px;padding:12px;selection-background-color:#BEEDE4}

"""

APP_STYLE += r"""


/* EN VIVO V4 — DISEÑO PROFESIONAL */
QFrame#ProSetupCard,QFrame#ProSessionCard,QFrame#ProTranscriptCard{
    background:#FFFFFF;border:1px solid #D7E1EC;border-radius:14px;
}
QLabel#ProSectionTitle{color:#10213D;font-size:14px;font-weight:800;letter-spacing:.3px;}
QLabel#ProSectionSubtitle{color:#66778F;font-size:12px;}
QLabel#ProFieldLabel{color:#2A3F5A;font-size:12px;font-weight:750;}
QFrame#ProSourceCard{background:#F8FAFC;border:1px solid #DCE5EF;border-radius:12px;}
QLabel#ProSourceTitle{color:#10213D;font-size:14px;font-weight:800;}
QLabel#ProSourceName{color:#334D6A;font-size:12px;font-weight:700;}
QLabel#ProSourceDescription{color:#74849A;font-size:11px;}
QComboBox#ProDeviceCombo,QComboBox#ProModeCombo{
    background:#FFFFFF;color:#142844;border:1px solid #C6D2E0;border-radius:8px;padding:8px 10px;min-height:22px;
}
QLabel#ProStatusNeutral,QLabel#ProStatusOk,QLabel#ProStatusError{
    border-radius:9px;padding:3px 8px;font-size:10px;font-weight:700;
}
QLabel#ProStatusNeutral{background:#EEF2F6;color:#65758E;}
QLabel#ProStatusOk{background:#E6F8F2;color:#087A67;}
QLabel#ProStatusError{background:#FFF0EF;color:#B3423E;}
QPushButton#ProSecondaryButton,QPushButton#ProTestButton,QPushButton#ProControlButton,QPushButton#ProExportButton{
    background:#FFFFFF;color:#203B59;border:1px solid #BCCADB;border-radius:8px;padding:8px 12px;font-size:12px;font-weight:650;
}
QPushButton#ProSecondaryButton:hover,QPushButton#ProTestButton:hover,QPushButton#ProControlButton:hover,QPushButton#ProExportButton:hover{background:#EDF3F8;}
QFrame#ProMetric{background:#F7F9FC;border:1px solid #E1E7EF;border-radius:8px;}
QLabel#ProMetricLabel{color:#78889D;font-size:10px;font-weight:700;}
QLabel#ProMetricValue{color:#10213D;font-size:16px;font-weight:800;}
QPushButton#ProPrimaryButton{background:#13788C;color:#FFFFFF;border:0;border-radius:9px;padding:11px 18px;font-weight:800;}
QPushButton#ProPrimaryButton:hover{background:#0E6577;}
QPushButton#ProStopButton{background:#FFF5F4;color:#B3423E;border:1px solid #EAC5C2;border-radius:9px;padding:10px 14px;font-weight:700;}
QPushButton#ProInlineButton{background:#F7F9FC;color:#49627E;border:1px solid #D1DBE7;border-radius:7px;padding:6px 10px;font-size:11px;font-weight:650;}
QTextEdit#ProLiveEditor{background:#FFFFFF;color:#142844;border:1px solid #CDD8E5;border-radius:10px;padding:12px;selection-background-color:#BEEDE4;}
QPushButton#ProDangerGhost{background:transparent;color:#A84A46;border:1px solid #E2C4C1;border-radius:8px;padding:8px 13px;font-size:12px;font-weight:650;}

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


APP_STYLE += r"""
QFrame#MonoFileSourceCard,
QFrame#MonoFileTranscriptCard {
    background: #FFFFFF;
    border: 1px solid #D7E1EC;
    border-radius: 12px;
}

QLabel#MonoFileSectionTitle {
    color: #10213D;
    font-size: 14px;
    font-weight: 800;
}

QLabel#MonoFileHelp {
    color: #718097;
    font-size: 11px;
}

QLabel#MonoFileLabel {
    color: #167F9C;
    font-size: 11px;
    font-weight: 800;
}

QLabel#MonoFileValue {
    background: #F8FAFD;
    color: #142844;
    border: 1px solid #C8D4E0;
    border-radius: 7px;
    padding: 8px 10px;
}

QLabel#MonoFileStatus {
    background: #E8F7F1;
    color: #087A67;
    border-radius: 9px;
    padding: 5px 9px;
    font-size: 10px;
    font-weight: 750;
}

QLabel#MonoFileDetail {
    color: #60738B;
    font-size: 10px;
}

QLabel#MonoFileState {
    color: #40556F;
    font-size: 11px;
    font-weight: 750;
}

QPushButton#MonoFilePrimary {
    background: #137B8F;
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-size: 12px;
    font-weight: 800;
}

QPushButton#MonoFileSecondary {
    background: #FFFFFF;
    color: #263F5C;
    border: 1px solid #BECBD9;
    border-radius: 8px;
    padding: 8px 13px;
    font-size: 11px;
    font-weight: 700;
}

QPushButton#MonoFileDanger {
    background: #FFF6F5;
    color: #A94742;
    border: 1px solid #E3C2BF;
    border-radius: 8px;
    padding: 9px 13px;
    font-size: 11px;
    font-weight: 700;
}

QProgressBar#MonoFileProgress {
    background: #E6EDF4;
    color: #40556F;
    border: none;
    border-radius: 6px;
    min-height: 18px;
    text-align: center;
}

QProgressBar#MonoFileProgress::chunk {
    background: #1685A1;
    border-radius: 6px;
}

QPlainTextEdit#MonoFileEditor {
    background: #FBFCFE;
    color: #10213D;
    border: 1px solid #BFCEDF;
    border-radius: 10px;
    padding: 16px;
    font-size: 14px;
    selection-background-color: #BDECE2;
}
"""


APP_STYLE += r"""
QPushButton#MonoFileAgentButton {
    background: #E8F5F8;
    color: #167F9C;
    border: 1px solid #B9DDE5;
    border-radius: 7px;
    padding: 7px 12px;
    font-size: 11px;
    font-weight: 750;
}

QPushButton#MonoFileAgentButton:hover {
    background: #DDF0F4;
}

QPushButton#MonoFileClientButton {
    background: #EAF7F2;
    color: #138B68;
    border: 1px solid #BDE1D4;
    border-radius: 7px;
    padding: 7px 12px;
    font-size: 11px;
    font-weight: 750;
}

QPushButton#MonoFileClientButton:hover {
    background: #DFF2EA;
}
"""
