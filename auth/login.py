"""Pantalla de acceso conectada a Supabase Auth."""

from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtUiTools import QUiLoader

from .menu import MenuWindow
from .recovery import RecoveryDialog
from .register import RegisterDialog
from .storage import resource_path
from .supabase_client import SupabaseAuth, SupabaseAuthError
from .theme import theme_palette


class LoginWindow(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.auth = SupabaseAuth()
        ui_path = resource_path("admin_login.ui")
        self.window = QUiLoader().load(str(ui_path))
        if self.window is None:
            raise RuntimeError(f"No se pudo cargar la interfaz: {ui_path}")
        self.user_input = self.window.findChild(QtWidgets.QLineEdit, "usernameInput")
        self.password_input = self.window.findChild(QtWidgets.QLineEdit, "passwordInput")
        self.status_label = self.window.findChild(QtWidgets.QLabel, "statusLabel")
        self.login_button = self.window.findChild(QtWidgets.QPushButton, "loginButton")
        self.forgot_button = self.window.findChild(QtWidgets.QPushButton, "forgotButton")
        self.window.setWindowTitle("Cancha - Iniciar sesion")
        self.window.findChild(QtWidgets.QLabel, "subtitle").setText("Ingresa con tu cuenta de Cancha")
        self.artwork = self.window.findChild(QtWidgets.QLabel, "artwork")
        artwork_path = resource_path("sONIASQ.jpg")
        self.artwork_source = QtGui.QPixmap(str(artwork_path))
        self.artwork.installEventFilter(self)
        self._fit_artwork()
        self.user_input.setPlaceholderText("   Correo electronico")
        self.forgot_button.setText("¿Olvidaste tu contrasena?")
        self.window.findChild(QtWidgets.QLabel, "footerHint").setText("¿No tienes una cuenta? Crea una ahora")
        self.register_button = QtWidgets.QPushButton("Crear cuenta")
        self.register_button.setCursor(QtCore.Qt.CursorShape.PointingHandCursor)
        self._apply_theme()
        card_layout = self.window.findChild(QtWidgets.QVBoxLayout, "cardLayout")
        card_layout.addWidget(self.register_button)
        self.login_button.clicked.connect(self.login)
        self.password_input.returnPressed.connect(self.login)
        self.forgot_button.clicked.connect(self.show_recovery)
        self.register_button.clicked.connect(self.show_register)

    def _apply_theme(self):
        palette = theme_palette()
        self.login_button.setStyleSheet(
            f"background:{palette['secondary']}; color:{palette['text']}; border:none; "
            "border-radius:8px; padding:9px; font-weight:700;"
        )
        self.register_button.setStyleSheet(
            f"color:{palette['primary']}; background:transparent; border:none; font-weight:600;"
        )

    def eventFilter(self, watched, event):
        if watched is self.artwork and event.type() == QtCore.QEvent.Type.Resize:
            self._fit_artwork()
        return super().eventFilter(watched, event)

    def _fit_artwork(self):
        if not hasattr(self, "artwork_source") or self.artwork_source.isNull():
            return
        size = self.artwork.size()
        if size.width() < 2 or size.height() < 2:
            return
        scaled = self.artwork_source.scaled(
            size, QtCore.Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        x = max(0, (scaled.width() - size.width()) // 2)
        y = max(0, (scaled.height() - size.height()) // 2)
        cropped = scaled.copy(x, y, size.width(), size.height())
        rounded = QtGui.QPixmap(size)
        rounded.fill(QtCore.Qt.GlobalColor.transparent)
        painter = QtGui.QPainter(rounded)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QtGui.QPainter.RenderHint.SmoothPixmapTransform)
        path = QtGui.QPainterPath()
        path.addRoundedRect(QtCore.QRectF(0, 0, size.width(), size.height()), 12, 12)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, cropped)

        # Suaviza el borde con una transición corta y transparente hacia la tarjeta.
        painter.setClipping(False)
        edge = 5
        for inset in range(edge):
            alpha = int(30 * (edge - inset) / edge)
            pen = QtGui.QPen(QtGui.QColor(245, 244, 246, alpha), 1)
            painter.setPen(pen)
            painter.setBrush(QtCore.Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(
                QtCore.QRectF(inset + 0.5, inset + 0.5,
                              size.width() - 1 - 2 * inset, size.height() - 1 - 2 * inset),
                max(2, 12 - inset), max(2, 12 - inset),
            )
        painter.end()
        self.artwork.setPixmap(rounded)
        self.artwork.setStyleSheet("border: none; background: transparent;")

    @QtCore.Slot()
    def login(self):
        email, password = self.user_input.text().strip(), self.password_input.text()
        if not email or not password:
            self.status_label.setText("Ingresa tu correo y contrasena para continuar.")
            return
        try:
            response = self.auth.sign_in(email, password)
        except SupabaseAuthError as error:
            message = str(error)
            if "email not confirmed" in message.lower():
                self.status_label.setText("Primero verifica tu correo desde Crear cuenta.")
            else:
                self.status_label.setText(message)
            return

        auth_user = response.get("user") or {}
        access_token = response.get("access_token")
        metadata = auth_user.get("user_metadata") or {}
        user = {
            "id": auth_user.get("id"),
            "email": auth_user.get("email", email),
            "full_name": metadata.get("full_name") or email,
            "document_type": metadata.get("document_type", "DNI"),
            "dni": metadata.get("dni", ""),
            "address": metadata.get("address", ""),
            "phone": metadata.get("phone", ""),
            "created_at": auth_user.get("created_at", ""),
            "access_token": access_token,
            "refresh_token": response.get("refresh_token"),
        }
        try:
            self.menu = MenuWindow(user, self.auth)
            self.menu.logout_button.clicked.connect(lambda: self._sign_out(access_token))
            self.menu.show()
            self.window.hide()
            self.password_input.clear()
        except Exception as error:
            # Windowed PyInstaller builds have no console, so surface startup
            # errors in the login screen instead of silently losing the password.
            self.status_label.setText(f"No se pudo abrir el menú: {error}")

    def _sign_out(self, access_token):
        if access_token:
            try:
                self.auth.sign_out(access_token)
            except SupabaseAuthError:
                pass
        self.user_input.clear()
        self._apply_theme()
        self.password_input.clear()
        self.status_label.clear()
        self.menu.close()
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    @QtCore.Slot()
    def show_register(self):
        dialog = RegisterDialog(self.window)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.user_input.setText(dialog.email.text().strip())
            self.status_label.setText("Correo verificado. Ya puedes iniciar sesion.")

    @QtCore.Slot()
    def show_recovery(self):
        dialog = RecoveryDialog(self.window)
        dialog.exec()
