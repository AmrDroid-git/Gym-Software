from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTableView, QPushButton, QHBoxLayout, QMessageBox
)
from PyQt6.QtSql import QSqlTableModel
from PyQt6.QtWidgets import QHeaderView
from .income_summary import show_income_for_period


class MembershipsViewDialog(QDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.setWindowTitle("All Memberships")
        self.resize(800, 400)
        self._db = db

        # Normal window with minimize, maximize, and default close button
        self.setWindowFlags(Qt.WindowType.Window |
                            Qt.WindowType.WindowMinimizeButtonHint |
                            Qt.WindowType.WindowMaximizeButtonHint |
                            Qt.WindowType.WindowCloseButtonHint)

        self.setModal(False)  # allows minimizing

        layout = QVBoxLayout(self)

        # Buttons row (left top)
        btn_row = QHBoxLayout()
        delete_btn = QPushButton("Delete Membership")
        delete_btn.clicked.connect(self._delete_selected)
        btn_row.addWidget(delete_btn)
        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        income_pdf_btn = QPushButton("Income Summary")
        income_pdf_btn.clicked.connect(lambda: show_income_for_period(self._db, self))
        btn_row.addWidget(income_pdf_btn)

        # Table
        self.table = QTableView(self)
        layout.addWidget(self.table)

        # Model
        self.model = QSqlTableModel(self, db)
        self.model.setTable("memberships")
        self.model.setEditStrategy(QSqlTableModel.EditStrategy.OnManualSubmit)
        self.model.select()

        headers = ["ID", "Client ID", "Plan ID", "Start Date", "End Date", "Price Paid"]
        for i, h in enumerate(headers):
            self.model.setHeaderData(i, Qt.Orientation.Horizontal, h)

        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

    def _delete_selected(self):
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            QMessageBox.warning(self, "No selection", "Please select a membership to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Delete {len(selection)} membership(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        for index in selection:
            self.model.removeRow(index.row())

        if not self.model.submitAll():
            QMessageBox.critical(self, "Error", "Failed to delete membership(s).")
            self.model.revertAll()
        else:
            self.model.select()
