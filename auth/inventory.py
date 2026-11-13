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
                    warehouse_received REAL NOT NULL DEFAULT 0 CHECK(warehouse_received >= 0),
                    PRIMARY KEY (inventory_date, product_id),
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(inventory_daily)")}
            if "total" not in columns:
                connection.execute("ALTER TABLE inventory_daily ADD COLUMN total REAL NOT NULL DEFAULT 0")
            if "warehouse_received" not in columns:
                connection.execute("ALTER TABLE inventory_daily ADD COLUMN warehouse_received REAL NOT NULL DEFAULT 0")

    def rows_for_date(self, day):
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute("""
                SELECT p.id AS product_id, p.name, COALESCE(i.stock, 0) AS stock,
                       COALESCE(i.added, 0) AS added,
                       COALESCE(i.stock, 0) + COALESCE(i.added, 0) + COALESCE(i.warehouse_received, 0) AS total,
                       COALESCE(i.warehouse_received, 0) AS warehouse_received, i.closing AS closing
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
                INSERT INTO inventory_daily(inventory_date, product_id, stock, added, closing, total, warehouse_received)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(inventory_date, product_id) DO UPDATE SET
                    stock=excluded.stock, added=excluded.added,
                    closing=excluded.closing, total=excluded.total, warehouse_received=excluded.warehouse_received
            """, [(day, row["product_id"], row["stock"], row["added"], row["closing"], row["total"], row.get("warehouse_received",0))
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
        self.setWindowTitle("Inventario diario | App 1.0")
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

        hint = QtWidgets.QLabel("De Almacen muestra el acumulado enviado desde Almacen; ambos valores se mantienen sincronizados.")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.table = QtWidgets.QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Producto", "Stock tienda", "De Almacen", "Total en tienda", "Cierre"])
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
            name_item.setData(QtCore.Qt.ItemDataRole.UserRole + 1, row.get("added", 0))
            name_item.setData(QtCore.Qt.ItemDataRole.UserRole + 2, row.get("warehouse_received", 0))
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row_index, 0, name_item)
            for column, value in ((1, row["stock"]), (2, row.get("warehouse_received", 0)),
                                  (3, row["total"]), (4, row.get("closing", 0))):
                item = QtWidgets.QTableWidgetItem(self._format_quantity(value))
                if column == 3:
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                    item.setBackground(QtCore.Qt.GlobalColor.lightGray)
                elif not editable:
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
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
            received = float(self.table.item(row, 2).text().replace(",", "."))
            added = float(self.table.item(row, 0).data(QtCore.Qt.ItemDataRole.UserRole + 1) or 0)
        except (ValueError, AttributeError):
            stock = added = received = 0
        self._loading = True
        self.table.item(row, 3).setText(self._format_quantity(stock + added + received))
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
                received = float(self.table.item(row_index, 2).text().strip().replace(",", "."))
                added = float(self.table.item(row_index, 0).data(QtCore.Qt.ItemDataRole.UserRole + 1) or 0)
                previous_received = float(self.table.item(row_index, 0).data(QtCore.Qt.ItemDataRole.UserRole + 2) or 0)
                closing_text = self.table.item(row_index, 4).text().strip().replace(",", ".")
                closing = float(closing_text) if closing_text else 0
                if stock < 0 or added < 0 or received < 0 or closing < 0:
                    raise ValueError
                rows.append({
                    "product_id": self.table.item(row_index, 0).data(QtCore.Qt.ItemDataRole.UserRole),
                    "stock": stock,
                    "added": added,
                    "total": stock + added + received,
                    "warehouse_received": received,
                    "previous_warehouse_received": previous_received,
                    "closing": closing,
                })
        except (ValueError, AttributeError):
            QtWidgets.QMessageBox.warning(
                self, "Cantidad inválida", "Revisa las cantidades de Stock, Agregado y Cierre."
            )
            return
        try:
            transfers = [{"product_id": row["product_id"], "quantity": row["warehouse_received"] - row["previous_warehouse_received"]}
                         for row in rows if row["warehouse_received"] != row["previous_warehouse_received"]]
            if transfers:
                self.store.transfer_to_store(selected_day, transfers)
            self.store.save_day(selected_day, rows)
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "No se pudo guardar", str(error))
            return
        self.inventory_saved.emit()
        QtWidgets.QMessageBox.information(
            self, "Inventario guardado", "El inventario del día se guardó correctamente."
        )
        self._load_day()


class WarehouseDialog(QtWidgets.QDialog):
    """Stock de almacen con saldo acumulable y traspaso a tienda."""

    def __init__(self, parent=None, inventory_store=None, product_store=None):
        super().__init__(parent)
        self.setWindowTitle("Almacen | App 1.0")
        self.setMinimumSize(850, 500)
        self.resize(1000, 580)
        self.setStyleSheet(theme_stylesheet())
        self.store = inventory_store
        self.products = product_store or ProductStore()
        self._loading = False
        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("Almacen - stock independiente de tienda")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {theme_palette()['primary']};")
        layout.addWidget(title)
        bar = QtWidgets.QHBoxLayout()
        bar.addWidget(QtWidgets.QLabel("Fecha del almacen"))
        self.day = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.day.setCalendarPopup(True); self.day.setDisplayFormat("dd/MM/yyyy"); self.day.setMaximumDate(QtCore.QDate.currentDate())
        bar.addWidget(self.day); bar.addStretch(); layout.addLayout(bar)
        hint = QtWidgets.QLabel("Agregado a tienda coincide con De Almacen en Inventario. Ingreso almacen registra reposiciones; el saldo restante pasa al dia siguiente.")
        hint.setWordWrap(True); layout.addWidget(hint)
        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Producto", "Stock", "Ingreso almacen", "Agregado a tienda", "Enviar a tienda", "Saldo almacen"])
        self.table.setAlternatingRowColors(True); self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        for column in range(1,6): self.table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemChanged.connect(self._recalculate)
        layout.addWidget(self.table)
        actions = QtWidgets.QHBoxLayout(); self.summary = QtWidgets.QLabel(); actions.addWidget(self.summary); actions.addStretch()
        self.save_button = QtWidgets.QPushButton("Guardar y enviar a tienda"); self.save_button.setObjectName("accentButton"); self.save_button.clicked.connect(self._save); actions.addWidget(self.save_button)
        close = QtWidgets.QPushButton("Cerrar"); close.setObjectName("secondaryButton"); close.clicked.connect(self.accept); actions.addWidget(close); layout.addLayout(actions)
        self.day.dateChanged.connect(self._load_day); self._load_day()

    def _load_day(self, *_args):
        day = self.day.date().toString("yyyy-MM-dd"); rows = self.store.rows_for_date(day); self._loading = True; self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            name = QtWidgets.QTableWidgetItem(row["name"]); name.setData(QtCore.Qt.ItemDataRole.UserRole,row["product_id"]); name.setData(QtCore.Qt.ItemDataRole.UserRole+1,row.get("transferred_to_store",0)); name.setFlags(name.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable); self.table.setItem(index,0,name)
            for column, value in ((1,row["stock"]),(2,row["added"]),(3,row.get("transferred_to_store",0)),(4,0),(5,row["total"])):
                item=QtWidgets.QTableWidgetItem(self._fmt(value));
                if column in (3,5): item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(index,column,item)
        self._loading=False; self.summary.setText(f"{len(rows)} productos ? {sum(float(r['total'] or 0) for r in rows):g} unidades disponibles")

    @staticmethod
    def _fmt(value):
        number=float(value or 0); return str(int(number)) if number.is_integer() else f"{number:g}"

    def _recalculate(self,item):
        if self._loading or item.column() not in (1,2,4): return
        try:
            value=float(item.text().replace(",","."));
            if value<0: raise ValueError
            stock=float(self.table.item(item.row(),1).text().replace(",",".")); added=float(self.table.item(item.row(),2).text().replace(",",".")); transfer=float(self.table.item(item.row(),4).text().replace(",","."))
            prior=float(self.table.item(item.row(),0).data(QtCore.Qt.ItemDataRole.UserRole+1) or 0)
            if transfer>stock+added-prior: raise ValueError
        except ValueError:
            QtWidgets.QMessageBox.warning(self,"Cantidad inválida","El traspaso no puede superar el stock disponible."); self._loading=True; item.setText("0"); self._loading=False; transfer=0
            stock=float(self.table.item(item.row(),1).text() or 0); added=float(self.table.item(item.row(),2).text() or 0)
        self._loading=True; self.table.item(item.row(),5).setText(self._fmt(stock+added-prior-transfer)); self._loading=False

    def _save(self):
        day=self.day.date().toString("yyyy-MM-dd"); rows=[]
        try:
            for index in range(self.table.rowCount()):
                stock=float(self.table.item(index,1).text().replace(",",".")); added=float(self.table.item(index,2).text().replace(",",".")); transfer=float(self.table.item(index,4).text().replace(",",".")); total=float(self.table.item(index,5).text().replace(",","."))
                prior_transfer=float(self.table.item(index,0).data(QtCore.Qt.ItemDataRole.UserRole+1) or 0)
                if min(stock,added,transfer,total)<0 or transfer>stock+added-prior_transfer: raise ValueError
                rows.append({"product_id":self.table.item(index,0).data(QtCore.Qt.ItemDataRole.UserRole),"stock":stock,"added":added,"transferred_to_store":prior_transfer,"transfer_now":transfer,"total":stock+added-prior_transfer})
        except (ValueError,AttributeError):
            QtWidgets.QMessageBox.warning(self,"Cantidad inválida","Revisa stock, agregado y traspaso a tienda."); return
        try:
            self.store.save_day(day,[{key:value for key,value in row.items() if key != "transfer_now"} for row in rows])
            transfers=[{"product_id":row["product_id"],"quantity":row["transfer_now"]} for row in rows if row["transfer_now"]>0]
            if transfers: self.store.transfer_to_store(day,transfers)
        except Exception as error:
            QtWidgets.QMessageBox.critical(self,"No se pudo guardar",str(error)); return
        QtWidgets.QMessageBox.information(self,"Almacen actualizado","El stock se guardó; los traspasos se descontaron de almacen y se sumaron a tienda.")
        self._load_day()
