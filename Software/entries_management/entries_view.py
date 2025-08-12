# entries_management/entries_view.py
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTableView
from PyQt6.QtSql import QSqlQueryModel, QSqlDatabase
from .entry_add import AddEntryDialog


class EntriesViewDialog(QDialog):
    def __init__(self, db: QSqlDatabase, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gym Entries")
        self.resize(780, 500)
        self._db = db

        layout = QVBoxLayout(self)

        # Table
        self.view = QTableView(self)
        self.view.setSortingEnabled(True)
        self.view.setAlternatingRowColors(True)
        self.view.verticalHeader().setVisible(False)
        layout.addWidget(self.view, 1)

        # Buttons row
        row = QHBoxLayout()
        btn_add = QPushButton("Add entry for a client")
        btn_add.clicked.connect(self._add_entry)
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh)
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.reject)
        row.addWidget(btn_add)
        row.addWidget(btn_refresh)
        row.addStretch(1)
        row.addWidget(btn_close)
        layout.addLayout(row)

        # Model
        self.model = QSqlQueryModel(self)
        self.view.setModel(self.model)
        self.refresh()

    def refresh(self):
        # Join with Client for name; keep entries even if client deleted
        sql = """
        SELECT e.id            AS "ID",
               e.date          AS "Date",
               e.person_id     AS "Client ID",
               COALESCE(c.full_name, '(deleted)') AS "Client Name"
        FROM entries e
        LEFT JOIN Client c ON c.id = e.person_id
        ORDER BY e.date DESC, e.id DESC;
        """
        self.model.setQuery(sql, self._db)
        self.view.resizeColumnsToContents()

    def _add_entry(self):
        dlg = AddEntryDialog(self._db, parent=self)
        if dlg.exec():
            self.refresh()
