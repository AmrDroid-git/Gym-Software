from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableView, QPushButton,
    QHeaderView, QMessageBox, QFormLayout, QLineEdit, QComboBox, QDialogButtonBox
)
from PyQt6.QtSql import QSqlTableModel, QSqlQuery


class _PlanFormDialog(QDialog):
    """Small form dialog used for Add/Edit."""
    def __init__(self, db, title: str, initial=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._db = db
        self._initial = initial or {}
        self._build_ui()

    def _build_ui(self):
        form = QFormLayout(self)

        self.name_edit = QLineEdit(self._initial.get("name", ""))
        self.months_combo = QComboBox()
        self.months_combo.addItems(["1", "3", "6", "12"])
        if "months" in self._initial:
            idx = self.months_combo.findText(str(self._initial["months"]))
            if idx >= 0:
                self.months_combo.setCurrentIndex(idx)

        self.price_edit = QLineEdit(str(self._initial.get("price_decimal", "")))
        self.price_edit.setPlaceholderText("Price (integer, e.g., cents)")

        form.addRow("Name:", self.name_edit)
        form.addRow("Months:", self.months_combo)
        form.addRow("Price:", self.price_edit)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self._on_ok)
        btns.rejected.connect(self.reject)
        form.addRow(btns)

    def _on_ok(self):
        # Validate
        name = self.name_edit.text().strip()
        months_txt = self.months_combo.currentText()
        price_txt = self.price_edit.text().strip()

        if not name or not months_txt or not price_txt:
            QMessageBox.warning(self, "Missing", "All fields are required.")
            return
        try:
            months = int(months_txt)
            price = int(price_txt)
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Months and Price must be integers.")
            return
        if months not in (1, 3, 6, 12):
            QMessageBox.warning(self, "Invalid", "Months must be one of 1, 3, 6, 12.")
            return

        self._result = {"name": name, "months": months, "price_decimal": price}
        self.accept()

    def result_data(self):
        return getattr(self, "_result", None)


class MembershipPlansViewDialog(QDialog):
    """View of the membership_plans table with add/edit/remove controls."""
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Membership Plans")
        self.resize(760, 420)
        self._db = db

        # ✅ Enable minimize, maximize, and close buttons
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )

        root = QVBoxLayout(self)

        # Top bar buttons
        top = QHBoxLayout()
        self.add_btn = QPushButton("Add membership plan")
        self.edit_btn = QPushButton("Edit membership plan")
        self.remove_btn = QPushButton("Remove membership plan")

        self.add_btn.clicked.connect(self._add_plan)
        self.edit_btn.clicked.connect(self._edit_selected_plan)
        self.remove_btn.clicked.connect(self._remove_selected_plan)

        top.addWidget(self.add_btn)
        top.addWidget(self.edit_btn)
        top.addWidget(self.remove_btn)
        top.addStretch(1)
        root.addLayout(top)

        # Table
        self.table = QTableView(self)
        root.addWidget(self.table)

        model = QSqlTableModel(self, db)
        model.setTable("membership_plans")
        model.setEditStrategy(QSqlTableModel.EditStrategy.OnManualSubmit)
        model.select()

        headers = ["ID", "Name", "Months", "Price (decimal)"]
        for i, h in enumerate(headers):
            model.setHeaderData(i, Qt.Orientation.Horizontal, h)

        self.table.setModel(model)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

        self.model = model  # keep reference

    # ---------- Helpers ----------
    def _selected_row_info(self):
        """Return (row_index, id, name, months, price_decimal) of the selected row, or (None, ...)."""
        idxs = self.table.selectionModel().selectedRows()
        if not idxs:
            return (None, None, None, None, None)
        row = idxs[0].row()
        rec = self.model.record(row)
        return (
            row,
            rec.value("id"),
            rec.value("name"),
            rec.value("months"),
            rec.value("price_decimal"),
        )

    def _refresh(self):
        self.model.select()

    # ---------- Button slots ----------
    def _add_plan(self):
        dlg = _PlanFormDialog(self._db, "Add membership plan", parent=self)
        if dlg.exec():
            data = dlg.result_data()
            if not data:
                return
            q = QSqlQuery(self._db)
            q.prepare("""
                INSERT INTO membership_plans (name, months, price_decimal)
                VALUES (?, ?, ?)
            """)
            q.addBindValue(data["name"])
            q.addBindValue(data["months"])
            q.addBindValue(data["price_decimal"])
            if not q.exec():
                QMessageBox.critical(self, "DB Error", q.lastError().text())
                return
            self._refresh()

    def _edit_selected_plan(self):
        row, plan_id, name, months, price = self._selected_row_info()
        if plan_id is None:
            QMessageBox.information(self, "Select a row", "Please select a plan to edit.")
            return
        dlg = _PlanFormDialog(
            self._db,
            "Edit membership plan",
            initial={"name": name, "months": months, "price_decimal": price},
            parent=self
        )
        if dlg.exec():
            data = dlg.result_data()
            if not data:
                return
            q = QSqlQuery(self._db)
            q.prepare("""
                UPDATE membership_plans
                SET name = ?, months = ?, price_decimal = ?
                WHERE id = ?
            """)
            q.addBindValue(data["name"])
            q.addBindValue(data["months"])
            q.addBindValue(data["price_decimal"])
            q.addBindValue(plan_id)
            if not q.exec():
                QMessageBox.critical(self, "DB Error", q.lastError().text())
                return
            self._refresh()
            # Keep the edited row selected if possible
            if 0 <= row < self.model.rowCount():
                self.table.selectRow(row)

    def _remove_selected_plan(self):
        _, plan_id, name, months, price = self._selected_row_info()
        if plan_id is None:
            QMessageBox.information(self, "Select a row", "Please select a plan to remove.")
            return
        confirm = QMessageBox.question(
            self,
            "Confirm deletion",
            f"Delete membership plan:\n\nID: {plan_id}\nName: {name}\nMonths: {months}\nPrice: {price}\n\nAre you sure?"
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        q = QSqlQuery(self._db)
        q.prepare("DELETE FROM membership_plans WHERE id = ?")
        q.addBindValue(plan_id)
        if not q.exec():
            QMessageBox.critical(self, "DB Error", q.lastError().text())
            return
        self._refresh()
