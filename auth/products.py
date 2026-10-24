"""Administracion local de productos."""

import sqlite3
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from .storage import database_path
from .theme import (
    DIALOG_HEIGHT, DIALOG_MIN_HEIGHT, DIALOG_MIN_WIDTH, DIALOG_WIDTH,
    theme_palette, theme_stylesheet,
)


DB_PATH = database_path()


class ProductStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    entry_date TEXT NOT NULL,
                    cost_price REAL NOT NULL CHECK(cost_price >= 0),
                    sale_price REAL NOT NULL CHECK(sale_price >= 0),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def list_all(self):
        with sqlite3.connect(self.db_path) as connection:
            connection.row_factory = sqlite3.Row
            return [dict(row) for row in connection.execute(
                "SELECT * FROM products ORDER BY name COLLATE NOCASE, id"
            )]

    def save(self, product, product_id=None):
        values = (product["name"], product["description"], product["entry_date"],
                  product["cost_price"], product["sale_price"])
        with sqlite3.connect(self.db_path) as connection:
            if product_id is None:
                connection.execute(
                    "INSERT INTO products(name, description, entry_date, cost_price, sale_price) "
                    "VALUES (?, ?, ?, ?, ?)", values
                )
            else:
                connection.execute(
                    "UPDATE products SET name=?, description=?, entry_date=?, cost_price=?, "
                    "sale_price=? WHERE id=?", values + (product_id,)
                )

    def delete(self, product_id):
        with sqlite3.connect(self.db_path) as connection:
            connection.execute("DELETE FROM products WHERE id=?", (product_id,))


class ProductForm(QtWidgets.QDialog):
    def __init__(self, parent=None, product=None):
        super().__init__(parent)
        self.setWindowTitle("Editar producto" if product else "Agregar producto")
        self.setMinimumWidth(430)
        self.setStyleSheet(theme_stylesheet())
        layout = QtWidgets.QFormLayout(self)
        self.name = QtWidgets.QLineEdit()
        self.name.setMaxLength(120)
        self.description = QtWidgets.QPlainTextEdit()
        self.description.setMaximumHeight(100)
        self.entry_date = QtWidgets.QDateEdit()
        self.entry_date.setCalendarPopup(True)
        self.entry_date.setDisplayFormat("dd/MM/yyyy")
        self.entry_date.setDate(QtCore.QDate.currentDate())
        self.entry_date.setMaximumDate(QtCore.QDate.currentDate())
        self.cost_price = self._price_input()
        self.sale_price = self._price_input()
        layout.addRow("Nombre del producto", self.name)
        layout.addRow("Descripción", self.description)
        layout.addRow("Fecha de ingreso", self.entry_date)
        layout.addRow("Precio de costo (S/)", self.cost_price)
        layout.addRow("Precio de venta (S/)", self.sale_price)
        actions = QtWidgets.QHBoxLayout()
        cancel = QtWidgets.QPushButton("Cancelar")
        cancel.setObjectName("secondaryButton")
        cancel.clicked.connect(self.reject)
        save = QtWidgets.QPushButton("Guardar producto")
        save.setObjectName("accentButton")
        save.clicked.connect(self._validate)
        actions.addWidget(cancel)
        actions.addWidget(save)
        layout.addRow(actions)
        if product:
            self.name.setText(product["name"])
            self.description.setPlainText(product["description"])
            self.entry_date.setDate(QtCore.QDate.fromString(product["entry_date"], "yyyy-MM-dd"))
            self.cost_price.setValue(product["cost_price"])
            self.sale_price.setValue(product["sale_price"])

    @staticmethod
    def _price_input():
        spin = QtWidgets.QDoubleSpinBox()
        spin.setRange(0, 999999999)
        spin.setDecimals(2)
        spin.setSingleStep(1)
        spin.setPrefix("S/ ")
        return spin

    def _validate(self):
        if not self.name.text().strip():
            QtWidgets.QMessageBox.warning(self, "Falta el nombre", "Escribe el nombre del producto.")
            return
        self.accept()

    def product_data(self):
        return {
            "name": self.name.text().strip(),
            "description": self.description.toPlainText().strip(),
            "entry_date": self.entry_date.date().toString("yyyy-MM-dd"),
            "cost_price": self.cost_price.value(),
            "sale_price": self.sale_price.value(),
        }


class ProductsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, store=None, on_delete=None):
        super().__init__(parent)
        self.setWindowTitle("Productos | Cancha")
        self.setMinimumSize(DIALOG_MIN_WIDTH, DIALOG_MIN_HEIGHT)
        self.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
        self.setStyleSheet(theme_stylesheet())
        self.store = store or ProductStore()
        self.on_delete = on_delete
        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("Productos")
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {theme_palette()['primary']};")
        layout.addWidget(title)
        actions = QtWidgets.QHBoxLayout()
        add_button = QtWidgets.QPushButton("Agregar producto")
        add_button.setObjectName("accentButton")
        add_button.clicked.connect(self.add_product)
        actions.addWidget(add_button)
        self.edit_button = QtWidgets.QPushButton("Editar")
        self.delete_button = QtWidgets.QPushButton("Eliminar")
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        self.edit_button.clicked.connect(self.edit_product)
        self.delete_button.clicked.connect(self.delete_product)
        actions.addWidget(self.edit_button)
        actions.addWidget(self.delete_button)
        actions.addStretch()
        close = QtWidgets.QPushButton("Cerrar")
        close.setObjectName("secondaryButton")
        close.clicked.connect(self.accept)
        actions.addWidget(close)
        layout.addLayout(actions)
        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Producto", "Descripción", "Fecha de ingreso", "Precio de costo", "Precio de venta", "Margen"
        ])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        for column in (3, 4, 5):
            self.table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._update_actions)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self.edit_product())
        layout.addWidget(self.table)
        self.refresh()

    def refresh(self):
        products = self.store.list_all()
        self.table.setRowCount(len(products))
        for row_index, product in enumerate(products):
            values = (
                product["name"], product["description"],
                QtCore.QDate.fromString(product["entry_date"], "yyyy-MM-dd").toString("dd/MM/yyyy"),
                f'S/ {product["cost_price"]:.2f}', f'S/ {product["sale_price"]:.2f}',
                f'S/ {product["sale_price"] - product["cost_price"]:.2f}',
            )
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if column == 0:
                    item.setData(QtCore.Qt.ItemDataRole.UserRole, product["id"])
                self.table.setItem(row_index, column, item)
        self.table.clearSelection()
        self._update_actions()

    def _selected_id(self):
        row = self.table.currentRow()
        if row < 0 or self.table.item(row, 0) is None:
            return None
        return self.table.item(row, 0).data(QtCore.Qt.ItemDataRole.UserRole)

    def _update_actions(self):
        selected = self._selected_id() is not None
        self.edit_button.setEnabled(selected)
        self.delete_button.setEnabled(selected)

    def add_product(self):
        form = ProductForm(self)
        if form.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            try:
                self.store.save(form.product_data())
                self.refresh()
            except Exception as error:
                QtWidgets.QMessageBox.critical(self, "No se pudo guardar", str(error))

    def edit_product(self):
        product_id = self._selected_id()
        if product_id is None:
            return
        product = next((row for row in self.store.list_all() if row["id"] == product_id), None)
        if product is None:
            self.refresh()
            return
        form = ProductForm(self, product)
        if form.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            try:
                self.store.save(form.product_data(), product_id)
                self.refresh()
            except Exception as error:
                QtWidgets.QMessageBox.critical(self, "No se pudo guardar", str(error))

    def delete_product(self):
        product_id = self._selected_id()
        if product_id is None:
            return
        answer = QtWidgets.QMessageBox.question(
            self, "Eliminar producto", "¿Seguro que deseas eliminar este producto?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No,
        )
        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                if self.on_delete:
                    self.on_delete(product_id)
                self.store.delete(product_id)
                self.refresh()
            except Exception as error:
                QtWidgets.QMessageBox.critical(self, "No se pudo eliminar", str(error))
