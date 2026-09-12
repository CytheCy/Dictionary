# WordDesk

A compact native desktop client for Merriam-Webster's Collegiate Dictionary and Collegiate Thesaurus APIs, plus no-key results from Datamuse, Open English WordNet, and Moby Thesaurus.

## Run

Python 3.10+ and PySide6 are required.

```bash
python3 -m pip install -r requirements.txt
python3 run.py
```

Open **Settings** in the toolbar and choose the two `.txt` files that contain your API keys. Each file should contain only its key. WordDesk stores the file locations in your desktop settings and reads the keys only when it makes a lookup.

Press `Ctrl+F` to focus the search field. Press `Enter` to search all five services, then move between the Dictionary, Thesaurus, Datamuse, WordNet, and Moby Thesaurus tabs. Datamuse, WordNet, and Moby Thesaurus do not require a key.

The WordNet tab prefers the richer Open English WordNet response. If that service is unavailable or slow, WordDesk automatically falls back to the WordNet-backed definitions supplied by Datamuse.

The app uses the official HTTPS endpoints for Merriam-Webster's Collegiate Dictionary and Collegiate Thesaurus, and the Open English WordNet JSON API. API access is subject to each service's terms and query limits.
