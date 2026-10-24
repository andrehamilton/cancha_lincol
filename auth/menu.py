"""Menu principal con accesos visuales a las secciones de Cancha."""

from PySide6 import QtCore, QtGui, QtWidgets

from .inventory import InventoryDialog
from .products import ProductsDialog
from .reservations import ReservationDialog
from .reports import ReportsDialog
from .profile import ProfileDialog
from .settings import SettingsDialog
from .theme import theme_palette, theme_stylesheet
from .cloud_store import ProductCloudStore, InventoryCloudStore, ReservationCloudStore


class DailyIncomeChart(QtWidgets.QWidget):
    """Comparativo lineal de ventas de productos y alquiler de canchas."""

    def __init__(self, inventory_store, reservation_store, parent=None):
        super().__init__(parent)
        self.inventory_store = inventory_store
        self.reservation_store = reservation_store
        self.setMinimumSize(360, 300)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.hover_index = None
        self.pinned_index = None
        self.chart_points = []
        self.products = {}
        self.courts = {}
        self.refresh_timer = QtCore.QTimer(self)
        self.refresh_timer.setInterval(15000)
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start()
        self.refresh()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        palette = theme_palette()
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(QtGui.QPen(QtGui.QColor(palette["outline"]), 1))
        painter.setBrush(QtGui.QColor(palette["surface"]))
        painter.drawRoundedRect(rect, 14, 14)
        margin = 42
        chart_left, chart_right = margin, self.width() - 20
        chart_top, chart_bottom = 96, self.height() - 40
        chart_height = max(1, chart_bottom - chart_top)
        self.chart_points = []
        today = QtCore.QDate.currentDate()
        dates = [today.addDays(offset) for offset in range(-6, 1)]
        keys = [day.toString("yyyy-MM-dd") for day in dates]
        product_values = [self.products.get(key, 0) for key in keys]
        court_values = [self.courts.get(key, 0) for key in keys]
        products_total = sum(product_values)
        courts_total = sum(court_values)
        total = products_total + courts_total
        peak = max([0, *product_values, *court_values])
        scale_max = max(100, ((int(peak) + 99) // 100) * 100)


        title_font = QtGui.QFont()
        title_font.setPixelSize(16)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.setPen(QtGui.QColor(palette["text"]))
        painter.drawText(margin, 29, "Ventas diarias")
        painter.setFont(QtGui.QFont("", 9))
        painter.setPen(QtGui.QColor(palette["muted"]))
        painter.drawText(margin, 47, "ÚLTIMOS 7 DÍAS · ESCALA DINÁMICA · INTERVALOS DE S/ 500")

        metric_rect = QtCore.QRectF(max(margin + 145, self.width() - 190), 12, 166, 42)
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.setBrush(QtGui.QColor(palette["highlight"]))
        painter.drawRoundedRect(metric_rect, 10, 10)
        painter.setPen(QtGui.QColor(palette["primary"]))
        painter.setFont(QtGui.QFont("", 12, QtGui.QFont.Weight.Bold))
        painter.drawText(metric_rect, QtCore.Qt.AlignmentFlag.AlignCenter, f"S/ {total:,.2f}")

        # Leyenda visible bajo el encabezado, con el nombre completo de cada serie.
        legend_y = 69
        legend_items = ((44, "Productos (inventario)", palette["primary"], products_total),
                        (self.width() // 2, "Alquiler de canchas", palette["secondary"], courts_total))
        painter.setFont(QtGui.QFont("", 8, QtGui.QFont.Weight.DemiBold))
        for x, label, color, amount in legend_items:
            painter.setPen(QtGui.QPen(QtGui.QColor(color), 3,
                                      QtCore.Qt.PenStyle.SolidLine,
                                      QtCore.Qt.PenCapStyle.RoundCap))
            painter.drawLine(x, legend_y - 4, x + 18, legend_y - 4)
            painter.setPen(QtGui.QColor(palette["text"]))
            painter.drawText(x + 24, legend_y, f"{label}  S/ {amount:,.2f}")

        painter.setFont(QtGui.QFont("", 8))
        tick_step = max(25, ((scale_max // 4 + 24) // 25) * 25)
        for value in range(scale_max, -1, -tick_step):
            y = chart_bottom - chart_height * value / scale_max
            painter.setPen(QtGui.QPen(QtGui.QColor(palette["outline"]), 1, QtCore.Qt.PenStyle.DashLine))
            painter.drawLine(int(chart_left), int(y), int(chart_right), int(y))
            painter.setPen(QtGui.QColor(palette["muted"]))
            painter.drawText(QtCore.QRectF(3, y - 7, margin - 9, 14),
                             QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter,
                             f"{value:,}")

        spacing = (chart_right - chart_left) / 6
        series = (("products", "Productos", palette["primary"]),
                  ("courts", "Canchas", palette["secondary"]))
        for series_index, (key, label, color) in enumerate(series):
            values = product_values if key == "products" else court_values
            points = [QtCore.QPointF(chart_left + spacing * index,
                                     chart_bottom - chart_height * value / scale_max)
                      for index, value in enumerate(values)]
            path = QtGui.QPainterPath(points[0])
            for left, right in zip(points, points[1:]):
                middle = (left.x() + right.x()) / 2
                path.cubicTo(middle, left.y(), middle, right.y(), right.x(), right.y())
            if series_index == 0:
                area = QtGui.QPainterPath(path)
                area.lineTo(points[-1].x(), chart_bottom)
                area.lineTo(points[0].x(), chart_bottom)
                area.closeSubpath()
                gradient = QtGui.QLinearGradient(0, chart_top, 0, chart_bottom)
                fill = QtGui.QColor(color)
                fill.setAlpha(62)
                clear = QtGui.QColor(color)
                clear.setAlpha(0)
                gradient.setColorAt(0, fill)
                gradient.setColorAt(1, clear)
                painter.setPen(QtCore.Qt.PenStyle.NoPen)
                painter.setBrush(gradient)
                painter.drawPath(area)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.setPen(QtGui.QPen(QtGui.QColor(color), 3,
                                      QtCore.Qt.PenStyle.SolidLine,
                                      QtCore.Qt.PenCapStyle.RoundCap,
                                      QtCore.Qt.PenJoinStyle.RoundJoin))
            painter.drawPath(path)
            for index, point in enumerate(points):
                self.chart_points.append((index, series_index, point))
                radius = 7 if index == self.hover_index else 5
                painter.setPen(QtGui.QPen(QtGui.QColor("white"), 2))
                painter.setBrush(QtGui.QColor(color))
                painter.drawEllipse(point, radius, radius)

        painter.setFont(QtGui.QFont("", 9))
        for index, day in enumerate(dates):
            x = chart_left + spacing * index
            painter.setPen(QtGui.QColor(palette["muted"]))
            painter.drawText(QtCore.QRectF(x - spacing / 2, chart_bottom + 7, spacing, 16),
                             QtCore.Qt.AlignmentFlag.AlignHCenter,
                             "Hoy" if day == today else day.toString("ddd").capitalize())

        tip_index = self.hover_index if self.hover_index is not None else self.pinned_index
        if tip_index is not None:
            index = tip_index
            tip = QtCore.QRectF(max(5, min(self.width() - 222, chart_left + spacing * index - 108)),
                                chart_top + 4, 212, 69)
            painter.setPen(QtCore.Qt.PenStyle.NoPen)
            painter.setBrush(QtGui.QColor(palette["surface"]))
            painter.drawRoundedRect(tip, 8, 8)
            painter.setFont(QtGui.QFont("", 8, QtGui.QFont.Weight.DemiBold))
            painter.setPen(QtGui.QColor(palette["muted"]))
            painter.drawText(QtCore.QRectF(tip.x() + 9, tip.y() + 4, 194, 13),
                             QtCore.Qt.AlignmentFlag.AlignLeft, dates[index].toString("dd/MM/yyyy"))
            painter.setFont(QtGui.QFont("", 8, QtGui.QFont.Weight.Bold))
            painter.setPen(QtGui.QColor(palette["primary"]))
            painter.drawText(QtCore.QRectF(tip.x() + 9, tip.y() + 22, 194, 15),
                             QtCore.Qt.AlignmentFlag.AlignLeft, f"Productos  S/ {product_values[index]:,.2f}")
            painter.setPen(QtGui.QColor(palette["secondary"]))
            painter.drawText(QtCore.QRectF(tip.x() + 9, tip.y() + 43, 194, 15),
                             QtCore.Qt.AlignmentFlag.AlignLeft, f"Canchas  S/ {court_values[index]:,.2f}")
        painter.end()

    def refresh(self):
        if self.inventory_store is None and self.reservation_store is None:
            self.products, self.courts = {}, {}
            self.update()
            return
        try:
            self.products = self.inventory_store.daily_sales(7) if self.inventory_store is not None else {}
            self.courts = self.reservation_store.daily_court_revenue(7) if self.reservation_store is not None else {}
        except Exception:
            self.products, self.courts = {}, {}
        self.update()

    def mouseMoveEvent(self, event):
        position = event.position()
        if self.chart_points:
            nearest = min(self.chart_points, key=lambda entry: abs(entry[2].x() - position.x()))
            self.hover_index = nearest[0] if abs(nearest[2].x() - position.x()) <= 35 else None
        else:
            self.hover_index = None
        self.update()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self.chart_points:
            position = event.position()
            nearest = min(self.chart_points, key=lambda entry: abs(entry[2].x() - position.x()))
            self.pinned_index = nearest[0] if abs(nearest[2].x() - position.x()) <= 40 else None
            self.update()
            return
        super().mousePressEvent(event)

    def leaveEvent(self, event):
        self.hover_index = None
        self.update()
        super().leaveEvent(event)


class MenuCard(QtWidgets.QPushButton):
    def __init__(self, title, subtitle, icon, accent=False, parent=None):
        super().__init__(parent)
        self.setObjectName("menuCardAccent" if accent else "menuCard")
        self.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(70)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(16, 8, 20, 8)
        row.setSpacing(18)

        illustration = QtWidgets.QLabel()
        illustration.setFixedSize(44, 44)
        illustration.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.illustration = illustration
        self.icon_name = icon
        self.refresh_icon()
        illustration.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(illustration)

        text_box = QtWidgets.QVBoxLayout()
        text_box.setSpacing(5)
        heading = QtWidgets.QLabel(title)
        heading.setObjectName("menuCardTitle")
        description = QtWidgets.QLabel(subtitle)
        description.setObjectName("menuCardDescription")
        description.setWordWrap(True)
        for label in (heading, description):
            label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        text_box.addStretch()
        text_box.addWidget(heading)
        text_box.addWidget(description)
        text_box.addStretch()
        row.addLayout(text_box, 1)

        arrow = QtWidgets.QLabel("›")
        arrow.setObjectName("menuCardArrow")
        arrow.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(arrow)

    def refresh_icon(self):
        palette = theme_palette()
        main = palette["secondary"] if self.icon_name == "reserve" else palette["primary"]
        pale = palette["highlight"]
        self.illustration.setPixmap(self._icon_pixmap(self.icon_name, main, pale))

    @staticmethod
    def _icon_pixmap(name, main, pale):
        drawings = {
            "reserve": '<path d="M20 48h56M27 48V27h42v21M27 36h42M34 27v-7m28 7v-7"/><path d="M16 57h64M22 57l-5 16m57-16 5 16"/>',
            "agenda": '<rect x="20" y="22" width="56" height="52" rx="7"/><path d="M20 37h56M32 16v13m32-13v13M31 48h8m9 0h8m9 0h8M31 60h8m9 0h8"/>',
            "inventory": '<path d="m48 17 29 16v33L48 82 19 66V33z"/><path d="m19 33 29 17 29-17M48 50v32M34 25l29 17"/>',
            "products": '<path d="M20 28h56v47H20zM20 40h56M31 17v20m34-20v20M29 52h12v12H29zm26 0h12v12H55z"/>',
            "reports": '<path d="M20 76V20m0 56h58M30 63l13-16 12 8 20-25"/><circle cx="30" cy="63" r="3"/><circle cx="43" cy="47" r="3"/><circle cx="55" cy="55" r="3"/><circle cx="75" cy="30" r="3"/>',
            "profile": '<circle cx="48" cy="34" r="15"/><path d="M20 79c2-15 12-24 28-24s26 9 28 24z"/>',
            "settings": '<circle cx="48" cy="48" r="13"/><path d="M48 17v8m0 46v8M17 48h8m46 0h8M26 26l6 6m32 32 6 6m0-44-6 6m-32 32-6 6"/><circle cx="48" cy="48" r="25"/>',
        }
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96">'
               f'<rect x="5" y="5" width="86" height="86" rx="22" fill="{pale}"/>'
               f'<path d="M15 78h65" stroke="{main}" stroke-width="2" opacity=".12"/>'
               f'<g fill="none" stroke="{main}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round">{drawings[name]}</g></svg>')
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(svg.encode("utf-8"), "SVG")
        return pixmap.scaled(44, 44, QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                             QtCore.Qt.TransformationMode.SmoothTransformation)


class MenuWindow(QtWidgets.QMainWindow):
    def __init__(self, user, auth):
        super().__init__()
        self.setWindowTitle("Cancha | Menú principal")
        self.resize(1100, 720)
        self.setMinimumSize(900, 620)
        self.user = user
        self.auth = auth
        self.product_store = None
        self.inventory_store = None
        self.reservation_store = None

        central = QtWidgets.QWidget()
        central.setObjectName("menuBackground")
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setContentsMargins(32, 20, 32, 16)
        layout.setSpacing(8)

        brand = QtWidgets.QLabel("CANCHA  /  ADMINISTRACIÓN")
        brand.setObjectName("menuBrand")
        layout.addWidget(brand)
        self.welcome_title = QtWidgets.QLabel(f"¡Bienvenido, {user['full_name']}!")
        self.welcome_title.setObjectName("menuTitle")
        self.welcome_title.setWordWrap(True)
        layout.addWidget(self.welcome_title)
        subtitle = QtWidgets.QLabel("Elige una opción para continuar")
        subtitle.setObjectName("menuSubtitle")
        layout.addWidget(subtitle)
        self.sync_notice = QtWidgets.QLabel(
            "Sincronización pendiente: ejecuta SUPABASE_SHARED_DATA.sql en tu proyecto Supabase."
        )
        self.sync_notice.setWordWrap(True)
        self.sync_notice.setStyleSheet(
            "background:#fff3d9; color:#714a12; border:1px solid #e9cc8b; "
            "border-radius:8px; padding:8px 12px; font-size:12px;"
        )
        layout.addWidget(self.sync_notice)
        self.sync_notice.hide()
        content = QtWidgets.QHBoxLayout()
        content.setSpacing(18)
        self.options_content = QtWidgets.QWidget()
        self.options_content.setObjectName("menuOptionsContent")
        self.options_content.setAutoFillBackground(True)
        options = QtWidgets.QVBoxLayout(self.options_content)
        options.setContentsMargins(0, 0, 4, 0)
        options.setSpacing(6)
        self.reserve_card = MenuCard("Reservar una cancha", "Registrar una nueva reserva", "reserve", accent=True)
        self.reserve_card.clicked.connect(self.open_reservation_form)
        options.addWidget(self.reserve_card)
        self.reservations_card = MenuCard("Reservas registradas", "Consultar, editar y confirmar reservas", "agenda")
        self.reservations_card.clicked.connect(self.show_reservations)
        options.addWidget(self.reservations_card)
        self.inventory_card = MenuCard("Inventario", "Revisar stock, agregados y cierre diario", "inventory")
        self.inventory_card.clicked.connect(self.show_inventory)
        options.addWidget(self.inventory_card)
        self.products_card = MenuCard("Productos", "Administrar el catálogo de productos", "products")
        self.products_card.clicked.connect(self.show_products)
        options.addWidget(self.products_card)
        self.reports_card = MenuCard("Reportes", "Gráfico detallado de ventas por fechas", "reports")
        self.reports_card.clicked.connect(self.show_reports)
        options.addWidget(self.reports_card)
        self.profile_card = MenuCard("Perfil", "Ver datos de la cuenta", "profile")
        self.profile_card.clicked.connect(self.show_profile)
        options.addWidget(self.profile_card)
        self.settings_card = MenuCard("Configuraciones", "Personalizar colores y tema", "settings")
        self.settings_card.clicked.connect(self.show_settings)
        options.addWidget(self.settings_card)
        options.addStretch(1)
        self.options_scroll = QtWidgets.QScrollArea()
        self.options_scroll.setWidgetResizable(True)
        self.options_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.options_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.options_scroll.setAutoFillBackground(True)
        self.options_scroll.setWidget(self.options_content)
        content.addWidget(self.options_scroll, 5)
        self.activity_chart = DailyIncomeChart(None, None)
        content.addWidget(self.activity_chart, 6)
        layout.addLayout(content, 1)

        footer = QtWidgets.QHBoxLayout()
        footer.addStretch()
        self.logout_button = QtWidgets.QPushButton("Cerrar sesión")
        self.logout_button.setObjectName("secondaryButton")
        self.logout_button.setMinimumHeight(36)
        footer.addWidget(self.logout_button)
        layout.addLayout(footer)
        self._apply_theme()

    def open_reservation_form(self):
        if not self._ensure_shared_stores("reservations"):
            return
        dialog = ReservationDialog(self.user, self, self.reservation_store)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.activity_chart.refresh()
            QtWidgets.QMessageBox.information(self, "Reserva guardada", "La reserva se guardó correctamente.")

    def show_reservations(self):
        if not self._ensure_shared_stores("reservations"):
            return
        ReservationDialog(self.user, self, self.reservation_store, list_mode=True).exec()
        self.activity_chart.refresh()

    def show_inventory(self):
        if not self._ensure_shared_stores("inventory"):
            return
        dialog = InventoryDialog(self, inventory_store=self.inventory_store, product_store=self.product_store)
        dialog.inventory_saved.connect(self.activity_chart.refresh)
        dialog.exec()

    def show_products(self):
        if not self._ensure_shared_stores("products"):
            return
        if self.inventory_store is None:
            if not self._ensure_shared_stores("inventory"):
                return
        ProductsDialog(self, store=self.product_store, on_delete=self.inventory_store.delete_product_days).exec()
        self.activity_chart.refresh()

    def _ensure_shared_stores(self, section):
        try:
            if self.product_store is None:
                self.product_store = ProductCloudStore(self.auth, self.user)
            if section in ("inventory", "reports") and self.inventory_store is None:
                self.inventory_store = InventoryCloudStore(self.auth, self.user, self.product_store)
            if section in ("reservations", "reports") and self.reservation_store is None:
                self.reservation_store = ReservationCloudStore(self.auth, self.user)
            store = {
                "products": self.product_store,
                "inventory": self.inventory_store,
                "reservations": self.reservation_store,
            }.get(section)
            if store is not None:
                store.refresh_session(self.user)
            if section == "products":
                # ProductsDialog loads the catalogue once when it opens.
                pass
            elif section == "reservations":
                # ReservationDialog loads only the selected date when it opens.
                pass
            elif section == "inventory":
                # InventoryDialog fetches products and the selected date only.
                pass
            self.sync_notice.hide()
            return True
        except Exception as error:
            message = str(error)
            if "schema cache" in message.lower() or "does not exist" in message.lower():
                self.sync_notice.show()
                message = (
                    "Iniciaste sesión, pero faltan las tablas compartidas en Supabase. "
                    "El menú seguirá disponible. Ejecuta SUPABASE_SHARED_DATA.sql "
                    "en el SQL Editor del proyecto para habilitar la sincronización."
                )
            QtWidgets.QMessageBox.warning(self, "Sincronización pendiente", message)
            return False

    def show_reports(self):
        if not self._ensure_shared_stores("reports"):
            return
        ReportsDialog(self, inventory_store=self.inventory_store, reservation_store=self.reservation_store).exec()

    def show_profile(self):
        dialog = ProfileDialog(self.user, self.auth, self)
        dialog.profile_updated.connect(self._profile_updated)
        dialog.exec()

    def _profile_updated(self, user):
        self.user.update(user)
        self.welcome_title.setText(f"¡Bienvenido, {self.user['full_name']}!")

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.theme_selected.connect(self._apply_theme)
        dialog.exec()

    def _apply_theme(self, theme_id=None):
        palette = theme_palette(theme_id)
        for widget in (self.options_content, self.options_scroll, self.options_scroll.viewport()):
            widget_palette = widget.palette()
            widget_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(palette["background"]))
            widget.setPalette(widget_palette)
            widget.setAutoFillBackground(True)
        self.options_scroll.setStyleSheet(f"QScrollArea {{ background: {palette['background']}; border: 0; }}")
        self.setStyleSheet(theme_stylesheet(theme_id) + f"""
            QWidget#menuBackground {{ background: {palette['background']}; }}
            QWidget#menuOptionsContent {{ background: {palette['background']}; }}
            QLabel#menuBrand {{ color: {palette['primary']}; font-size: 11px; font-weight: 700; letter-spacing: 1px; }}
            QLabel#menuTitle {{ color: {palette['text']}; font-size: 26px; font-weight: 700; }}
            QLabel#menuSubtitle {{ color: {palette['muted']}; font-size: 13px; }}
            QPushButton#menuCard, QPushButton#menuCardAccent {{
                text-align: left; background: {palette['surface']}; color: {palette['text']};
                border: 1px solid {palette['outline']}; border-left: 5px solid {palette['primary']};
                border-radius: 13px; padding: 0;
            }}
            QPushButton#menuCard:hover {{ background: {palette['highlight']}; border-color: {palette['primary']}; }}
            QPushButton#menuCardAccent {{ border-left-color: {palette['secondary']}; }}
            QPushButton#menuCardAccent:hover {{ background: {palette['highlight']}; border-color: {palette['secondary']}; }}
            QLabel#menuCardTitle {{ color: {palette['text']}; font-size: 16px; font-weight: 700; }}
            QLabel#menuCardDescription {{ color: {palette['muted']}; font-size: 12px; }}
            QLabel#menuCardArrow {{ color: {palette['primary']}; font-size: 30px; padding-right: 2px; }}
        """)
        for card in (self.reserve_card, self.reservations_card, self.inventory_card,
                     self.products_card, self.reports_card, self.profile_card, self.settings_card):
            card.refresh_icon()
        self.activity_chart.refresh()
