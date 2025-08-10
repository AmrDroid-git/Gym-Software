from datetime import date
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QComboBox, QDateEdit,
    QDialogButtonBox, QMessageBox
)
from PyQt6.QtSql import QSqlQuery
from dateutil.relativedelta import relativedelta


class AddMembershipDialog(QDialog):
    """Dialog to choose membership plan and add to a client."""
    def __init__(self, db, client_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Membership")
        self.resize(360, 160)

        self._db = db
        self._client_id = client_id

        # Normal window buttons
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.plan_combo = QComboBox()
        self._load_plans()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(date.today())

        form.addRow("Plan:", self.plan_combo)
        form.addRow("Start date:", self.start_date)
        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _load_plans(self):
        """Fill combo with (id, name, months, price_decimal)."""
        q = QSqlQuery(self._db)
        if not q.exec("SELECT id, name, months, price_decimal FROM membership_plans ORDER BY name"):
            QMessageBox.critical(self, "DB Error", "Failed to load plans.")
            return
        has_any = False
        while q.next():
            has_any = True
            plan_id = q.value(0)
            name = q.value(1)
            months = q.value(2)
            price = q.value(3)
            label = f"{name} — {months} month(s) — {price}"
            # store all useful data as the item's userData
            self.plan_combo.addItem(label, (plan_id, months, price))
        if not has_any:
            self.plan_combo.addItem("No plans found (create one first)", None)
            self.plan_combo.setEnabled(False)

    def _on_ok(self):
        if not self.plan_combo.isEnabled() or self.plan_combo.currentData() is None:
            QMessageBox.warning(self, "No plans", "You must create a membership plan first.")
            return

        plan_id, months, price = self.plan_combo.currentData()
        start_dt = self.start_date.date().toPyDate()
        end_dt = start_dt + relativedelta(months=months)

        q = QSqlQuery(self._db)
        q.prepare("""
            INSERT INTO memberships (client_id, plan_id, start_date, end_date, price_paid)
            VALUES (?, ?, ?, ?, ?)
        """)
        q.addBindValue(self._client_id)
        q.addBindValue(plan_id)
        q.addBindValue(start_dt.isoformat())
        q.addBindValue(end_dt.isoformat())
        q.addBindValue(price)

        if not q.exec():
            from PyQt6.QtSql import QSqlError
            err = q.lastError().text() if q.lastError() else "Unknown error"
            QMessageBox.critical(self, "DB Error", f"Failed to add membership:\n{err}")
            return

        self.accept()
