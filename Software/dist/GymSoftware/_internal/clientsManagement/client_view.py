from pathlib import Path
from datetime import date
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QWidget, QFormLayout, QPushButton
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtSql import QSqlQuery

from clientsManagement.edit_client import ClientEditDialog
from .change_role import ChangeRoleDialog
from .add_membership import AddMembershipDialog   # <-- NEW IMPORT


def _load_client(db, client_id: int) -> dict:
    q = QSqlQuery(db)
    q.prepare("""
        SELECT id, full_name, id_card, phone_number, role, picture, created_at
        FROM Client WHERE id = ?
    """)
    q.addBindValue(client_id)
    q.exec()
    if q.next():
        return {
            "id": q.value(0),
            "full_name": q.value(1),
            "id_card": q.value(2),
            "phone_number": q.value(3),
            "role": q.value(4),
            "picture": q.value(5),
            "created_at": q.value(6),
        }
    return {}


def _latest_membership_end(db, client_id: int) -> str | None:
    q = QSqlQuery(db)
    q.prepare("SELECT MAX(date(end_date)) FROM memberships WHERE client_id = ?")
    q.addBindValue(client_id)
    if not q.exec():
        return None
    if q.next():
        val = q.value(0)
        return str(val) if val else None
    return None


def _status_from_end(end_str: str | None) -> tuple[str, str]:
    if not end_str:
        return ("Not allowed", "color: #b00020;")
    try:
        end_dt = date.fromisoformat(end_str)
    except ValueError:
        return ("Not allowed", "color: #b00020;")
    today = date.today()
    if end_dt >= today:
        return ("Allowed to enter", "color: #0a7b34;")
    return ("Not allowed", "color: #b00020;")


class ClientInfoDialog(QDialog):
    # Signal emitted when something changes (role/edit/add membership) so the main table can refresh
    refreshed = pyqtSignal()

    def __init__(self, db, client_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Client Info")
        self.setMinimumSize(560, 420)
        self._db = db
        self._client_id = client_id
        self._data = _load_client(db, client_id)

        # Normal window controls
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        root = QVBoxLayout(self)
        top = QHBoxLayout()

        # Picture
        self.pic_label = QLabel()
        self.pic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pic_label.setFixedSize(220, 220)
        self._set_picture(self._data.get("picture"))
        top.addWidget(self.pic_label, 0)

        # Info form
        self.lbl_id = QLabel(str(self._data.get("id", "")))
        self.lbl_name = QLabel(str(self._data.get("full_name", "")))
        self.lbl_card = QLabel(str(self._data.get("id_card", "")))
        self.lbl_phone = QLabel(str(self._data.get("phone_number", "")))
        self.lbl_role = QLabel(str(self._data.get("role", "")))
        self.lbl_created = QLabel(str(self._data.get("created_at", "")))

        latest_end = _latest_membership_end(self._db, self._client_id)
        self.lbl_membership_end = QLabel(latest_end if latest_end else "No memberships yet")
        status_text, status_color = _status_from_end(latest_end)
        self.lbl_status = QLabel(status_text)
        self.lbl_status.setStyleSheet(status_color)

        form = QFormLayout()
        form.addRow("ID:", self.lbl_id)
        form.addRow("Full name:", self.lbl_name)
        form.addRow("ID card:", self.lbl_card)
        form.addRow("Phone:", self.lbl_phone)
        form.addRow("Role:", self.lbl_role)
        form.addRow("Created at:", self.lbl_created)
        form.addRow("Membership ends:", self.lbl_membership_end)
        form.addRow("Status:", self.lbl_status)
        right = QWidget()
        right.setLayout(form)
        top.addWidget(right, 1)

        root.addLayout(top)

        # Buttons
        btn_row = QHBoxLayout()
        edit_btn = QPushButton("Edit info")
        change_role_btn = QPushButton("Change role")
        add_membership_btn = QPushButton("Add membership")   # <-- NEW BUTTON
        close_btn = QPushButton("Close")

        edit_btn.clicked.connect(self._open_edit)
        change_role_btn.clicked.connect(self._open_change_role)
        add_membership_btn.clicked.connect(self._open_add_membership)  # <-- CONNECT
        close_btn.clicked.connect(self.reject)

        btn_row.addStretch(1)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(change_role_btn)
        btn_row.addWidget(add_membership_btn)  # <-- ADD TO UI
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)

    # -------- helpers --------
    def _set_picture(self, path: str | None):
        if not path:
            self.pic_label.setText("No picture")
            return
        p = Path(path)
        if not p.exists():
            self.pic_label.setText("Picture not found")
            return
        pm = QPixmap(str(p))
        if pm.isNull():
            self.pic_label.setText("Invalid image")
            return
        self.pic_label.setPixmap(pm.scaled(
            self.pic_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

    def _refresh_labels(self):
        self._data = _load_client(self._db, self._client_id)
        self.lbl_name.setText(str(self._data.get("full_name", "")))
        self.lbl_card.setText(str(self._data.get("id_card", "")))
        self.lbl_phone.setText(str(self._data.get("phone_number", "")))
        self.lbl_role.setText(str(self._data.get("role", "")))
        self._set_picture(self._data.get("picture"))
        latest_end = _latest_membership_end(self._db, self._client_id)
        self.lbl_membership_end.setText(latest_end if latest_end else "No memberships yet")
        status_text, status_color = _status_from_end(latest_end)
        self.lbl_status.setText(status_text)
        self.lbl_status.setStyleSheet(status_color)

    # -------- actions --------
    def _open_edit(self):
        dlg = ClientEditDialog(self._db, self._data, self)
        if dlg.exec():
            self._refresh_labels()
            self.refreshed.emit()   # keep dialog open, refresh main table

    def _open_change_role(self):
        dlg = ChangeRoleDialog(self._db, self._client_id, self._data.get("role", ""), self)
        if dlg.exec():
            self._refresh_labels()
            self.refreshed.emit()   # keep dialog open, refresh main table

    def _open_add_membership(self):
        dlg = AddMembershipDialog(self._db, self._client_id, self)
        if dlg.exec():
            self._refresh_labels()
            self.refreshed.emit()   # keep dialog open, refresh main table
