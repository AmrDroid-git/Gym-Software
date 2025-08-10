from pathlib import Path
from datetime import datetime
import shutil

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QLabel, QHBoxLayout, QWidget,
    QDialogButtonBox, QFileDialog, QPushButton, QMessageBox
)
from PyQt6.QtGui import QImage
from PyQt6.QtSql import QSqlQuery

FACES_DIR = Path("faces")
OLD_FACES_DIR = FACES_DIR / "oldFaces"
OLD_FACES_DIR.mkdir(parents=True, exist_ok=True)

def _safe_name(text: str) -> str:
    return "".join(ch for ch in text.strip() if ch.isalnum() or ch in (" ", "_", "-")).strip().replace(" ", "_")

def _save_image_as_jpg(src_path: Path, dest_path: Path) -> bool:
    img = QImage(str(src_path))
    if img.isNull():
        return False
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    return img.save(str(dest_path), "JPG")

def _update_client_row(db, client_id: int, name: str, id_card: int, phone: int | None) -> tuple[bool,str]:
    q = QSqlQuery(db)
    q.prepare("""
        UPDATE Client
        SET full_name = ?, id_card = ?, phone_number = ?
        WHERE id = ?
    """)
    q.addBindValue(name)
    q.addBindValue(id_card)
    q.addBindValue(phone)
    q.addBindValue(client_id)
    ok = q.exec()
    return ok, ("" if ok else q.lastError().text())

def _replace_picture(db, client_id: int, old_path_str: str | None, new_src: Path, full_name: str, id_card: int) -> tuple[bool,str]:
    # pick final destination (same filename if old exists; else standard name)
    if old_path_str:
        dest_path = Path(old_path_str)
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = FACES_DIR / f"{_safe_name(full_name)}_{id_card}_{ts}.jpg"

    tmp_path = dest_path.with_suffix(".tmp.jpg")
    if not _save_image_as_jpg(new_src, tmp_path):
        tmp_path.unlink(missing_ok=True)
        return False, "Failed to read/encode the new picture."

    if old_path_str:
        old_path = Path(old_path_str)
        if old_path.exists():
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            moved_name = f"{old_path.stem}__OLD_{ts}{old_path.suffix}"
            try:
                shutil.move(str(old_path), str(OLD_FACES_DIR / moved_name))
            except Exception as e:
                # not fatal, just warn
                pass

    try:
        tmp_path.replace(dest_path)
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        return False, f"Could not finalize new picture: {e}"

    # ensure DB has picture path if it was missing
    if not old_path_str:
        q = QSqlQuery(db)
        q.prepare("UPDATE Client SET picture = ? WHERE id = ?")
        q.addBindValue(str(dest_path.as_posix()))
        q.addBindValue(client_id)
        if not q.exec():
            return False, "Picture saved, but DB path update failed."
    return True, ""

class ClientEditDialog(QDialog):
    """Modal dialog to edit name, id card, phone and optionally replace picture."""
    def __init__(self, db, client: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Client")
        self._db = db
        self._client = client
        self._new_picture_path: Path | None = None

        form = QFormLayout(self)
        self.name_edit = QLineEdit(str(client.get("full_name", "")))
        self.id_card_edit = QLineEdit(str(client.get("id_card", "")))
        self.phone_edit = QLineEdit("" if client.get("phone_number") in (None, "") else str(client.get("phone_number")))

        self.pic_label = QLabel(Path(client.get("picture") or "").name or "No picture")
        self.pic_label.setStyleSheet("color: gray;" if not client.get("picture") else "")
        choose_btn = QPushButton("Choose New Picture…"); choose_btn.clicked.connect(self._choose_pic)

        row = QHBoxLayout(); row.addWidget(self.pic_label, 1); row.addWidget(choose_btn, 0)

        form.addRow("Full name:", self.name_edit)
        form.addRow("ID card:", self.id_card_edit)
        form.addRow("Phone:", self.phone_edit)
        form.addRow(QWidget()); form.addRow(row)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._save); btns.rejected.connect(self.reject)
        form.addRow(btns)

    def _choose_pic(self):
        f, _ = QFileDialog.getOpenFileName(self, "Choose new picture", "", "Images (*.jpg *.jpeg *.png *.bmp)")
        if f:
            self._new_picture_path = Path(f)
            self.pic_label.setText(self._new_picture_path.name)
            self.pic_label.setStyleSheet("")

    def _save(self):
        name = self.name_edit.text().strip()
        id_card_txt = self.id_card_edit.text().strip()
        phone_txt = self.phone_edit.text().strip()
        if not name or not id_card_txt:
            QMessageBox.warning(self, "Missing data", "Name and ID card are required."); return
        try:
            id_card = int(id_card_txt)
        except ValueError:
            QMessageBox.warning(self, "Invalid ID", "ID card must be a number."); return
        phone_val = None
        if phone_txt:
            try: phone_val = int(phone_txt)
            except ValueError:
                QMessageBox.warning(self, "Invalid phone", "Phone must be a number (or empty)."); return

        ok, err = _update_client_row(self._db, self._client["id"], name, id_card, phone_val)
        if not ok:
            QMessageBox.critical(self, "Database Error", err); return

        if self._new_picture_path:
            ok, err = _replace_picture(self._db, self._client["id"], self._client.get("picture"),
                                       self._new_picture_path, name, id_card)
            if not ok:
                QMessageBox.critical(self, "Image Error", err); return

        self.accept()
