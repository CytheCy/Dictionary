import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from dictionary_app.main import MainWindow


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_one_search_starts_both_services(self):
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
            window._start_request = lambda word, tab, endpoint, key, view: calls.append((word, tab, key))
            window.search_input.setText("calm")

            window.search()

            self.assertEqual(calls, [("calm", 0, "dictionary-secret"), ("calm", 1, "thesaurus-secret")])
            window.close()


if __name__ == "__main__":
    unittest.main()
