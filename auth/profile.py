"""Edición de datos del vendedor y credenciales de su cuenta."""

from datetime import datetime, timedelta, timezone

from PySide6 import QtCore, QtGui, QtWidgets

from .supabase_client import SupabaseAuthError
from .theme import (
    DIALOG_HEIGHT, DIALOG_MIN_HEIGHT, DIALOG_MIN_WIDTH, DIALOG_WIDTH,
    theme_palette, theme_stylesheet,
)


class ProfileDialog(QtWidgets.QDialog):
    profile_updated = QtCore.Signal(dict)

    def __init__(self, user, auth, parent=None):
        super().__init__(parent)
        self.user = user
        self.auth = auth
        self.setWindowTitle("Perfil | Cancha")
        self.setMinimumSize(DIALOG_MIN_WIDTH, DIALOG_MIN_HEIGHT)
        self.resize(DIALOG_WIDTH, DIALOG_HEIGHT)
        self.setStyleSheet(theme_stylesheet())
        palette = theme_palette()
        layout = QtWidgets.QVBoxLayout(self)
        content = QtWidgets.QWidget()
        content.setObjectName("profileContent")
        content.setAutoFillBackground(True)
        content_palette = content.palette()
        content_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(palette["background"]))
        content.setPalette(content_palette)
        content_layout = QtWidgets.QVBoxLayout(content)

        title = QtWidgets.QLabel("Perfil del vendedor")
        title.setStyleSheet(f"font-size:24px; font-weight:700; color:{palette['primary']};")
        content_layout.addWidget(title)
        subtitle = QtWidgets.QLabel("Actualiza tus datos y administra la contraseña de la cuenta.")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"color:{palette['muted']};")
        content_layout.addWidget(subtitle)

        self.name = QtWidgets.QLineEdit(str(user.get("full_name") or ""))
        self.document_type = QtWidgets.QComboBox()
        self.document_type.addItems(["DNI", "Carné de Extranjería"])
        saved_type = user.get("document_type", "DNI")
        self.document_type.setCurrentIndex(1 if saved_type == "Carné de Extranjería" else 0)
        self.document = QtWidgets.QLineEdit(str(user.get("dni") or ""))
        self.document.setMaxLength(8 if self.document_type.currentIndex() == 0 else 12)
        self.document.setValidator(QtGui.QRegularExpressionValidator(
            QtCore.QRegularExpression(r"[0-9]{0,%d}" % self.document.maxLength()), self.document
        ))
        self.document_type.currentIndexChanged.connect(self._set_document_type)
        self.address = QtWidgets.QLineEdit(str(user.get("address") or ""))
        self.address.setMaxLength(180)
        self.phone = QtWidgets.QLineEdit(str(user.get("phone") or ""))
        self.phone.setMaxLength(9)
        self.phone.setValidator(QtGui.QRegularExpressionValidator(
            QtCore.QRegularExpression(r"[0-9]{0,9}"), self.phone
        ))
        self.phone.setPlaceholderText("Celular de 9 dígitos")
        self.email = QtWidgets.QLineEdit(str(user.get("email") or ""))
        self.account_id = QtWidgets.QLineEdit(str(user.get("id") or ""))
        self.account_id.setReadOnly(True)
        seller_code = "VEN-" + str(user.get("id") or "").replace("-", "").upper()[:8]
        self.seller_code = QtWidgets.QLineEdit(seller_code)
        self.seller_code.setReadOnly(True)
        self.joined_at = QtWidgets.QLineEdit(self._format_joined_date(user.get("created_at", "")))
        self.joined_at.setReadOnly(True)
        personal_group = QtWidgets.QGroupBox("1. Datos personales")
        personal = QtWidgets.QGridLayout(personal_group)
        personal.setHorizontalSpacing(14)
        personal.setVerticalSpacing(18)
        personal.setContentsMargins(16, 24, 16, 16)
        personal.addWidget(QtWidgets.QLabel("Nombre completo"), 0, 0)
        personal.addWidget(self.name, 0, 1, 1, 3)
        personal.addWidget(QtWidgets.QLabel("Tipo de documento"), 1, 0)
        personal.addWidget(self.document_type, 1, 1)
        personal.addWidget(QtWidgets.QLabel("DNI / Carné"), 1, 2)
        personal.addWidget(self.document, 1, 3)
        personal.setColumnStretch(1, 1)
        personal.setColumnStretch(3, 1)
        content_layout.addWidget(personal_group)

        contact_group = QtWidgets.QGroupBox("2. Datos de contacto")
        contact = QtWidgets.QGridLayout(contact_group)
        contact.setHorizontalSpacing(14)
        contact.setVerticalSpacing(18)
        contact.setContentsMargins(16, 24, 16, 16)
        contact.addWidget(QtWidgets.QLabel("Dirección"), 0, 0)
        contact.addWidget(self.address, 0, 1, 1, 3)
        contact.addWidget(QtWidgets.QLabel("Teléfono"), 1, 0)
        contact.addWidget(self.phone, 1, 1)
        contact.addWidget(QtWidgets.QLabel("Correo electrónico"), 1, 2)
        contact.addWidget(self.email, 1, 3)
        contact.setColumnStretch(1, 1)
        contact.setColumnStretch(3, 1)
        content_layout.addWidget(contact_group)

        account_group = QtWidgets.QGroupBox("3. Datos de cuenta")
        account = QtWidgets.QGridLayout(account_group)
        account.setHorizontalSpacing(14)
        account.setVerticalSpacing(18)
        account.setContentsMargins(16, 24, 16, 16)
        account.addWidget(QtWidgets.QLabel("Código del vendedor"), 0, 0)
        account.addWidget(self.seller_code, 0, 1)
        account.addWidget(QtWidgets.QLabel("Fecha de ingreso"), 0, 2)
        account.addWidget(self.joined_at, 0, 3)
        account.addWidget(QtWidgets.QLabel("ID de cuenta"), 1, 0)
        account.addWidget(self.account_id, 1, 1, 1, 3)
        account.setColumnStretch(1, 1)
        account.setColumnStretch(3, 1)
        content_layout.addWidget(account_group)

        save_profile = QtWidgets.QPushButton("Guardar datos del perfil")
        save_profile.setObjectName("accentButton")
        save_profile.clicked.connect(self.save_profile)
        content_layout.addWidget(save_profile)

        password_group = QtWidgets.QGroupBox("4. Seguridad · Cambiar contraseña")
        password_form = QtWidgets.QGridLayout(password_group)
        password_form.setHorizontalSpacing(14)
        password_form.setVerticalSpacing(18)
        password_form.setContentsMargins(16, 24, 16, 16)
        self.current_password = QtWidgets.QLineEdit()
        self.current_password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.current_password.setPlaceholderText("Contraseña actual")
        self.new_password = QtWidgets.QLineEdit()
        self.new_password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.new_password.setPlaceholderText("Mínimo 8 caracteres")
        self.confirm_password = QtWidgets.QLineEdit()
        self.confirm_password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.confirm_password.setPlaceholderText("Repite la nueva contraseña")
        password_form.addWidget(QtWidgets.QLabel("Contraseña actual"), 0, 0)
        password_form.addWidget(self.current_password, 0, 1)
        password_form.addWidget(QtWidgets.QLabel("Nueva contraseña"), 0, 2)
        password_form.addWidget(self.new_password, 0, 3)
        password_form.addWidget(QtWidgets.QLabel("Confirmar contraseña"), 1, 0)
        password_form.addWidget(self.confirm_password, 1, 1, 1, 3)
        password_form.setColumnStretch(1, 1)
        password_form.setColumnStretch(3, 1)
        content_layout.addWidget(password_group)

        change_password = QtWidgets.QPushButton("Verificar y cambiar contraseña")
        change_password.clicked.connect(self.change_password)
        content_layout.addWidget(change_password)

        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        self.status.setStyleSheet(f"color:{palette['primary']}; padding:4px;")
        content_layout.addWidget(self.status)
        content_layout.addStretch(1)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        scroll.setAutoFillBackground(True)
        scroll.setStyleSheet(f"QScrollArea {{ background: {palette['background']}; border: 0; }}")
        viewport_palette = scroll.viewport().palette()
        viewport_palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(palette["background"]))
        scroll.viewport().setPalette(viewport_palette)
        scroll.viewport().setAutoFillBackground(True)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

        close = QtWidgets.QPushButton("Cerrar")
        close.setObjectName("secondaryButton")
        close.clicked.connect(self.accept)
        layout.addWidget(close, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

    def _set_document_type(self, index):
        length = 8 if index == 0 else 12
        self.document.setMaxLength(length)
        self.document.setValidator(QtGui.QRegularExpressionValidator(
            QtCore.QRegularExpression(r"[0-9]{0,%d}" % length), self.document
        ))
        self.document.setText(self.document.text()[:length])

    @staticmethod
    def _format_joined_date(value):
        if not value:
            return "No disponible"
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            lima = timezone(timedelta(hours=-5))
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(lima)
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            return value[:10]

    def save_profile(self):
        name = self.name.text().strip()
        document = self.document.text().strip()
        document_type = self.document_type.currentText()
        expected_length = 8 if self.document_type.currentIndex() == 0 else 12
        new_email = self.email.text().strip()
        if not name:
            self.status.setText("Ingresa tu nombre completo.")
            return
        if document and (not document.isdigit() or len(document) != expected_length):
            self.status.setText(f"El {document_type} debe contener {expected_length} dígitos.")
            return
        phone = self.phone.text().strip()
        if phone and (not phone.isdigit() or len(phone) != 9):
            self.status.setText("El teléfono debe contener exactamente 9 dígitos.")
            return
        if not new_email or "@" not in new_email or "." not in new_email.rsplit("@", 1)[-1]:
            self.status.setText("Ingresa un correo electrónico válido.")
            return

        token = self.user.get("access_token")
        metadata = {
            "full_name": name,
            "document_type": document_type,
            "dni": document,
            "address": self.address.text().strip(),
            "phone": phone,
        }
        try:
            self.auth.update_user(token, {"data": metadata})
        except SupabaseAuthError as error:
            self.status.setText(f"No se pudieron guardar los datos: {error}")
            return

        self.user.update(metadata)
        self.profile_updated.emit(dict(self.user))
        current_email = str(self.user.get("email") or "")
        if new_email.lower() != current_email.lower():
            try:
                self.auth.update_user(token, {"email": new_email})
            except SupabaseAuthError as error:
                self.status.setText(f"Los datos se guardaron, pero no se pudo cambiar el correo: {error}")
                return
            self.status.setText(
                f"Datos guardados. Supabase envió una solicitud de confirmación a {new_email}; "
                "el cambio de correo se aplicará cuando completes la verificación."
            )
        else:
            self.status.setText("Datos del perfil guardados correctamente.")

    def change_password(self):
        current = self.current_password.text()
        new = self.new_password.text()
        if not current:
            self.status.setText("Ingresa tu contraseña actual para verificar tu identidad.")
            return
        if len(new) < 8:
            self.status.setText("La nueva contraseña debe tener al menos 8 caracteres.")
            return
        if new != self.confirm_password.text():
            self.status.setText("La nueva contraseña y su confirmación no coinciden.")
            return

        try:
            session = self.auth.sign_in(self.user.get("email", ""), current)
            auth_user = session.get("user") or {}
            if auth_user.get("id") != self.user.get("id"):
                self.status.setText("La contraseña actual no corresponde a esta cuenta.")
                return
            token = session.get("access_token")
            self.auth.update_password(token, new)
        except SupabaseAuthError as error:
            message = str(error)
            if "invalid login credentials" in message.lower() or "invalid_credentials" in message.lower():
                self.status.setText("La contraseña actual es incorrecta.")
            else:
                self.status.setText(f"No se pudo cambiar la contraseña: {message}")
            return

        self.current_password.clear()
        self.new_password.clear()
        self.confirm_password.clear()
        self.status.setText("Contraseña actualizada correctamente.")
