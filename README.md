# WordDesk

A compact native desktop client for Merriam-Webster's Collegiate Dictionary and Collegiate Thesaurus APIs, plus the public Free Dictionary API.

## Run

Python 3.10+ and PySide6 are required.

```bash
python3 -m pip install -r requirements.txt
python3 run.py
```

Open **Settings** in the toolbar and choose the two `.txt` files that contain your API keys. Each file should contain only its key. WordDesk stores the file locations in your desktop settings and reads the keys only when it makes a lookup.

Press `Ctrl+F` to focus the search field. Press `Enter` to search all three services, then move between the Dictionary, Thesaurus, and Free Dictionary tabs. The Free Dictionary API does not require a key.

The app uses the official HTTPS endpoints for Merriam-Webster's Collegiate Dictionary and Collegiate Thesaurus. API access is subject to Merriam-Webster's terms and query limits.
