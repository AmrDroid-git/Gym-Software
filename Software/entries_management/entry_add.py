# entries_management/entry_add.py
from PyQt6.QtCore import Qt, QSortFilterProxyModel
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QLabel, QTableView,
    QDialogButtonBox, QMessageBox
)
from PyQt6.QtSql import QSqlQueryModel, QSqlDatabase, QSqlQuery

# Clients allowed to enter today:
# - Have at least one membership where today is between start_date and end_date (inclusive)
# - We group by client to avoid duplicates if multiple memberships overlap
ACTIVE_CLIENTS_QUERY = """
SELECT c.id, c.full_name
FROM Client c
JOIN memberships m ON m.client_id = c.id
WHERE date('now') BETWEEN date(m.start_date) AND date(m.end_date)
GROUP BY c.id
ORDER BY c.full_name COLLATE NOCASE;
"""


class AddEntryDialog(QDialog):
    def __init__(self, db: QSqlDatabase, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Entry")
        self.resize(560, 440)
        self._db = db

        v = QVBoxLayout(self)

        # Search bar
        top = QHBoxLayout()
        top.addWidget(QLabel("Search:"))
        self.search = QLineEdit()
        self.search.setClearButtonEnabled(True)
        top.addWidget(self.search, 1)
        v.addLayout(top)

        # Base model with allowed clients
        self.base = QSqlQueryModel(self)
        self.base.setQuery(ACTIVE_CLIENTS_QUERY, self._db)
        self.base.setHeaderData(0, Qt.Orientation.Horizontal, "ID")
        self.base.setHeaderData(1, Qt.Orientation.Horizontal, "Full Name")

        # Filter by name (case-insensitive)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.base)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy.setFilterKeyColumn(1)

        # Table
        self.view = QTableView(self)
        self.view.setModel(self.proxy)
        self.view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.view.verticalHeader().setVisible(False)
        self.view.setAlternatingRowColors(True)
        v.addWidget(self.view, 1)

        # Buttons
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        v.addWidget(btns)

        # Wire search
        self.search.textChanged.connect(self.proxy.setFilterFixedString)

    def _current_client_id(self) -> int | None:
        idx = self.view.currentIndex()
        if not idx.isValid():
            return None
        src = self.proxy.mapToSource(idx)
        return self.base.data(self.base.index(src.row(), 0))  # id column

    def _on_accept(self):
        client_id = self._current_client_id()
        if client_id is None:
            QMessageBox.warning(self, "Select client", "Please select a client from the list.")
            return

        # Insert entry for *today* (DATE type). Use date('now') from SQLite.
        q = QSqlQuery(self._db)
        q.prepare("INSERT INTO entries (date, person_id) VALUES (datetime('now','localtime'), ?);")
        q.addBindValue(int(client_id))
        if not q.exec():
            QMessageBox.critical(self, "Database error", q.lastError().text())
            return

        self.accept()
