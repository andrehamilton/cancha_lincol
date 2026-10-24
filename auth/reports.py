"""Reportes de ventas de productos y alquiler de canchas."""

from PySide6 import QtCore, QtGui, QtWidgets

from .inventory import InventoryStore
from .reservations import ReservationStore
from .theme import (
    DIALOG_HEIGHT, DIALOG_MIN_HEIGHT, DIALOG_MIN_WIDTH, DIALOG_WIDTH,
    theme_palette, theme_stylesheet,
)


class SalesReportChart(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(260)
        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.days = []
        self.product_sales = []
        self.court_sales = []
        self.hover_index = None

    def set_report_data(self, days, product_sales, court_sales):
        self.days = days
        self.product_sales = product_sales
        self.court_sales = court_sales
        self.hover_index = None
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        palette = theme_palette()
        product_color, court_color = palette["primary"], palette["secondary"]
        painter.fillRect(self.rect(), QtGui.QColor(palette["surface"]))
        if not self.days:
            painter.setPen(QtGui.QColor(palette["muted"]))
            painter.drawText(self.rect(), QtCore.Qt.AlignmentFlag.AlignCenter,
                             "Selecciona un rango de fechas para ver las ventas.")
            painter.end()
            return

        left, right = 62, self.width() - 22
        top, bottom = 24, self.height() - 48
        plot_height = max(1, bottom - top)
        max_data = max(self.product_sales + self.court_sales + [0])
        axis_max = max(1000, int((max_data + 499) // 500) * 500)

        painter.setFont(QtGui.QFont("", 8))
        for step, value in enumerate(range(axis_max, -1, -500)):
            y = top + plot_height * (axis_max - value) / axis_max
            painter.setPen(QtGui.QPen(QtGui.QColor(palette["outline"]), 1, QtCore.Qt.PenStyle.DashLine))
            painter.drawLine(left, int(y), right, int(y))
            painter.setPen(QtGui.QColor(palette["muted"]))
            painter.drawText(QtCore.QRectF(2, y - 8, left - 10, 16),
                             QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter,
                             f"S/ {value:,.0f}")

        count = len(self.days)
        step_x = (right - left) / max(1, count - 1)
        self.points = []
        for index, (values, color) in enumerate(((self.product_sales, product_color),
                                                  (self.court_sales, court_color))):
            points = [QtCore.QPointF(left + i * step_x,
                                     bottom - plot_height * value / axis_max)
                      for i, value in enumerate(values)]
            self.points.append(points)
            if len(points) > 1:
                path = QtGui.QPainterPath(points[0])
                for p1, p2 in zip(points, points[1:]):
                    middle = (p1.x() + p2.x()) / 2
                    path.cubicTo(middle, p1.y(), middle, p2.y(), p2.x(), p2.y())
                painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
                painter.setPen(QtGui.QPen(QtGui.QColor(color), 3,
                                          QtCore.Qt.PenStyle.SolidLine,
                                          QtCore.Qt.PenCapStyle.RoundCap,
                                          QtCore.Qt.PenJoinStyle.RoundJoin))
                painter.drawPath(path)
            for i, point in enumerate(points):
                painter.setPen(QtGui.QPen(QtGui.QColor("white"), 2))
                painter.setBrush(QtGui.QColor(color))
                radius = 6 if i == self.hover_index else 4
                painter.drawEllipse(point, radius, radius)

        label_font = QtGui.QFont("", 8)
        painter.setFont(label_font)
        label_count = min(8, count)
        label_indexes = sorted({round(i * (count - 1) / max(1, label_count - 1))
                                 for i in range(label_count)})
        for index in label_indexes:
            x = left + index * step_x
            painter.setPen(QtGui.QColor(palette["muted"]))
            painter.drawText(QtCore.QRectF(x - 32, bottom + 7, 64, 16),
                             QtCore.Qt.AlignmentFlag.AlignHCenter,
                             self.days[index].toString("dd/MM"))

        if self.hover_index is not None:
            index = self.hover_index
            tip = QtCore.QRectF(max(4, min(self.width() - 196,
                                          left + index * step_x - 92)), top + 4, 190, 58)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(palette["surface"]))
            painter.drawRoundedRect(tip, 8, 8)
            painter.setFont(QtGui.QFont("", 8, QtGui.QFont.Weight.Bold))
            painter.setPen(QtGui.QColor(palette["primary"]))
            painter.drawText(QtCore.QRectF(tip.x() + 9, tip.y() + 5, 172, 15),
                             QtCore.Qt.AlignmentFlag.AlignLeft,
                             f"Productos: S/ {self.product_sales[index]:,.2f}")
            painter.setPen(QtGui.QColor(palette["secondary"]))
            painter.drawText(QtCore.QRectF(tip.x() + 9, tip.y() + 23, 172, 15),
                             QtCore.Qt.AlignmentFlag.AlignLeft,
                             f"Canchas: S/ {self.court_sales[index]:,.2f}")
            painter.setPen(QtGui.QColor(palette["text"]))
            painter.drawText(QtCore.QRectF(tip.x() + 9, tip.y() + 40, 172, 14),
                             QtCore.Qt.AlignmentFlag.AlignLeft,
                             self.days[index].toString("dd/MM/yyyy"))
        painter.end()

    def mouseMoveEvent(self, event):
        if not self.days or not getattr(self, "points", None):
            return
        x = event.position().x()
        all_points = self.points[0]
        nearest = min(range(len(all_points)), key=lambda index: abs(all_points[index].x() - x))
        self.hover_index = nearest if abs(all_points[nearest].x() - x) <= 36 else None
        self.update()

    def leaveEvent(self, event):
        self.hover_index = None
        self.update()
        super().leaveEvent(event)


class ReportsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, inventory_store=None, reservation_store=None):
        super().__init__(parent)
        self.setWindowTitle("Reportes de ventas | Cancha")
        self.setMinimumSize(DIALOG_MIN_WIDTH, DIALOG_MIN_HEIGHT)
        self.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
        self.setStyleSheet(theme_stylesheet())
        self.inventory = inventory_store or InventoryStore()
        self.reservations = reservation_store or ReservationStore()

        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("Reportes de ventas")
        palette = theme_palette()
        title.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {palette['primary']};")
        layout.addWidget(title)
        subtitle = QtWidgets.QLabel("Compara las ventas diarias de productos y alquileres de cancha.")
        subtitle.setStyleSheet(f"color: {palette['muted']};")
        layout.addWidget(subtitle)

        filters = QtWidgets.QHBoxLayout()
        filters.addWidget(QtWidgets.QLabel("Desde"))
        self.start_date = QtWidgets.QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("dd/MM/yyyy")
        self.start_date.setDate(QtCore.QDate.currentDate().addDays(-29))
        filters.addWidget(self.start_date)
        filters.addWidget(QtWidgets.QLabel("Hasta"))
        self.end_date = QtWidgets.QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd/MM/yyyy")
        self.end_date.setDate(QtCore.QDate.currentDate())
        filters.addWidget(self.end_date)
        filters.addStretch(1)
        self.refresh_button = QtWidgets.QPushButton("Actualizar reporte")
        self.refresh_button.setObjectName("accentButton")
        self.refresh_button.clicked.connect(self.refresh_report)
        filters.addWidget(self.refresh_button)
        layout.addLayout(filters)

        self.summary = QtWidgets.QLabel()
        self.summary.setStyleSheet(
            f"background:{palette['highlight']}; color:{palette['primary']}; border-radius:9px; padding:10px; font-weight:600;"
        )
        layout.addWidget(self.summary)

        legend = QtWidgets.QHBoxLayout()
        legend.addWidget(self._legend_item("Ventas de productos (inventario)", palette["primary"]))
        legend.addWidget(self._legend_item("Reservas de cancha", palette["secondary"]))
        legend.addStretch(1)
        layout.addLayout(legend)

        self.chart = SalesReportChart()
        layout.addWidget(self.chart, 3)
        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Fecha", "Productos (S/)", "Canchas (S/)", "Total (S/)"])
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 3):
            self.table.horizontalHeader().setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 2)

        footer = QtWidgets.QHBoxLayout()
        footer.addStretch(1)
        close_button = QtWidgets.QPushButton("Cerrar")
        close_button.setObjectName("secondaryButton")
        close_button.clicked.connect(self.accept)
        footer.addWidget(close_button)
        layout.addLayout(footer)
        self.refresh_report()

    @staticmethod
    def _legend_item(text, color):
        item = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(item)
        row.setContentsMargins(0, 0, 8, 0)
        swatch = QtWidgets.QLabel("●")
        swatch.setStyleSheet(f"color:{color}; font-size:16px;")
        row.addWidget(swatch)
        row.addWidget(QtWidgets.QLabel(text))
        return item

    def refresh_report(self):
        start = self.start_date.date()
        end = self.end_date.date()
        if start > end:
            QtWidgets.QMessageBox.warning(self, "Rango inválido", "La fecha inicial debe ser anterior a la fecha final.")
            return
        days_count = start.daysTo(end) + 1
        if days_count > 366:
            QtWidgets.QMessageBox.warning(self, "Rango muy amplio", "El reporte admite rangos de hasta un año.")
            return

        start_text = start.toString("yyyy-MM-dd")
        end_text = end.toString("yyyy-MM-dd")
        product_map = self.inventory.sales_between(start_text, end_text)
        court_map = self.reservations.court_revenue_between(start_text, end_text)
        days = [start.addDays(offset) for offset in range(days_count)]
        keys = [day.toString("yyyy-MM-dd") for day in days]
        product_values = [product_map.get(key, 0) for key in keys]
        court_values = [court_map.get(key, 0) for key in keys]
        self.chart.set_report_data(days, product_values, court_values)

        product_total = sum(product_values)
        court_total = sum(court_values)
        self.summary.setText(
            f"Productos: S/ {product_total:,.2f}     |     "
            f"Canchas: S/ {court_total:,.2f}     |     "
            f"Total del período: S/ {product_total + court_total:,.2f}"
        )
        self.table.setRowCount(days_count)
        for row, day in enumerate(days):
            products = product_values[row]
            courts = court_values[row]
            values = (day.toString("dd/MM/yyyy"), f"{products:,.2f}",
                      f"{courts:,.2f}", f"{products + courts:,.2f}")
            for column, value in enumerate(values):
                item = QtWidgets.QTableWidgetItem(value)
                if column:
                    item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row, column, item)
