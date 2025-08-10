import sys
from PyQt6.QtWidgets import QApplication
from gym_window import GymMainWindow

DB_PATH = "gym.db"

def main():
    app = QApplication(sys.argv)
    w = GymMainWindow(DB_PATH)
    w.resize(900, 600)  # normal size
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
