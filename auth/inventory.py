"""Inventario diario vinculado al catalogo de productos."""

import sqlite3
from datetime import date
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from .products import ProductStore
from .storage import database_path
from .theme import (
    DIALOG_HEIGHT, DIALOG_MIN_HEIGHT, DIALOG_MIN_WIDTH, DIALOG_WIDTH,
    theme_palette, theme_stylesheet,
)

DB_PATH = database_path()


class InventoryStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS inventory_daily (
                    inventory_date TEXT NOT NULL,
                    product_id INTEGER NOT NULL,
                    stock REAL NOT NULL DEFAULT 0 CHECK(stock >= 0),
                    added REAL NOT NULL DEFAULT 0 CHECK(added >= 0),
                    closing REAL NOT NULL DEFAULT 0 CHECK(closing >= 0),
                    total REAL NOT NULL DEFAULT 0 CHECK(total >= 0),
                    PRIMARY KEY (inventory_date, product_id),
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(inventory_daily)")}
            if "total" not in columns:
                connection.execute("ALTER TABLE inventory_daily ADD COLUMN total REAL NOT NULL DEFAULT 0")

    def rows_for_date(self, day):
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute("""
                SELECT p.id AS product_id, p.name, COALESCE(i.stock, 0) AS stock,
                       COALESCE(i.added, 0) AS added,
                       COALESCE(i.stock, 0) + COALESCE(i.added, 0) AS total,
                       i.closing AS closing
                FROM products p
                LEFT JOIN inventory_daily i
                    ON i.product_id = p.id AND i.inventory_date = ?
                ORDER BY p.name COLLATE NOCASE, p.id
            """, (day,))]

    @staticmethod
    def is_editable(day, today=None):
        """Permite cambios durante los siete dias posteriores al inventario."""
        inventory_date = date.fromisoformat(day)
        current_date = today or date.today()
        age_days = (current_date - inventory_date).days
        return 0 <= age_days <= 7

    def save_day(self, day, rows):
        if not self.is_editable(day):
            raise ValueError("Este inventario ya supero el plazo de 7 dias y no se puede modificar.")
        with sqlite3.connect(self.db_path) as connection:
            connection.executemany("""
                INSERT INTO inventory_daily(inventory_date, product_id, stock, added, closing, total)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(inventory_date, product_id) DO UPDATE SET
                    stock=excluded.stock, added=excluded.added,
                    closing=excluded.closing, total=excluded.total
            """, [(day, row["product_id"], row["stock"], row["added"], row["closing"], row["total"])
                  for row in rows])

    def daily_sales(self, days=7):
        """Ventas estimadas desde diferencias de inventario y precios actuales."""
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("""
                SELECT i.inventory_date,
                       SUM(MAX(0, i.total - i.closing) * p.sale_price) AS sales
                FROM inventory_daily i
                JOIN products p ON p.id = i.product_id
                WHERE i.inventory_date >= date('now', ?)
                    AND i.inventory_date <= date('now')
                    AND (i.total > 0 OR i.added > 0 OR i.closing > 0)
                GROUP BY i.inventory_date
                ORDER BY i.inventory_date
            """, (f"-{max(1, int(days) - 1)} days",)).fetchall()
        return {row["inventory_date"]: row["sales"] or 0 for row in rows}

    def sales_between(self, start_date, end_date):
        """Ventas estimadas por inventario agrupadas para un rango elegido."""
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute("""
                SELECT i.inventory_date,
                       SUM(MAX(0, i.total - i.closing) * p.sale_price) AS sales
                FROM inventory_daily i
                JOIN products p ON p.id = i.product_id
                WHERE i.inventory_date BETWEEN ? AND ?
                    AND (i.total > 0 OR i.added > 0 OR i.closing > 0)
                GROUP BY i.inventory_date
                ORDER BY i.inventory_date
            """, (start_date, end_date)).fetchall()
        return {row["inventory_date"]: row["sales"] or 0 for row in rows}


class InventoryDialog(QtWidgets.QDialog):
    inventory_saved = QtCore.Signal()

    def __init__(self, parent=None, inventory_store=None, product_store=None):
        super().__init__(parent)
        self.setWindowTitle("Inventario diario | Cancha")
        self.setMinimumSize(DIALOG_MIN_WIDTH, DIALOG_MIN_HEIGHT)
        self.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
        self.setStyleSheet(theme_stylesheet())
        self.store = inventory_store or InventoryStore()
        self.products = product_store or ProductStore()
        self._loading = False

        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("Inventario diario")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {theme_palette()['primary']};")
        layout.addWidget(title)

        date_row = QtWidgets.QHBoxLayout()
        date_row.addWidget(QtWidgets.QLabel("Fecha del inventario"))
        self.day = QtWidgets.QDateEdit()
        self.day.setCalendarPopup(True)
        self.day.setDisplayFormat("dd/MM/yyyy")
        self.day.setDate(QtCore.QDate.currentDate())
        self.day.setMaximumDate(QtCore.QDate.currentDate())
        date_row.addWidget(self.day)
        date_row.addStretch()
        layout.addLayout(date_row)

        hint = QtWidgets.QLabel(
            "Ingresa Stock y Agregado; Total se calcula automáticamente. "
            "Al final del día, ingresa el stock contado en Cierre."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Producto", "Stock", "Agregado", "Total", "Cierre"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3, 4):
            self.table.horizontalHeader().setSectionResizeMode(
                column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents
            )
        self.table.itemChanged.connect(self._cell_changed)
        self.day.dateChanged.connect(self._load_day)
        layout.addWidget(self.table)

        actions = QtWidgets.QHBoxLayout()
        save_button = QtWidgets.QPushButton("Guardar inventario")
        save_button.setObjectName("accentButton")
        self.save_button = save_button
        save_button.clicked.connect(self._save)
        actions.addWidget(save_button)
        close_button = QtWidgets.QPushButton("Cerrar")
        close_button.setObjectName("secondaryButton")
        close_button.clicked.connect(self.accept)
        actions.addWidget(close_button)
        layout.addLayout(actions)
        self._load_day()

    def _load_day(self, *_args):
        day = self.day.date().toString("yyyy-MM-dd")
        rows = self.store.rows_for_date(day)
        editable = self.store.is_editable(day)
        self._loading = True
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            name_item = QtWidgets.QTableWidgetItem(row["name"])
            name_item.setData(QtCore.Qt.ItemDataRole.UserRole, row["product_id"])
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row_index, 0, name_item)
            for column, key in ((1, "stock"), (2, "added"), (3, "total"), (4, "closing")):
                item = QtWidgets.QTableWidgetItem(self._format_quantity(row[key]))
                if column == 3:
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                    item.setBackground(QtCore.Qt.GlobalColor.lightGray)
                else:
                    if not editable:
                        item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                    item.setTextAlignment(
                        QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter
                    )
                self.table.setItem(row_index, column, item)
        self._loading = False
        self.save_button.setEnabled(editable)

    @staticmethod
    def _format_quantity(value):
        if value is None:
            return ""
        number = float(value)
        return str(int(number)) if number.is_integer() else f"{number:g}"

    def _cell_changed(self, item):
        if self._loading or item.column() not in (1, 2, 4):
            return
        if not self.store.is_editable(self.day.date().toString("yyyy-MM-dd")):
            self._load_day()
            return
        try:
            value = float(item.text().strip().replace(",", "."))
            if value < 0:
                raise ValueError
            item.setText(self._format_quantity(value))
        except ValueError:
            QtWidgets.QMessageBox.warning(
                self, "Cantidad inválida", "Ingresa una cantidad igual o mayor que cero."
            )
            self._loading = True
            item.setText("0")
            self._loading = False
        if item.column() in (1, 2):
            self._recalculate_row(item.row())

    def _recalculate_row(self, row):
        try:
            stock = float(self.table.item(row, 1).text().replace(",", "."))
            added = float(self.table.item(row, 2).text().replace(",", "."))
        except (ValueError, AttributeError):
            stock = added = 0
        self._loading = True
        self.table.item(row, 3).setText(self._format_quantity(stock + added))
        self._loading = False

    def _save(self):
        selected_day = self.day.date().toString("yyyy-MM-dd")
        if not self.store.is_editable(selected_day):
            QtWidgets.QMessageBox.warning(
                self, "Plazo vencido",
                "Este inventario ya supero el plazo de 7 dias y no se puede modificar.",
            )
            self._load_day()
            return
        rows = []
        try:
            for row_index in range(self.table.rowCount()):
                stock = float(self.table.item(row_index, 1).text().strip().replace(",", "."))
                added = float(self.table.item(row_index, 2).text().strip().replace(",", "."))
                closing_text = self.table.item(row_index, 4).text().strip().replace(",", ".")
                closing = float(closing_text) if closing_text else 0
                if stock < 0 or added < 0 or closing < 0:
                    raise ValueError
                rows.append({
                    "product_id": self.table.item(row_index, 0).data(QtCore.Qt.ItemDataRole.UserRole),
                    "stock": stock,
                    "added": added,
                    "total": stock + added,
                    "closing": closing,
                })
        except (ValueError, AttributeError):
            QtWidgets.QMessageBox.warning(
                self, "Cantidad inválida", "Revisa las cantidades de Stock, Agregado y Cierre."
            )
            return
        try:
            self.store.save_day(selected_day, rows)
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "No se pudo guardar", str(error))
            return
        self.inventory_saved.emit()
        QtWidgets.QMessageBox.information(
            self, "Inventario guardado", "El inventario del día se guardó correctamente."
        )
        self._load_day()
