from pathlib import Path
from datetime import datetime
import shutil

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QPushButton, QDialog, QFormLayout, QLineEdit, QLabel, QHBoxLayout,
    QWidget, QDialogButtonBox, QFileDialog, QMessageBox
)
from PyQt6.QtGui import QImage
from PyQt6.QtSql import QSqlQuery
from .phone_capture import PhoneCaptureDialog

# --- use Documents\GymSoftware\faces instead of a local 'faces' folder ---
from ctypes import windll, wintypes, byref

def _documents_dir() -> Path:
    try:
        # FOLDERID_Documents
        FOLDERID_Documents = (0xFDD39AD0, 0x238F, 0x46AF, 0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7)
        SHGetKnownFolderPath = windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [wintypes.GUID, wintypes.DWORD, wintypes.HANDLE, wintypes.LPWSTR]
        p = wintypes.LPWSTR()
        SHGetKnownFolderPath(wintypes.GUID(*FOLDERID_Documents), 0, 0, byref(p))
        return Path(p.value)
    except Exception:
        return Path.home() / "Documents"

FACES_DIR = _documents_dir() / "GymSoftware" / "faces"
FACES_DIR.mkdir(parents=True, exist_ok=True)
# --------------------------------------------------------------------------

def _safe_name(text: str) -> str:
    return "".join(ch for ch in text.strip() if ch.isalnum() or ch in (" ", "_", "-")).strip().replace(" ", "_")

def _save_image_as_jpg(src: Path, dst: Path) -> bool:
    img = QImage(str(src))
    if img.isNull():  # fallback to raw copy if Qt can't read
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            return True
        except Exception:
            return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    return img.save(str(dst), "JPG")

class AddClientDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Client")
        self._img = None

        form = QFormLayout(self)
        self.name_edit = QLineEdit()
        self.id_card_edit = QLineEdit()
        self.phone_edit = QLineEdit()

        self.pic_label = QLabel("No file chosen"); self.pic_label.setStyleSheet("color: gray;")
        choose = QPushButton("Choose Picture…"); choose.clicked.connect(self._choose_pic)
        row = QHBoxLayout(); row.addWidget(self.pic_label, 1); row.addWidget(choose, 0)
        
        # NEW: take from phone (ADB)
        take_from_phone = QPushButton("Take picture from phone")
        take_from_phone.clicked.connect(self._take_from_phone)

        form.addRow("Full name:", self.name_edit)
        form.addRow("ID card:", self.id_card_edit)
        form.addRow("Phone:", self.phone_edit)
        form.addRow(QWidget())
        form.addRow(row)
        form.addRow(QWidget(), take_from_phone)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._validate_then_accept); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def _choose_pic(self):
        path, _ = QFileDialog.getOpenFileName(self, "Choose face picture", "", "Images (*.jpg *.jpeg *.png *.bmp)")
        if path:
            self._img = Path(path); self.pic_label.setText(self._img.name); self.pic_label.setStyleSheet("")

    def data(self):
        return {
            "name": self.name_edit.text().strip(),
            "id_card": self.id_card_edit.text().strip(),
            "phone": self.phone_edit.text().strip(),
            "image": self._img
        }

    def _validate_then_accept(self):
        d = self.data()
        if not d["name"] or not d["id_card"] or not d["image"]:
            QMessageBox.warning(self, "Missing data", "Name, ID card and Picture are required.")
            return
        # numeric checks
        try: int(d["id_card"])
        except ValueError:
            QMessageBox.warning(self, "Invalid ID", "ID card must be a number.")
            return
        if d["phone"]:
            try: int(d["phone"])
            except ValueError:
                QMessageBox.warning(self, "Invalid phone", "Phone must be a number (or leave empty).")
                return
        self.accept()
        
    # new function
    def _take_from_phone(self):
        dlg = PhoneCaptureDialog(self)
        if dlg.exec():  # Accepted
            if dlg.selected_path:
                self._img = Path(dlg.selected_path)
                self.pic_label.setText(self._img.name)
                self.pic_label.setStyleSheet("")
        
def _insert_client(db, full_name: str, id_card: int, phone: int | None, picture_path: str) -> tuple[bool, str]:
    q = QSqlQuery(db)
    q.prepare("""
    INSERT INTO Client (full_name, id_card, phone_number, role, picture, created_at)
    VALUES (?, ?, ?, 'client', ?, ?)
""")
    q.addBindValue(full_name)
    q.addBindValue(id_card)
    q.addBindValue(phone)
    q.addBindValue(picture_path)
    q.addBindValue(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    if not q.exec():
        return False, q.lastError().text()
    return True, "ok"

def create_add_client_button(parent, db, on_saved=lambda: None) -> QPushButton:
    """
    Returns a QPushButton wired to open the AddClientDialog,
    copy the image to faces/, insert the row (role='client'), then call on_saved().
    """
    btn = QPushButton("Add Client", parent)

    def on_click():
        dlg = AddClientDialog(parent)
        if dlg.exec():
            d = dlg.data()
            name = d["name"]; id_card = int(d["id_card"])
            phone = int(d["phone"]) if d["phone"] else None
            src = d["image"]

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dst_name = f"{_safe_name(name)}_{id_card}_{ts}.jpg"
            dst = FACES_DIR / dst_name

            if not _save_image_as_jpg(src, dst):
                QMessageBox.critical(parent, "Image Error", "Failed to save picture.")
                return

            ok, err = _insert_client(db, name, id_card, phone, str(dst.as_posix()))
            if not ok:
                dst.unlink(missing_ok=True)
                QMessageBox.critical(parent, "Database Error", f"Could not insert client:\n{err}")
                return

            QMessageBox.information(parent, "Success", "Client added successfully.")
            on_saved()

    btn.clicked.connect(on_click)
    return btn
