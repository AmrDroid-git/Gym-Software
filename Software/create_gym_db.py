import os, sqlite3
from pathlib import Path
from ctypes import windll, wintypes, byref

# --- Windows Documents (robust, localized-safe) ---
def get_documents_dir() -> Path:
    try:
        # FOLDERID_Documents
        FOLDERID_Documents = (0xFDD39AD0, 0x238F, 0x46AF, 0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7)
        _SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
        _SHGetKnownFolderPath.argtypes = [wintypes.GUID, wintypes.DWORD, wintypes.HANDLE, wintypes.LPWSTR]
        path_ptr = wintypes.LPWSTR()
        _SHGetKnownFolderPath(wintypes.GUID(*FOLDERID_Documents), 0, 0, byref(path_ptr))
        return Path(path_ptr.value)
    except Exception:
        return Path.home() / "Documents"

APP_DATA_DIR = get_documents_dir() / "GymSoftware"
FACES_DIR = APP_DATA_DIR / "faces"
OLD_FACES_DIR = FACES_DIR / "oldFaces"
PHONE_INBOX_DIR = APP_DATA_DIR / "phone_inbox"

# create folders if they don't exist
OLD_FACES_DIR.mkdir(parents=True, exist_ok=True)
PHONE_INBOX_DIR.mkdir(parents=True, exist_ok=True)

# --- Connect to SQLite (creates file if not exists) ---
DB_PATH = APP_DATA_DIR / "gym.db"
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("PRAGMA foreign_keys = ON;")

# Create tables
cursor.executescript("""
CREATE TABLE IF NOT EXISTS Client (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    id_card INTEGER UNIQUE NOT NULL,
    phone_number INTEGER,
    role TEXT CHECK(role IN ('owner', 'client', 'coach')) NOT NULL,
    picture TEXT,
    created_at DATE DEFAULT CURRENT_DATE
);
CREATE TABLE IF NOT EXISTS membership_plans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    months INTEGER NOT NULL CHECK(months IN (1, 3, 6, 12)),
    price_decimal INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    plan_id INTEGER,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    price_paid INTEGER NOT NULL,
    FOREIGN KEY (client_id) REFERENCES Client(id) ON DELETE CASCADE,
    FOREIGN KEY (plan_id) REFERENCES membership_plans(id) ON DELETE SET NULL
);
CREATE TABLE IF NOT EXISTS entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    person_id INTEGER NOT NULL,
    FOREIGN KEY (person_id) REFERENCES Client(id) ON DELETE CASCADE
);
""")
conn.commit()
conn.close()

print(f"Database created or verified at: {DB_PATH}")
print(f"Folders created: {FACES_DIR}, {OLD_FACES_DIR}, {PHONE_INBOX_DIR}")
