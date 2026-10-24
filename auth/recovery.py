"""Recuperacion de contrasena con OTP de Supabase Auth."""

from PySide6 import QtCore, QtGui, QtWidgets

from .supabase_client import SupabaseAuth, SupabaseAuthError


class RecoveryDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Recuperar contrasena | Cancha")
        self.setMinimumWidth(380)
        self.auth = SupabaseAuth()
        self.recovery_token = None
        self.resend_seconds = 0
        self.resend_timer = QtCore.QTimer(self)
        self.resend_timer.setInterval(1000)
        self.resend_timer.timeout.connect(self._tick_resend_cooldown)
        self.email = QtWidgets.QLineEdit()
        self.email.setPlaceholderText("Correo de tu cuenta")
        self.code = QtWidgets.QLineEdit()
        self.code.setPlaceholderText("Codigo de recuperacion de 6 digitos")
        self.code.setMaxLength(6)
        self.code.setValidator(QtGui.QRegularExpressionValidator(
            QtCore.QRegularExpression(r"[0-9]{0,6}"), self.code
        ))
        self.code.setEnabled(False)
        self.password = QtWidgets.QLineEdit()
        self.password.setPlaceholderText("Nueva contrasena (minimo 8 caracteres)")
        self.password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.confirm = QtWidgets.QLineEdit()
        self.confirm.setPlaceholderText("Confirma la nueva contrasena")
        self.confirm.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.status = QtWidgets.QLabel("Solicita un codigo para restablecer tu contrasena.")
        self.status.setWordWrap(True)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.email)
        self.send_button = QtWidgets.QPushButton("Solicitar codigo")
        self.send_button.clicked.connect(self.request_code)
        layout.addWidget(self.send_button)
        layout.addWidget(self.code)
        layout.addWidget(self.password)
        layout.addWidget(self.confirm)
        layout.addWidget(self.status)
        self.reset_button = QtWidgets.QPushButton("Verificar codigo y cambiar contrasena")
        self.reset_button.setEnabled(False)
        self.reset_button.clicked.connect(self.reset)
        layout.addWidget(self.reset_button)

    def request_code(self):
        email = self.email.text().strip()
        if not email:
            self.status.setText("Ingresa el correo de tu cuenta.")
            return
        try:
            self.auth.request_password_reset(email)
        except SupabaseAuthError as error:
            self.code.setEnabled(False)
            self.reset_button.setEnabled(False)
            self.status.setText(str(error))
            return
        self.code.clear()
        self.code.setEnabled(True)
        self.reset_button.setEnabled(True)
        self.status.setText("Enviamos el codigo a tu correo. Revisa tambien la carpeta de spam.")
        self.code.setFocus()
        self._start_resend_cooldown()

    def _start_resend_cooldown(self):
        self.resend_seconds = 60
        self.send_button.setEnabled(False)
        self._update_resend_button()
        self.resend_timer.start()

    def _tick_resend_cooldown(self):
        self.resend_seconds -= 1
        if self.resend_seconds <= 0:
            self.resend_timer.stop()
            self.send_button.setEnabled(True)
            self.send_button.setText("Solicitar otro codigo")
        else:
            self._update_resend_button()

    def _update_resend_button(self):
        self.send_button.setText(f"Puedes reenviar en {self.resend_seconds} s")

    def reset(self):
        email = self.email.text().strip()
        code = self.code.text().strip()
        password = self.password.text()
        if len(code) != 6:
            self.status.setText("Ingresa los 6 digitos recibidos por correo.")
            return
        if len(password) < 8:
            self.status.setText("La nueva contrasena debe tener al menos 8 caracteres.")
            return
        if password != self.confirm.text():
            self.status.setText("Las contrasenas no coinciden.")
            return
        try:
            if not self.recovery_token:
                response = self.auth.verify_recovery_code(email, code)
                self.recovery_token = response.get("access_token")
                if not self.recovery_token:
                    raise SupabaseAuthError("No se pudo validar el codigo de recuperacion.")
            self.auth.update_password(self.recovery_token, password)
        except SupabaseAuthError as error:
            self.recovery_token = None
            self.status.setText(str(error))
            return
        QtWidgets.QMessageBox.information(
            self, "Contrasena actualizada", "Ya puedes iniciar sesion con tu nueva contrasena."
        )
        self.accept()
