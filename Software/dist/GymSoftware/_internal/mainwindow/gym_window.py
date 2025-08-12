from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTableView,
    QMessageBox, QPushButton, QHeaderView, QDialog, QAbstractItemView,
    QComboBox, QLineEdit, QLabel
)
from PyQt6.QtSql import QSqlDatabase, QSqlTableModel

from clientsManagement.client_add import create_add_client_button
from clientsManagement.client_view import ClientInfoDialog
from membershipsInfo.memberships_view import MembershipsViewDialog
from membershipsPlans.membership_plans_view import MembershipPlansViewDialog

from entries_management.entries_view import EntriesViewDialog

TABLE_NAME = "Client"

# Map visible names -> actual DB column names
COLUMN_MAP = {
    "ID": "id",
    "Full Name": "full_name",
    "ID Card": "id_card",
    "Phone Number": "phone_number",
    "Role": "role",
    "Picture": "picture",
    "Created At": "created_at",
}

def _connect_sqlite(db_path: str) -> QSqlDatabase:
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    db = QSqlDatabase.addDatabase("QSQLITE")
    db.setDatabaseName(db_path)
    if not db.open():
        raise RuntimeError("Cannot open SQLite database.")
    db.exec("PRAGMA foreign_keys = ON;")
    return db

def _escape_like(s: str) -> str:
    """Escape %, _, and single quotes for a safe LIKE pattern."""
    return s.replace("'", "''").replace("%", r"\%").replace("_", r"\_")

class GymMainWindow(QMainWindow):
    def __init__(self, db_path: str):
        super().__init__()
        self.setWindowTitle("Gym — Clients")
        try:
            self.db = _connect_sqlite(db_path)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))
            raise

        root = QWidget(self)
        main = QVBoxLayout(root)
        self.setCentralWidget(root)

        # ---- Top actions bar ----
        top = QHBoxLayout()
        add_btn = create_add_client_button(parent=self, db=self.db, on_saved=self._refresh)

        memberships_btn = QPushButton("Memberships")
        memberships_btn.clicked.connect(self._open_memberships_view)

        plans_btn = QPushButton("Membership Plans")
        plans_btn.clicked.connect(self._open_membership_plans_view)
        
        entries_btn = QPushButton("Entries")
        entries_btn.clicked.connect(self._open_entries_view)

        top.addWidget(add_btn)
        top.addWidget(memberships_btn)
        top.addWidget(plans_btn)
        top.addWidget(entries_btn)
        top.addStretch(1)
        main.addLayout(top)

        # ---- Search bar ----
        search_bar = QHBoxLayout()
        self.field_combo = QComboBox()
        self.field_combo.addItems(["ID", "Full Name", "ID Card", "Phone Number", "Role", "Created At"])
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Type to search…")
        self.search_edit.setClearButtonEnabled(True)

        search_bar.addWidget(QLabel("Search in:"))
        search_bar.addWidget(self.field_combo, 0)
        search_bar.addWidget(self.search_edit, 1)
        main.addLayout(search_bar)

        # ---- Table view ----
        self.view = QTableView(self)
        main.addWidget(self.view, 1)

        self.model = QSqlTableModel(self, self.db)
        self.model.setTable(TABLE_NAME)
        self.model.setEditStrategy(QSqlTableModel.EditStrategy.OnManualSubmit)

        headers = ["ID", "Full Name", "ID Card", "Phone Number", "Role", "Picture", "Created At"]
        for i, h in enumerate(headers):
            self.model.setHeaderData(i, Qt.Orientation.Horizontal, h)

        self.view.setModel(self.model)
        self.view.setSortingEnabled(True)
        self.view.setAlternatingRowColors(True)
        self.view.verticalHeader().setVisible(False)
        self.view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.view.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

        # 🔹 Restore double-click to open client details
        self.view.doubleClicked.connect(self._open_client_details)

        # ---- Flexible / user-resizable columns ----
        header = self.view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)

        # Auto-fit a few columns initially
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Full Name
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # ID Card
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Phone Number

        self.view.setColumnWidth(1, max(self.view.columnWidth(1), 220))
        self.view.setColumnWidth(3, max(self.view.columnWidth(3), 150))

        self.view.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        header.setSectionsClickable(True)
        header.sectionDoubleClicked.connect(self.view.resizeColumnToContents)

        # ---- Click-to-sort (uses SQL ORDER BY) ----
        header.setSortIndicatorShown(True)
        header.sortIndicatorChanged.connect(self._on_sort_changed)

        # ---- Live search wiring ----
        self.search_edit.textChanged.connect(self._apply_filter)
        self.field_combo.currentIndexChanged.connect(self._apply_filter)

        # Initial load
        self.model.select()
        self.view.resizeColumnsToContents()

    # ---------- Behaviors ----------
    def _apply_filter(self):
        field_label = self.field_combo.currentText()
        column = COLUMN_MAP.get(field_label)
        if not column:
            self.model.setFilter("")
            self.model.select()
            return

        txt = self.search_edit.text().strip()
        if not txt:
            self.model.setFilter("")
            self.model.select()
            return

        esc = _escape_like(txt)

        if column == "id":
            if esc.isdigit():
                cond = f"CAST({column} AS TEXT) LIKE '{esc}%' ESCAPE '\\'"
            else:
                cond = "1=0"
        elif column == "created_at":
            cond = f"{column} LIKE '%{esc}%' ESCAPE '\\'"
        else:
            cond = f"{column} LIKE '%{esc}%' ESCAPE '\\'"

        self.model.setFilter(cond)
        self.model.select()

    def _on_sort_changed(self, section: int, order: Qt.SortOrder):
        self.model.setSort(section, order)
        self.model.select()

    def _refresh(self):
        self.model.select()
        self.view.resizeColumnsToContents()

    def _open_client_details(self, index):
        if not index.isValid():
            return
        row = index.row()
        record = self.model.record(row)
        client_id = record.value(0)
        dlg = ClientInfoDialog(self.db, client_id, parent=self)
        dlg.refreshed.connect(self._refresh)
        dlg.exec()

    def _open_memberships_view(self):
        dlg = MembershipsViewDialog(self.db, parent=self)
        dlg.exec()

    def _open_membership_plans_view(self):
        dlg = MembershipPlansViewDialog(self.db, parent=self)
        dlg.exec()

    
    def _open_entries_view(self):
        dlg = EntriesViewDialog(self.db, parent=self)
        dlg.exec()
