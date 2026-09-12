from __future__ import annotations

import json
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QUrl, QUrlQuery
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .api import (
    DATAMUSE_ENDPOINT,
    DICTIONARY_ENDPOINT,
    THESAURUS_ENDPOINT,
    parse_datamuse_response,
    parse_response,
)
from .style import STYLESHEET
from .widgets import ResultsView


class KeyPathRow(QWidget):
    def __init__(self, title: str, description: str, setting_key: str, settings: QSettings):
        super().__init__()
        self.setting_key = setting_key
        self.settings = settings
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        label = QLabel(title.upper())
        label.setProperty("class", "sectionLabel")
        layout.addWidget(label)
        helper = QLabel(description)
        helper.setProperty("class", "muted")
        helper.setWordWrap(True)
        layout.addWidget(helper)
        row = QHBoxLayout()
        row.setSpacing(7)
        self.path = QLineEdit(str(settings.value(setting_key, "")))
        self.path.setPlaceholderText("Choose a .txt key file…")
        self.path.setReadOnly(True)
        row.addWidget(self.path, 1)
        choose = QPushButton("Choose file…")
        choose.clicked.connect(self.choose_file)
        row.addWidget(choose)
        layout.addLayout(row)
        self.status = QLabel()
        self.status.setProperty("class", "muted")
        layout.addWidget(self.status)
        self.update_status()

    def choose_file(self) -> None:
        current = self.path.text()
        start = str(Path(current).parent) if current else str(Path.home())
        selected, _ = QFileDialog.getOpenFileName(self, "Choose API key file", start, "Text files (*.txt);;All files (*)")
        if selected:
            self.path.setText(selected)
            self.settings.setValue(self.setting_key, selected)
            self.update_status()

    def update_status(self) -> None:
        value = self.path.text()
        if not value:
            self.status.setText("No file selected")
        elif Path(value).is_file():
            self.status.setText("File found • the key will be read when you search")
        else:
            self.status.setText("File not found • choose a new location")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WordDesk")
        self.resize(920, 680)
        self.setMinimumSize(700, 500)
        self.settings = QSettings("WordDesk", "WordDesk")
        self.network = QNetworkAccessManager(self)
        self._pending: dict[QNetworkReply, tuple[str, int, int]] = {}
        self._request_generation = [0, 0, 0]
        self._build_toolbar()
        self._build_content()
        self._build_statusbar()
        self.search_input.setFocus()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        brand = QLabel("WordDesk")
        brand.setObjectName("brand")
        toolbar.addWidget(brand)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Type a word…")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(260)
        self.search_input.returnPressed.connect(self.search)
        toolbar.addWidget(self.search_input)
        self.search_button = QPushButton("Search")
        self.search_button.setObjectName("searchButton")
        self.search_button.clicked.connect(self.search)
        toolbar.addWidget(self.search_button)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)
        self.settings_action = QAction("Settings", self)
        self.settings_action.setToolTip("API key file settings")
        self.settings_action.triggered.connect(self.show_settings)
        toolbar.addAction(self.settings_action)
        focus_search = QAction(self)
        focus_search.setShortcut(QKeySequence.StandardKey.Find)
        focus_search.triggered.connect(self.focus_search)
        self.addAction(focus_search)

    def _build_content(self) -> None:
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.tabs = QTabWidget()
        self.dictionary_view = ResultsView("Ready for a word", "Search the Collegiate Dictionary for definitions, examples, and word history.")
        self.thesaurus_view = ResultsView("Ready for a word", "Search the Collegiate Thesaurus for meanings, synonyms, and antonyms.")
        self.datamuse_view = ResultsView(
            "Ready for a word",
            "Search definitions from Datamuse. No API key is required.",
        )
        self.dictionary_view.word_requested.connect(self.handle_word_request)
        self.thesaurus_view.word_requested.connect(self.handle_word_request)
        self.datamuse_view.word_requested.connect(self.handle_word_request)
        self.tabs.addTab(self.dictionary_view, "Dictionary")
        self.tabs.addTab(self.thesaurus_view, "Thesaurus")
        self.tabs.addTab(self.datamuse_view, "Datamuse")
        self.stack.addWidget(self.tabs)

        settings_page = QWidget()
        outer = QVBoxLayout(settings_page)
        outer.setContentsMargins(20, 18, 20, 20)
        outer.setSpacing(12)
        top = QHBoxLayout()
        title = QLabel("Settings")
        title.setProperty("class", "settingsTitle")
        top.addWidget(title)
        top.addStretch()
        done = QPushButton("Done")
        done.clicked.connect(self.show_lookup)
        top.addWidget(done)
        outer.addLayout(top)
        subtitle = QLabel("Choose the text file that contains each API key. Only the file locations are saved.")
        subtitle.setProperty("class", "muted")
        subtitle.setWordWrap(True)
        outer.addWidget(subtitle)
        card = QFrame()
        card.setProperty("class", "settingsCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 17, 18, 18)
        card_layout.setSpacing(20)
        self.dictionary_key_row = KeyPathRow(
            "Dictionary key file",
            "A .txt file containing your Merriam-Webster Collegiate Dictionary API key.",
            "keys/dictionary_path",
            self.settings,
        )
        self.thesaurus_key_row = KeyPathRow(
            "Thesaurus key file",
            "A .txt file containing your Merriam-Webster Collegiate Thesaurus API key.",
            "keys/thesaurus_path",
            self.settings,
        )
        card_layout.addWidget(self.dictionary_key_row)
        card_layout.addWidget(self.thesaurus_key_row)
        outer.addWidget(card)
        privacy = QLabel("Keys are read locally and sent only to the Merriam-Webster API over HTTPS.")
        privacy.setProperty("class", "muted")
        outer.addWidget(privacy)
        outer.addStretch()
        self.stack.addWidget(settings_page)

    def _build_statusbar(self) -> None:
        status = QStatusBar()
        self.setStatusBar(status)
        self.status_label = QLabel("Ready")
        status.addWidget(self.status_label, 1)
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedWidth(110)
        self.progress.hide()
        status.addPermanentWidget(self.progress)

    def focus_search(self) -> None:
        self.show_lookup()
        self.search_input.setFocus()
        self.search_input.selectAll()

    def show_settings(self) -> None:
        self.dictionary_key_row.update_status()
        self.thesaurus_key_row.update_status()
        self.stack.setCurrentIndex(1)

    def show_lookup(self) -> None:
        self.stack.setCurrentIndex(0)
        self.search_input.setFocus()

    def handle_word_request(self, word: str) -> None:
        if word == "__settings__":
            self.show_settings()
            return
        self.search_input.setText(word)
        self.search()

    def _read_key(self, setting_name: str, label: str, view: ResultsView) -> str | None:
        path_value = str(self.settings.value(setting_name, ""))
        if not path_value:
            view.show_error(f"{label} key is not set", "Choose its .txt file in Settings, then search again.", True)
            return None
        try:
            key = Path(path_value).read_text(encoding="utf-8-sig").strip()
        except OSError as error:
            view.show_error(f"Could not read the {label.lower()} key", str(error), True)
            return None
        if not key:
            view.show_error(f"{label} key file is empty", "Add the API key to the selected file, then search again.", True)
            return None
        return key

    def _active_view(self) -> ResultsView:
        return (self.dictionary_view, self.thesaurus_view, self.datamuse_view)[self.tabs.currentIndex()]

    def search(self) -> None:
        word = self.search_input.text().strip()
        if not word:
            self.search_input.setFocus()
            return
        if self._pending:
            return
        self.show_lookup()
        configurations = (
            (0, "Dictionary", "keys/dictionary_path", DICTIONARY_ENDPOINT, self.dictionary_view),
            (1, "Thesaurus", "keys/thesaurus_path", THESAURUS_ENDPOINT, self.thesaurus_view),
            (2, "Datamuse", None, DATAMUSE_ENDPOINT, self.datamuse_view),
        )
        started = 0
        for tab, label, setting_name, endpoint, view in configurations:
            key = self._read_key(setting_name, label, view) if setting_name else None
            if setting_name and key is None:
                continue
            self._start_request(word, tab, endpoint, key, view)
            started += 1
        if started:
            self.search_button.setEnabled(False)
            self.progress.show()
            self.status_label.setText("Searching all sources…" if started == 3 else "Searching available sources…")
        else:
            self.status_label.setText("API key files needed")

    def _start_request(
        self,
        word: str,
        tab: int,
        endpoint: str,
        key: str | None,
        view: ResultsView,
    ) -> None:
        self._request_generation[tab] += 1
        generation = self._request_generation[tab]
        if endpoint == DATAMUSE_ENDPOINT:
            url = QUrl(endpoint)
            query = QUrlQuery()
            query.addQueryItem("sp", word)
            query.addQueryItem("qe", "sp")
            query.addQueryItem("md", "dpr")
            query.addQueryItem("ipa", "1")
            query.addQueryItem("max", "1")
            url.setQuery(query)
        else:
            url = QUrl(endpoint + QUrl.toPercentEncoding(word).data().decode("ascii"))
        if key:
            query = QUrlQuery()
            query.addQueryItem("key", key)
            url.setQuery(query)
        request = QNetworkRequest(url)
        request.setRawHeader(b"Accept", b"application/json")
        request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, "WordDesk/1.0")
        request.setTransferTimeout(15_000)
        reply = self.network.get(request)
        self._pending[reply] = (word, tab, generation)
        reply.finished.connect(lambda current=reply: self._request_finished(current))
        service = "Datamuse" if tab == 2 else "Merriam-Webster"
        view.show_loading(word, service)

    def _finish_activity_if_idle(self) -> None:
        if not self._pending:
            self.search_button.setEnabled(True)
            self.progress.hide()

    def _request_finished(self, reply: QNetworkReply) -> None:
        context = self._pending.pop(reply, None)
        if context is None:
            reply.deleteLater()
            return
        word, tab, generation = context
        view = (self.dictionary_view, self.thesaurus_view, self.datamuse_view)[tab]
        is_latest = generation == self._request_generation[tab]
        if not is_latest:
            reply.deleteLater()
            self._finish_activity_if_idle()
            return

        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        if reply.error() != QNetworkReply.NetworkError.NoError:
            if tab != 2 and status_code in (401, 403):
                view.show_error("API key was rejected", "Check that the selected file contains the key for this API.", True)
                self.status_label.setText("Authentication failed")
            elif status_code == 429:
                view.show_error("Request limit reached", "The service has declined more requests for now.")
                self.status_label.setText("Request limit reached")
            else:
                service = "Datamuse" if tab == 2 else "The service"
                view.show_error("Could not complete the lookup", f"{service} reported: {reply.errorString()}")
                self.status_label.setText("Network error")
            reply.deleteLater()
            self._finish_activity_if_idle()
            return

        try:
            payload = json.loads(bytes(reply.readAll()).decode("utf-8"))
            entries, suggestions = parse_datamuse_response(payload) if tab == 2 else parse_response(payload)
            if entries:
                view.show_entries(entries, thesaurus=(tab == 1))
                self.status_label.setText(f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'} for “{word}”")
            elif suggestions:
                view.show_suggestions(word, suggestions)
                self.status_label.setText("No exact match")
            else:
                service = "Datamuse" if tab == 2 else "Merriam-Webster"
                view.show_error("No results", f"{service} returned no entries for “{word}”.")
                self.status_label.setText("No results")
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            view.show_error("Could not read the response", str(error))
            self.status_label.setText("Invalid response")
        finally:
            reply.deleteLater()
        self._finish_activity_if_idle()


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("WordDesk")
    app.setOrganizationName("WordDesk")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
