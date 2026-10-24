"""Registro local de reservas para la aplicacion de escritorio Cancha."""

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from .storage import database_path
from .theme import (
    DIALOG_HEIGHT, DIALOG_MIN_HEIGHT, DIALOG_MIN_WIDTH, DIALOG_WIDTH,
    theme_palette, theme_stylesheet,
)


DB_PATH = database_path()
PERU_TZ = timezone(timedelta(hours=-5))


def peru_now():
    return datetime.now(PERU_TZ)


class ReservationStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        self.initialize()

    def _connect(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self._connect() as connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS reservations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    court_name TEXT NOT NULL,
                    manager_name TEXT NOT NULL,
                    manager_document TEXT,
                    manager_phone TEXT,
                    booker_name TEXT NOT NULL,
                    booker_document TEXT,
                    booker_phone TEXT,
                    reservation_date TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    duration_minutes INTEGER NOT NULL CHECK(duration_minutes > 0),
                    notes TEXT,
                    created_by_user_id TEXT,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Reservada',
                    hourly_rate REAL NOT NULL DEFAULT 0 CHECK(hourly_rate >= 0),
                    reservation_amount REAL NOT NULL DEFAULT 0 CHECK(reservation_amount >= 0)
                )
            """)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(reservations)")}
            if "hourly_rate" not in columns:
                connection.execute("ALTER TABLE reservations ADD COLUMN hourly_rate REAL NOT NULL DEFAULT 0")
            if "reservation_amount" not in columns:
                connection.execute("ALTER TABLE reservations ADD COLUMN reservation_amount REAL NOT NULL DEFAULT 0")
                connection.execute("""
                    UPDATE reservations
                    SET reservation_amount = hourly_rate * duration_minutes / 60.0
                    WHERE hourly_rate > 0
                """)
            connection.execute("""
                CREATE INDEX IF NOT EXISTS idx_reservations_schedule
                ON reservations(reservation_date, start_time)
            """)

    def create(self, record):
        self._validate_and_check_overlap(record)
        with self._connect() as connection:
            connection.execute("""
                INSERT INTO reservations (
                    court_name, manager_name, manager_document, manager_phone,
                    booker_name, booker_document, booker_phone, reservation_date,
                    start_time, duration_minutes, notes, created_by_user_id, created_at,
                    hourly_rate, reservation_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, self._record_values(record) + (
                record.get("created_by_user_id"),
                datetime.now().isoformat(timespec="seconds"),
                0,
                record.get("reservation_amount", 0),
            ))

    def update(self, reservation_id, record):
        current = self.get(reservation_id)
        if current is None:
            raise ValueError("No se encontró la reserva.")
        if current["status"] in ("Confirmada", "Cerrada"):
            raise ValueError("La reserva está cerrada y ya no se puede editar.")
        self._validate_and_check_overlap(record, exclude_id=reservation_id)
        with self._connect() as connection:
            connection.execute("""
                UPDATE reservations SET court_name=?, manager_name=?, manager_document=?,
                    manager_phone=?, booker_name=?, booker_document=?, booker_phone=?,
                    reservation_date=?, start_time=?, duration_minutes=?, notes=?, hourly_rate=?,
                    reservation_amount=?
                WHERE id=?
            """, self._record_values(record) + (0, record.get("reservation_amount", 0), reservation_id))

    def confirm(self, reservation_id):
        with self._connect() as connection:
            connection.execute(
                "UPDATE reservations SET status = 'Cerrada' WHERE id = ? AND status = 'Reservada'",
                (reservation_id,),
            )

    @staticmethod
    def _record_values(record):
        return (
            record["court_name"], record["manager_name"], record["manager_document"],
            record["manager_phone"], record["booker_name"], record["booker_document"],
            record["booker_phone"], record["reservation_date"], record["start_time"],
            record["duration_minutes"], record["notes"],
        )

    def _validate_and_check_overlap(self, record, exclude_id=None):
        start = datetime.strptime(record["start_time"], "%H:%M").time()
        start_minutes = start.hour * 60 + start.minute
        end_minutes = start_minutes + int(record["duration_minutes"])
        if end_minutes > 24 * 60:
            raise ValueError("La reserva no puede terminar después de la medianoche.")
        with self._connect() as connection:
            existing = connection.execute("""
            SELECT id, start_time, duration_minutes FROM reservations
                WHERE reservation_date = ?
                    AND status IN ('Reservada', 'Confirmada')
            """, (record["reservation_date"],)).fetchall()
            for row in existing:
                if row["id"] == exclude_id:
                    continue
                other_start = datetime.strptime(row["start_time"], "%H:%M").time()
                other_start_minutes = other_start.hour * 60 + other_start.minute
                other_end_minutes = other_start_minutes + row["duration_minutes"]
                if start_minutes < other_end_minutes and other_start_minutes < end_minutes:
                    raise ValueError("Ese horario se cruza con otra reserva del día.")

    def delete(self, reservation_id):
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM reservations WHERE id = ? AND status != 'Confirmada'",
                (reservation_id,),
            )

    def get(self, reservation_id):
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM reservations WHERE id = ?", (reservation_id,)).fetchone()
        return dict(row) if row else None

    def list_all(self):
        with self._connect() as connection:
            rows = connection.execute("""
                SELECT * FROM reservations ORDER BY reservation_date DESC, start_time DESC, id DESC
            """).fetchall()
        return [dict(row) for row in rows]

    def list_for_date(self, reservation_date):
        with self._connect() as connection:
            rows = connection.execute("""
                SELECT * FROM reservations WHERE reservation_date = ?
                ORDER BY start_time ASC, id ASC
            """, (reservation_date,)).fetchall()
        return [dict(row) for row in rows]

    def daily_closed_minutes(self, days=7):
        """Horas reservadas cerradas por dia; no equivale a dinero cobrado."""
        with self._connect() as connection:
            rows = connection.execute("""
                SELECT reservation_date, SUM(duration_minutes) AS minutes
                FROM reservations
                WHERE status IN ('Cerrada', 'Confirmada')
                    AND reservation_date >= date('now', ?)
                    AND reservation_date <= date('now')
                GROUP BY reservation_date
                ORDER BY reservation_date
            """, (f"-{max(1, int(days) - 1)} days",)).fetchall()
        return {row["reservation_date"]: row["minutes"] or 0 for row in rows}

    def daily_court_revenue(self, days=7):
        """Ingresos de alquiler para reservas cerradas con tarifa registrada."""
        with self._connect() as connection:
            rows = connection.execute("""
                SELECT reservation_date, SUM(reservation_amount) AS revenue
                FROM reservations
                WHERE status IN ('Reservada', 'Confirmada', 'Cerrada')
                    AND reservation_amount > 0
                    AND reservation_date >= date('now', ?)
                    AND reservation_date <= date('now')
                GROUP BY reservation_date
            """, (f"-{max(1, int(days) - 1)} days",)).fetchall()
        return {row[0]: row[1] or 0 for row in rows}

    def court_revenue_between(self, start_date, end_date):
        """Montos de reservas de cancha agrupados por fecha para reportes."""
        with self._connect() as connection:
            rows = connection.execute("""
                SELECT reservation_date, SUM(reservation_amount) AS revenue
                FROM reservations
                WHERE status IN ('Reservada', 'Confirmada', 'Cerrada')
                    AND reservation_amount > 0
                    AND reservation_date BETWEEN ? AND ?
                GROUP BY reservation_date
                ORDER BY reservation_date
            """, (start_date, end_date)).fetchall()
        return {row[0]: row[1] or 0 for row in rows}


class ReservationDialog(QtWidgets.QDialog):
    def __init__(self, user, parent=None, store=None, list_mode=False):
        super().__init__(parent)
        self.user = user
        self.store = store or ReservationStore()
        self._loading_reservation = False
        self.setWindowTitle("Reservas de canchas | Cancha")
        self.setMinimumSize(DIALOG_MIN_WIDTH, DIALOG_MIN_HEIGHT)
        self.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
        palette = theme_palette()
        self.setStyleSheet(theme_stylesheet() + f"""
            QDialog {{ background: {palette['background']}; }}
            QLabel {{ color: {palette['text']}; font-size: 12px; }}
            QLineEdit, QDateEdit, QTimeEdit, QSpinBox {{
                background: {palette['surface']}; border: 1px solid {palette['outline']}; border-radius: 9px;
                padding: 9px 11px; min-height: 20px; color: {palette['text']};
            }}
            QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus, QSpinBox:focus {{
                border: 1px solid {palette['primary']};
            }}
            QPushButton {{
                background: {palette['primary']}; color: white; border: 0; border-radius: 9px;
                padding: 11px 16px; font-weight: 600; min-height: 22px;
            }}
            QPushButton:hover {{ background: {palette['text']}; }}
            QGroupBox {{
                background: {palette['surface']}; border: 1px solid {palette['outline']}; border-radius: 12px;
                margin-top: 13px; padding: 14px 12px 12px; font-weight: 700;
                color: {palette['primary']};
            }}
            QGroupBox::title {{ subcontrol-origin: margin; left: 13px; padding: 0 5px; }}
            QTableWidget {{ background: {palette['surface']}; border: 1px solid {palette['outline']}; border-radius: 8px; }}
            QHeaderView::section {{ background: {palette['highlight']}; padding: 8px; border: 0; font-weight: 600; }}
        """)
        layout = QtWidgets.QVBoxLayout(self)
        if list_mode:
            self._build_list(layout)
        else:
            self.form_scroll = QtWidgets.QScrollArea()
            self.form_scroll.setWidgetResizable(True)
            self.form_scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            self.form_scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            self.form_scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            form_content = QtWidgets.QWidget()
            form_content.setObjectName("reservationFormContent")
            form_content.setAutoFillBackground(True)
            form_palette = form_content.palette()
            form_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(palette["background"]))
            form_content.setPalette(form_palette)
            self.form_scroll.setAutoFillBackground(True)
            self.form_scroll.setStyleSheet(f"QScrollArea {{ background: {palette['background']}; border: 0; }}")
            viewport_palette = self.form_scroll.viewport().palette()
            viewport_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(palette["background"]))
            self.form_scroll.viewport().setPalette(viewport_palette)
            self.form_scroll.viewport().setAutoFillBackground(True)
            form_layout = QtWidgets.QVBoxLayout(form_content)
            form_layout.setContentsMargins(4, 4, 12, 4)
            self._build_form(form_layout)
            form_layout.addStretch()
            self.form_scroll.setWidget(form_content)
            layout.addWidget(self.form_scroll)
            actions = QtWidgets.QHBoxLayout()
            actions.setContentsMargins(8, 8, 8, 8)
            cancel_button = QtWidgets.QPushButton("Cancelar")
            cancel_button.setMinimumHeight(44)
            cancel_button.setObjectName("secondaryButton")
            cancel_button.clicked.connect(self.reject)
            save_button = QtWidgets.QPushButton("Guardar reserva")
            save_button.setMinimumHeight(44)
            save_button.setDefault(True)
            save_button.clicked.connect(self._save)
            actions.addWidget(cancel_button)
            actions.addWidget(save_button)
            layout.addLayout(actions)
            self.resize(DIALOG_WIDTH, DIALOG_HEIGHT)

    def _build_form(self, layout):
        palette = theme_palette()
        title = QtWidgets.QLabel("Nueva reserva")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {palette['primary']};")
        layout.addWidget(title)
        self.editing_id = None
        hint = QtWidgets.QLabel("Completa los datos para separar un horario.")
        hint.setStyleSheet(f"color: {palette['muted']};")
        layout.addWidget(hint)

        schedule = QtWidgets.QGroupBox("Cancha y horario")
        schedule_layout = QtWidgets.QVBoxLayout(schedule)
        self.court = QtWidgets.QLineEdit()
        self.court.setPlaceholderText("Cancha (por ejemplo: Cancha 1)")
        schedule_layout.addWidget(self.court)

        date_row = QtWidgets.QHBoxLayout()
        now = peru_now()
        today = QtCore.QDate(now.year, now.month, now.day)
        self.date = QtWidgets.QDateEdit(today)
        self.date.setCalendarPopup(True)
        self.date.setDisplayFormat("dd/MM/yyyy")
        self.date.setMinimumDate(today)
        self.time = QtWidgets.QTimeEdit(QtCore.QTime(now.hour, now.minute))
        self.time.setDisplayFormat("HH:mm")
        self.time.setMinimumTime(QtCore.QTime(0, 0))
        self.time.setReadOnly(True)
        self.time.setButtonSymbols(QtWidgets.QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.duration = QtWidgets.QSpinBox()
        self.duration.setRange(30, 720)
        self.duration.setSingleStep(30)
        self.duration.setValue(60)
        self.duration.setSuffix(" min")
        date_row.addWidget(QtWidgets.QLabel("Fecha"))
        date_row.addWidget(self.date)
        date_row.addWidget(QtWidgets.QLabel("Hora de inicio"))
        date_row.addWidget(self.time)
        date_row.addWidget(QtWidgets.QLabel("Tiempo"))
        date_row.addWidget(self.duration)
        schedule_layout.addLayout(date_row)
        self.availability_status = QtWidgets.QLabel("Horarios ocupados sombreados · selecciona una hora libre")
        self.availability_status.setStyleSheet(f"color: {palette['muted']}; font-size: 11px;")
        schedule_layout.addWidget(self.availability_status)
        self.availability_table = QtWidgets.QTableWidget(8, 6)
        self.availability_table.setObjectName("reservationAvailabilityTable")
        self.availability_table.horizontalHeader().hide()
        self.availability_table.verticalHeader().hide()
        self.availability_table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.availability_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectItems)
        self.availability_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.availability_table.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.availability_table.setShowGrid(False)
        self.availability_table.verticalHeader().setDefaultSectionSize(30)
        self.availability_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        self.availability_table.setFixedHeight(8 * 30 + 4)
        self.availability_table.cellClicked.connect(self._choose_available_time)
        schedule_layout.addWidget(self.availability_table)
        self._availability_timer = QtCore.QTimer(self)
        self._availability_timer.setSingleShot(True)
        self._availability_timer.timeout.connect(self._refresh_availability)
        amount_row = QtWidgets.QHBoxLayout()
        amount_row.addWidget(QtWidgets.QLabel("Monto acordado por la reserva"))
        self.reservation_amount = QtWidgets.QDoubleSpinBox()
        self.reservation_amount.setRange(0, 999999)
        self.reservation_amount.setDecimals(2)
        self.reservation_amount.setPrefix("S/ ")
        self.reservation_amount.setValue(0)
        amount_row.addWidget(self.reservation_amount)
        amount_row.addStretch(1)
        schedule_layout.addLayout(amount_row)
        layout.addWidget(schedule)

        self.date.dateChanged.connect(self._update_minimum_time)
        self.time.timeChanged.connect(self._enforce_future_time)
        self.time.editingFinished.connect(self._enforce_future_time)
        self.date.editingFinished.connect(lambda: self._update_minimum_time(self.date.date()))
        self.court.textChanged.connect(self._queue_availability_refresh)
        self.date.dateChanged.connect(lambda _date: self._queue_availability_refresh())
        self.duration.valueChanged.connect(lambda _value: self._queue_availability_refresh())
        self._refresh_availability()
        self._update_minimum_time(self.date.date())

        manager = QtWidgets.QGroupBox("Vendedor")
        manager_layout = QtWidgets.QVBoxLayout(manager)
        self.manager_name = QtWidgets.QLineEdit(self.user.get("full_name", ""))
        self.manager_name.setPlaceholderText("Nombre completo")
        self.manager_name.setReadOnly(True)
        self.manager_name.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.manager_name.setStyleSheet(
            f"background: {palette['highlight']}; color: {palette['muted']};"
        )
        self.manager_document_type, manager_document_row = self._document_input_row()
        manager_layout.addLayout(manager_document_row)
        self.manager_document = QtWidgets.QLineEdit()
        self._configure_document_field(self.manager_document, self.manager_document_type)
        manager_layout.addWidget(self.manager_document)
        self.manager_phone = QtWidgets.QLineEdit()
        self.manager_phone.setPlaceholderText("Celular: 9 dígitos")
        self._configure_phone_field(self.manager_phone)
        for field in (self.manager_name, self.manager_phone):
            manager_layout.addWidget(field)
        layout.addWidget(manager)

        customer = QtWidgets.QGroupBox("Cliente")
        customer_layout = QtWidgets.QVBoxLayout(customer)
        self.booker_name = QtWidgets.QLineEdit()
        self.booker_name.setPlaceholderText("Nombre completo del cliente")
        customer_layout.addWidget(self.booker_name)
        self.booker_document_type, booker_document_row = self._document_input_row()
        customer_layout.addLayout(booker_document_row)
        self.booker_document = QtWidgets.QLineEdit()
        self._configure_document_field(self.booker_document, self.booker_document_type)
        customer_layout.addWidget(self.booker_document)
        self.booker_phone = QtWidgets.QLineEdit()
        self.booker_phone.setPlaceholderText("Celular: 9 dígitos")
        self._configure_phone_field(self.booker_phone)
        customer_layout.addWidget(self.booker_phone)
        layout.addWidget(customer)

        notes_group = QtWidgets.QGroupBox("Observación")
        notes_layout = QtWidgets.QVBoxLayout(notes_group)
        self.notes = QtWidgets.QPlainTextEdit()
        self.notes.setPlaceholderText("Agrega aquí una observación o comentario para esta reserva (opcional).")
        self.notes.setMaximumHeight(100)
        notes_layout.addWidget(self.notes)
        layout.addWidget(notes_group)

    def _refresh_availability(self):
        if self._loading_reservation or not hasattr(self, "availability_table"):
            return
        table = self.availability_table
        table.clearContents()
        day = self.date.date().toString("yyyy-MM-dd")
        palette = theme_palette()
        try:
            reservations = self.store.list_for_date(day)
        except Exception as error:
            reservations = []
            self.availability_error = str(error)
        else:
            self.availability_error = ""
        if self.availability_error:
            self.availability_status.setText("No se pudo consultar la agenda; las horas se comprobarán al guardar.")
        else:
            self.availability_status.setText("Ocupaciones de toda la agenda sombreadas, sin importar la cancha.")
        reserved = [row for row in reservations
                    if row.get("status") in ("Reservada", "Confirmada")
                    and str(row.get("id")) != str(self.editing_id)]
        duration = self.duration.value()
        now = peru_now()
        is_today = self.date.date() == QtCore.QDate(now.year, now.month, now.day)
        selected_item = None
        for index in range(48):
            start = index * 30
            end = start + duration
            time_text = f"{start // 60:02d}:{start % 60:02d}"
            conflict = next((row for row in reserved
                             if start < self._minutes_of(row["start_time"]) + int(row["duration_minutes"])
                             and self._minutes_of(row["start_time"]) < end), None)
            is_past = is_today and start < now.hour * 60 + now.minute
            unavailable = bool(conflict) or is_past or end > 1440 or bool(self.availability_error)
            item = QtWidgets.QTableWidgetItem(time_text)
            item.setTextAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, not unavailable)
            if unavailable:
                item.setFlags(QtCore.Qt.ItemFlag.NoItemFlags)
                item.setBackground(QtGui.QColor(palette["highlight"]))
                item.setForeground(QtGui.QColor(palette["muted"]))
                item.setToolTip("Horario ocupado" if conflict else "Hora no disponible")
            else:
                item.setFlags(QtCore.Qt.ItemFlag.ItemIsEnabled | QtCore.Qt.ItemFlag.ItemIsSelectable)
                item.setBackground(QtGui.QColor(palette["surface"]))
                item.setForeground(QtGui.QColor(palette["text"]))
                if self.time.time().toString("HH:mm") == time_text:
                    selected_item = item
            table.setItem(index // 6, index % 6, item)
        if selected_item:
            table.setCurrentItem(selected_item)

    def _queue_availability_refresh(self):
        if not self._loading_reservation and hasattr(self, "_availability_timer"):
            self._availability_timer.start(300)

    @staticmethod
    def _minutes_of(value):
        parsed = QtCore.QTime.fromString(str(value)[:5], "HH:mm")
        return parsed.hour() * 60 + parsed.minute() if parsed.isValid() else 0

    def _choose_available_time(self, row, column):
        item = self.availability_table.item(row, column)
        if item is None or not item.data(QtCore.Qt.ItemDataRole.UserRole):
            return
        selected = QtCore.QTime.fromString(item.text(), "HH:mm")
        if selected.isValid():
            self.time.setTime(selected)
    @staticmethod
    def _document_input_row():
        row = QtWidgets.QHBoxLayout()
        row.addWidget(QtWidgets.QLabel("Tipo de documento"))
        document_type = QtWidgets.QComboBox()
        document_type.addItems(["DNI", "Carné de Extranjería"])
        row.addWidget(document_type)
        return document_type, row

    @staticmethod
    def _configure_document_field(field, document_type):
        field.setMaxLength(8)
        field.setValidator(QtGui.QRegularExpressionValidator(
            QtCore.QRegularExpression(r"[0-9]{0,8}"), field
        ))
        field.setPlaceholderText("Ingrese 8 dígitos")
        document_type.currentIndexChanged.connect(
            lambda index, target=field: ReservationDialog._set_document_type(target, index)
        )

    @staticmethod
    def _set_document_type(field, index):
        required_length = 8 if index == 0 else 12
        digits = field.text()[:required_length]
        field.setMaxLength(required_length)
        field.setValidator(QtGui.QRegularExpressionValidator(
            QtCore.QRegularExpression(r"[0-9]{0,%d}" % field.maxLength()), field
        ))
        field.setPlaceholderText(f"Ingrese {field.maxLength()} dígitos")
        field.setText(digits)

    @staticmethod
    def _configure_phone_field(field):
        field.setMaxLength(9)
        field.setValidator(QtGui.QRegularExpressionValidator(
            QtCore.QRegularExpression(r"[0-9]{0,9}"), field
        ))

    def _update_minimum_time(self, selected_date):
        now = peru_now()
        today = QtCore.QDate(now.year, now.month, now.day)
        if selected_date == today:
            self._set_minimum_time_for_today(now)
        else:
            self.time.setMinimumTime(QtCore.QTime(0, 0))

    def _set_minimum_time_for_today(self, now):
        minimum = QtCore.QTime(now.hour, now.minute)
        if now.second or now.microsecond:
            minimum = minimum.addSecs(60)
        self.time.setMinimumTime(minimum)
        if self.time.time() < minimum:
            self.time.setTime(minimum)

    def _enforce_future_time(self, *_args):
        now = peru_now()
        today = QtCore.QDate(now.year, now.month, now.day)
        if self.date.date() == today:
            self._set_minimum_time_for_today(now)

    def _save(self):
        court_name = self.court.text().strip()
        manager_name = self.manager_name.text().strip()
        booker_name = self.booker_name.text().strip()
        if not court_name or not manager_name or not booker_name:
            QtWidgets.QMessageBox.warning(
                self, "Faltan datos", "Completa la cancha y los nombres de quien gestiona y quien reserva."
            )
            return
        if self.reservation_amount.value() <= 0:
            QtWidgets.QMessageBox.warning(
                self, "Falta el monto", "Ingresa el monto total acordado con el cliente por la reserva."
            )
            return
        document_fields = (
            ("del vendedor", self.manager_document_type.currentText(), self.manager_document.text().strip()),
            ("del cliente", self.booker_document_type.currentText(), self.booker_document.text().strip()),
        )
        for label, document_type, document in document_fields:
            required_length = 8 if document_type == "DNI" else 12
            if not document or not document.isdigit() or len(document) != required_length:
                QtWidgets.QMessageBox.warning(
                    self, "Documento inválido",
                    f"El documento {label} ({document_type}) debe contener exactamente {required_length} dígitos.",
                )
                return
        phone_fields = (
            ("del vendedor", self.manager_phone.text().strip()),
            ("del cliente", self.booker_phone.text().strip()),
        )
        for label, phone in phone_fields:
            if not phone or not phone.isdigit() or len(phone) != 9:
                QtWidgets.QMessageBox.warning(
                    self, "Teléfono inválido",
                    f"El teléfono {label} debe contener exactamente 9 dígitos.",
                )
                return
        now = peru_now()
        selected_date = self.date.date()
        today = QtCore.QDate(now.year, now.month, now.day)
        selected_time = self.time.time()
        if selected_date < today or (
            selected_date == today
            and (selected_time.hour(), selected_time.minute()) <= (now.hour, now.minute)
        ):
            QtWidgets.QMessageBox.warning(
                self, "Fecha u hora pasada", "Elige una fecha y hora futura según la hora de Perú."
            )
            return
        record = {
            "court_name": court_name,
            "manager_name": manager_name,
            "manager_document": self.manager_document.text().strip(),
            "manager_phone": self.manager_phone.text().strip(),
            "booker_name": booker_name,
            "booker_document": self.booker_document.text().strip(),
            "booker_phone": self.booker_phone.text().strip(),
            "reservation_date": self.date.date().toString("yyyy-MM-dd"),
            "start_time": self.time.time().toString("HH:mm"),
            "duration_minutes": self.duration.value(),
            "reservation_amount": self.reservation_amount.value(),
            "notes": self.notes.toPlainText().strip(),
            "created_by_user_id": self.user.get("id"),
        }
        try:
            if self.editing_id is None:
                self.store.create(record)
            else:
                self.store.update(self.editing_id, record)
        except Exception as error:
            QtWidgets.QMessageBox.warning(self, "No se pudo guardar la reserva", str(error))
            return
        self.accept()

    def _build_list(self, layout):
        palette = theme_palette()
        title = QtWidgets.QLabel("Agenda de reservas")
        title.setStyleSheet(f"font-size: 22px; font-weight: 700; color: {palette['primary']};")
        layout.addWidget(title)
        date_bar = QtWidgets.QHBoxLayout()
        date_bar.addWidget(QtWidgets.QLabel("Reservas del día"))
        self.agenda_date = QtWidgets.QDateEdit()
        self.agenda_date.setCalendarPopup(True)
        self.agenda_date.setDisplayFormat("dddd, dd/MM/yyyy")
        self.agenda_date.setDate(QtCore.QDate.currentDate())
        self.agenda_date.setMinimumWidth(210)
        date_bar.addWidget(self.agenda_date)
        date_bar.addStretch()
        layout.addLayout(date_bar)

        actions = QtWidgets.QHBoxLayout()
        self.edit_button = QtWidgets.QPushButton("Editar")
        self.delete_button = QtWidgets.QPushButton("Eliminar")
        self.confirm_button = QtWidgets.QPushButton("Confirmar")
        for button in (self.edit_button, self.delete_button, self.confirm_button):
            button.setMinimumHeight(40)
            button.setEnabled(False)
            actions.addWidget(button)
        self.edit_button.clicked.connect(self._edit_selected)
        self.delete_button.clicked.connect(self._delete_selected)
        self.confirm_button.clicked.connect(self._confirm_selected)
        actions.addStretch()
        close_button = QtWidgets.QPushButton("Cerrar")
        close_button.setMinimumHeight(40)
        close_button.setObjectName("secondaryButton")
        close_button.clicked.connect(self.accept)
        actions.addWidget(close_button)
        layout.addLayout(actions)

        table = QtWidgets.QTableWidget()
        table.setObjectName("reservationListTable")
        table.setAutoFillBackground(True)
        table_palette = table.palette()
        table_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(palette["background"]))
        table_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(palette["background"]))
        table.setPalette(table_palette)
        table.viewport().setAutoFillBackground(True)
        viewport_palette = table.viewport().palette()
        viewport_palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(palette["background"]))
        viewport_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(palette["background"]))
        table.viewport().setPalette(viewport_palette)
        headers = ["Hora", "Cancha", "Tiempo", "Estado", "Vendedor", "Cliente", "Teléfono"]
        rows = self.store.list_for_date(self.agenda_date.date().toString("yyyy-MM-dd"))
        self.reservation_rows = rows
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(rows))
        table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        self.reservation_table = table
        self.agenda_date.dateChanged.connect(self._refresh_reservation_list)
        for row_index, row in enumerate(rows):
            self._set_table_row(row_index, row)
        table.cellDoubleClicked.connect(self._show_reservation_details)
        table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table)
        self.empty_label = QtWidgets.QLabel("No hay reservas registradas para este día.")
        self.empty_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(
            f"font-size: 16px; color: {palette['muted']}; padding: 24px;"
        )
        self.empty_label.setVisible(not rows)
        layout.addWidget(self.empty_label)
        table.itemSelectionChanged.connect(self._update_selection_actions)

    def _selected_reservation(self):
        row_index = self.reservation_table.currentRow()
        if row_index < 0:
            return None
        reservation_id_item = self.reservation_table.item(row_index, 0)
        reservation_id = reservation_id_item.data(QtCore.Qt.ItemDataRole.UserRole)
        return self.store.get(reservation_id) if reservation_id is not None else None

    def _update_selection_actions(self):
        reservation = self._selected_reservation()
        selected = reservation is not None
        editable = selected and reservation["status"] not in ("Confirmada", "Cerrada")
        self.edit_button.setEnabled(editable)
        self.delete_button.setEnabled(editable)
        self.confirm_button.setEnabled(selected and reservation["status"] == "Reservada")

    def _confirm_selected(self):
        reservation = self._selected_reservation()
        if reservation is None or reservation["status"] != "Reservada":
            return
        answer = QtWidgets.QMessageBox.question(
            self, "Confirmar y cerrar reserva",
            "Al confirmar, la reserva quedará cerrada y ya no se podrá editar ni eliminar. "
            "¿Deseas continuar?",
        )
        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                self.store.confirm(reservation["id"])
                self._refresh_reservation_list()
            except Exception as error:
                QtWidgets.QMessageBox.critical(self, "No se pudo confirmar", str(error))

    def _edit_selected(self):
        reservation = self._selected_reservation()
        if reservation is None or reservation["status"] in ("Confirmada", "Cerrada"):
            return
        dialog = ReservationDialog(self.user, self, self.store)
        dialog.setWindowTitle("Editar reserva | Cancha")
        dialog._loading_reservation = True
        dialog.editing_id = reservation["id"]
        dialog.findChild(QtWidgets.QLabel).setText("Editar reserva")
        for button in dialog.findChildren(QtWidgets.QPushButton):
            if button.text() == "Guardar reserva":
                button.setText("Guardar cambios")
        dialog.court.setText(reservation["court_name"])
        dialog.manager_name.setText(reservation["manager_name"])
        dialog.manager_document.setText(reservation["manager_document"] or "")
        dialog.manager_phone.setText(reservation["manager_phone"] or "")
        dialog.booker_name.setText(reservation["booker_name"])
        dialog.booker_document.setText(reservation["booker_document"] or "")
        dialog.booker_phone.setText(reservation["booker_phone"] or "")
        dialog.notes.setPlainText(reservation["notes"] or "")
        reservation_date = QtCore.QDate.fromString(reservation["reservation_date"], "yyyy-MM-dd")
        dialog.date.setMinimumDate(QtCore.QDate(2000, 1, 1))
        dialog.date.setDate(reservation_date)
        dialog.time.setMinimumTime(QtCore.QTime(0, 0))
        dialog.time.setTime(QtCore.QTime.fromString(reservation["start_time"], "HH:mm"))
        dialog.duration.setValue(reservation["duration_minutes"])
        dialog.reservation_amount.setValue(reservation.get("reservation_amount", 0))
        dialog._loading_reservation = False
        dialog._refresh_availability()
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self._refresh_reservation_list()

    def _show_reservation_details(self, _row, _column):
        reservation = self._selected_reservation()
        if reservation is None:
            return
        details = QtWidgets.QDialog(self)
        details.setWindowTitle("Detalle de reserva | Cancha")
        details.setMinimumWidth(440)
        details.setStyleSheet(self.styleSheet())
        palette = theme_palette()
        layout = QtWidgets.QVBoxLayout(details)
        title = QtWidgets.QLabel("Detalle de la reserva")
        title.setStyleSheet(f"font-size: 21px; font-weight: 700; color: {palette['primary']};")
        layout.addWidget(title)

        sections = (
            ("Cancha y horario", (
                ("Cancha", reservation["court_name"]),
                ("Fecha", reservation["reservation_date"]),
                ("Hora de inicio", reservation["start_time"]),
                ("Duración", f'{reservation["duration_minutes"]} minutos'),
                ("Monto acordado", f'S/ {reservation.get("reservation_amount", 0):.2f}'),
                ("Estado", reservation["status"]),
            )),
            ("Vendedor", (
                ("Nombre", reservation["manager_name"]),
                ("Documento", reservation["manager_document"]),
                ("Teléfono", reservation["manager_phone"]),
            )),
            ("Cliente", (
                ("Nombre", reservation["booker_name"]),
                ("Documento", reservation["booker_document"]),
                ("Teléfono", reservation["booker_phone"]),
            )),
            ("Observación", (("Comentario", reservation["notes"] or "Sin observación agregada"),)),
        )
        for heading, values in sections:
            group = QtWidgets.QGroupBox(heading)
            group_layout = QtWidgets.QFormLayout(group)
            for label, value in values:
                value_label = QtWidgets.QLabel(value or "No especificado")
                value_label.setWordWrap(True)
                group_layout.addRow(f"{label}:", value_label)
            layout.addWidget(group)

        close_button = QtWidgets.QPushButton("Cerrar")
        close_button.clicked.connect(details.accept)
        layout.addWidget(close_button)
        details.exec()

    def _delete_selected(self):
        reservation = self._selected_reservation()
        if reservation is None or reservation["status"] in ("Confirmada", "Cerrada"):
            return
        answer = QtWidgets.QMessageBox.question(
            self, "Eliminar reserva", "¿Seguro que quieres eliminar esta reserva? Esta acción no se puede deshacer."
        )
        if answer == QtWidgets.QMessageBox.StandardButton.Yes:
            try:
                self.store.delete(reservation["id"])
                self._refresh_reservation_list()
            except Exception as error:
                QtWidgets.QMessageBox.critical(self, "No se pudo eliminar", str(error))

    def _refresh_reservation_list(self, *_args):
        self.reservation_table.setSortingEnabled(False)
        try:
            rows = self.store.list_for_date(self.agenda_date.date().toString("yyyy-MM-dd"))
        except Exception as error:
            QtWidgets.QMessageBox.critical(self, "No se pudo sincronizar", str(error))
            return
        self.reservation_rows = rows
        self.reservation_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            self._set_table_row(row_index, row)
        self.reservation_table.setSortingEnabled(True)
        self.reservation_table.clearSelection()
        self.empty_label.setVisible(not rows)
        self._update_selection_actions()

    def _set_table_row(self, row_index, row):
        values = [
            row["start_time"], row["court_name"], f'{row["duration_minutes"]} min',
            row["status"], row["manager_name"], row["booker_name"],
            row["booker_phone"],
        ]
        for column, value in enumerate(values):
            item = QtWidgets.QTableWidgetItem(value or "")
            if column == 0:
                item.setData(QtCore.Qt.ItemDataRole.UserRole, row["id"])
            self.reservation_table.setItem(row_index, column, item)
