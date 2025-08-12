# income_summary.py
from __future__ import annotations
from dataclasses import dataclass

from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit,
    QDialogButtonBox, QMessageBox, QWidget
)
from PyQt6.QtSql import QSqlQuery


@dataclass
class DateRange:
    start: str  # 'YYYY-MM-DD'
    end: str    # 'YYYY-MM-DD'


class DateRangeDialog(QDialog):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Select period")
        layout = QVBoxLayout(self)

        row = QHBoxLayout()
        row.addWidget(QLabel("From:"))
        self.from_edit = QDateEdit(self)
        self.from_edit.setDisplayFormat("yyyy-MM-dd")
        self.from_edit.setCalendarPopup(True)
        self.from_edit.setDate(QDate.currentDate().addMonths(-1))
        row.addWidget(self.from_edit)
        layout.addLayout(row)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("To:"))
        self.to_edit = QDateEdit(self)
        self.to_edit.setDisplayFormat("yyyy-MM-dd")
        self.to_edit.setCalendarPopup(True)
        self.to_edit.setDate(QDate.currentDate())
        row2.addWidget(self.to_edit)
        layout.addLayout(row2)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def value(self) -> DateRange:
        return DateRange(
            start=self.from_edit.date().toString("yyyy-MM-dd"),
            end=self.to_edit.date().toString("yyyy-MM-dd"),
        )


def show_income_for_period(db, parent: QWidget | None = None):
    """Ask for a date range, then show a message box with total income + count."""
    dlg = DateRangeDialog(parent)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return
    rng = dlg.value()
    if rng.end < rng.start:
        QMessageBox.warning(parent, "Invalid period", "'To' date must be after 'From' date.")
        return

    q = QSqlQuery(db)
    q.prepare("""
        SELECT COALESCE(SUM(price_paid), 0) AS total_income,
               COUNT(*) AS num_memberships
        FROM memberships
        WHERE start_date BETWEEN ? AND ?
    """)
    q.addBindValue(rng.start)
    q.addBindValue(rng.end)

    if not q.exec() or not q.next():
        QMessageBox.critical(parent, "Error", "Failed to query income.")
        return

    total_income = q.value(0) or 0
    count = q.value(1) or 0

    QMessageBox.information(
        parent,
        "Income summary",
        f"Period: {rng.start} → {rng.end}\n"
        f"Memberships sold: {count}\n"
        f"Total income: {total_income}"
    )
