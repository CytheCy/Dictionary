STYLESHEET = """
QWidget {
    background: #202328;
    color: #e7e9ec;
    font-family: "Noto Sans", "Segoe UI", sans-serif;
    font-size: 13px;
}
QLabel { background: transparent; }
QToolBar > QWidget { background: transparent; }
QMainWindow, QStackedWidget { background: #1c1f23; }
QToolBar {
    background: #25282d;
    border: none;
    border-bottom: 1px solid #34383f;
    spacing: 5px;
    padding: 5px 8px;
}
QToolBar QLabel#brand { font-size: 13px; font-weight: 700; color: #f1f3f5; padding-right: 8px; }
QLineEdit {
    background: #181b1f;
    border: 1px solid #3b4048;
    border-radius: 8px;
    padding: 7px 10px;
    selection-background-color: #4f8cff;
}
QLineEdit:focus { border-color: #4f8cff; }
QPushButton, QToolButton {
    background: #30343a;
    border: 1px solid #444951;
    border-radius: 8px;
    padding: 6px 11px;
}
QPushButton:hover, QToolButton:hover { background: #393e45; border-color: #555b65; }
QPushButton:pressed, QToolButton:pressed { background: #292d32; }
QPushButton#searchButton {
    background: #4f8cff;
    color: white;
    border-color: #4f8cff;
    font-weight: 600;
    padding-left: 16px;
    padding-right: 16px;
}
QPushButton#searchButton:hover { background: #6098ff; }
QPushButton.secondary { background: #2c3036; }
QPushButton.wordChip {
    color: #a9c7ff;
    background: #283449;
    border-color: #354a6d;
    padding: 3px 8px;
    font-size: 12px;
}
QPushButton.suggestion { text-align: left; padding: 8px 11px; }
QTabWidget::pane { border: none; background: #1c1f23; }
QTabBar { background: #25282d; }
QTabBar::tab {
    background: #25282d;
    color: #9da3ad;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 9px 18px 8px 18px;
    font-weight: 600;
}
QTabBar::tab:selected { color: #f2f4f7; border-bottom-color: #4f8cff; }
QTabBar::tab:hover:!selected { color: #c9cdd3; }
QScrollArea, QScrollArea > QWidget > QWidget { background: #1c1f23; }
QFrame.resultCard {
    background: #25282d;
    border: 1px solid #353940;
    border-radius: 8px;
}
QLabel.resultHeadword { font-size: 22px; font-weight: 650; color: #f5f6f7; }
QLabel.partOfSpeech {
    background: #30343b;
    color: #b8bdc6;
    border-radius: 5px;
    padding: 3px 6px;
    font-size: 10px;
    font-weight: 700;
}
QLabel.pronunciation { color: #aeb5bf; font-size: 12px; }
QLabel.sectionLabel { color: #858d99; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
QLabel.senseNumber { color: #758092; font-weight: 600; }
QLabel.example { color: #aeb4be; font-style: italic; padding-left: 2px; }
QLabel.muted { color: #9198a3; }
QLabel.emptyTitle { color: #d8dbe0; font-size: 16px; font-weight: 600; }
QFrame.settingsCard { background: #25282d; border: 1px solid #353940; border-radius: 8px; }
QLabel.settingsTitle { font-size: 18px; font-weight: 650; }
QStatusBar { background: #25282d; color: #858d99; border-top: 1px solid #34383f; font-size: 11px; }
QProgressBar { border: none; background: #30343a; max-height: 2px; min-height: 2px; }
QProgressBar::chunk { background: #4f8cff; }
QScrollBar:vertical { width: 9px; background: transparent; margin: 2px; }
QScrollBar::handle:vertical { background: #454a52; border-radius: 4px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
