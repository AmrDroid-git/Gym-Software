from PyQt6.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QComboBox, QDialogButtonBox, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtSql import QSqlQuery


class ChangeRoleDialog(QDialog):
    def __init__(self, db, client_id: int, current_role: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Change Role")
        self.resize(300, 120)
        self._db = db
        self._client_id = client_id

        # Enable minimize/maximize/close
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.role_combo = QComboBox()
        self.role_combo.addItems(["owner", "client", "coach"])

        # Select current role
        idx = self.role_combo.findText(current_role)
        if idx >= 0:
            self.role_combo.setCurrentIndex(idx)

        form.addRow("Role:", self.role_combo)
        layout.addLayout(form)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_ok(self):
        new_role = self.role_combo.currentText()
        q = QSqlQuery(self._db)
        q.prepare('UPDATE Client SET role = ? WHERE id = ?')
        q.addBindValue(new_role)
        q.addBindValue(self._client_id)

        if not q.exec():
            QMessageBox.critical(self, "Error", f"Failed to change role:\n{q.lastError().text()}")
            return

        self.accept()
