# main.py
import sys, os
from pathlib import Path
from ctypes import windll, wintypes, byref
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from mainwindow.gym_window import GymMainWindow

# --- robust Documents path ---
def get_documents_dir() -> Path:
    try:
        FOLDERID_Documents = (0xFDD39AD0, 0x238F, 0x46AF, 0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7)
        _SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
        _SHGetKnownFolderPath.argtypes = [wintypes.GUID, wintypes.DWORD, wintypes.HANDLE, wintypes.LPWSTR]
        path_ptr = wintypes.LPWSTR()
        _SHGetKnownFolderPath(wintypes.GUID(*FOLDERID_Documents), 0, 0, byref(path_ptr))
        return Path(path_ptr.value)
    except Exception:
        return Path.home() / "Documents"

APP_DATA_DIR = get_documents_dir() / "GymSoftware"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = str(APP_DATA_DIR / "gym.db")   # <- app will always read/write here

# Handle assets in frozen or source mode
def base_path() -> Path:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

APP_DIR = base_path()
ASSETS_DIR = APP_DIR / "assets"
ICON_CANDIDATES = [ASSETS_DIR / "GymLogo.ico", ASSETS_DIR / "GymLogo.png"]
STYLE_PATH = ASSETS_DIR / "style.qss"

def load_app_icon() -> QIcon:
    for p in ICON_CANDIDATES:
        if p.exists():
            return QIcon(str(p))
    return QIcon()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Gym Software")
    app.setWindowIcon(load_app_icon())

    if STYLE_PATH.exists():
        app.setStyleSheet(STYLE_PATH.read_text(encoding="utf-8"))

    win = GymMainWindow(DB_PATH)
    win.setWindowIcon(app.windowIcon())
    win.resize(900, 600)
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
