# main.py
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from mainwindow.gym_window import GymMainWindow

DB_PATH = "gym.db"

APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"
ICON_CANDIDATES = [
    ASSETS_DIR / "GymLogo.ico",   # best on Windows taskbar
    ASSETS_DIR / "GymLogo.png",   # fallback if no .ico
]
STYLE_PATH = ASSETS_DIR / "style.qss"


def load_app_icon() -> QIcon:
    for p in ICON_CANDIDATES:
        if p.exists():
            return QIcon(str(p))
    return QIcon()  # empty if nothing found


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Gym Software")
    app.setWindowIcon(load_app_icon())  # sets icon for all windows/dialogs created after this line

    # Load QSS if present
    if STYLE_PATH.exists():
        app.setStyleSheet(STYLE_PATH.read_text(encoding="utf-8"))

    win = GymMainWindow(DB_PATH)
    # ensure the main window also has the global icon (covers very early-created child dialogs)
    win.setWindowIcon(app.windowIcon())
    win.resize(900, 600)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
