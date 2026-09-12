import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtNetwork import QNetworkReply
from PySide6.QtWidgets import QApplication

from dictionary_app.api import DATAMUSE_ENDPOINT, MOBY_ENDPOINT, WORDNET_ENDPOINT
from dictionary_app.main import MainWindow


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_one_search_starts_all_five_services(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dictionary_key = root / "dictionary.txt"
            thesaurus_key = root / "thesaurus.txt"
            dictionary_key.write_text("dictionary-secret\n", encoding="utf-8")
            thesaurus_key.write_text("thesaurus-secret\n", encoding="utf-8")
            window = MainWindow()
            window.settings = QSettings(str(root / "settings.ini"), QSettings.Format.IniFormat)
            window.settings.setValue("keys/dictionary_path", str(dictionary_key))
            window.settings.setValue("keys/thesaurus_path", str(thesaurus_key))
            calls = []
            window._start_request = lambda word, tab, endpoint, key, view: calls.append((word, tab, endpoint, key))
            window.search_input.setText("calm")

            window.search()

            self.assertEqual(
                calls,
                [
                    ("calm", 0, "https://www.dictionaryapi.com/api/v3/references/collegiate/json/", "dictionary-secret"),
                    ("calm", 1, "https://www.dictionaryapi.com/api/v3/references/thesaurus/json/", "thesaurus-secret"),
                    ("calm", 2, DATAMUSE_ENDPOINT, None),
                    ("calm", 3, WORDNET_ENDPOINT, None),
                    ("calm", 4, MOBY_ENDPOINT, None),
                ],
            )
            window.close()

    def test_wordnet_network_error_starts_fast_fallback(self):
        window = MainWindow()
        reply = MagicMock()
        reply.attribute.return_value = None
        reply.error.return_value = QNetworkReply.NetworkError.TimeoutError
        window._pending[reply] = ("calm", 3, 0, WORDNET_ENDPOINT)
        calls = []
        window._start_request = lambda word, tab, endpoint, key, view: calls.append((word, tab, endpoint, key, view))

        window._request_finished(reply)

        self.assertEqual(calls[0][:4], ("calm", 3, DATAMUSE_ENDPOINT, None))
        self.assertIs(calls[0][4], window.wordnet_view)
        reply.deleteLater.assert_called_once()
        window.close()


if __name__ == "__main__":
    unittest.main()
