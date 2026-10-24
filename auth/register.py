"""Registro y confirmacion de correo con Supabase Auth."""

from PySide6 import QtCore, QtGui, QtWidgets

from .supabase_client import SupabaseAuth, SupabaseAuthError


class RegisterDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Crear cuenta | Cancha")
        self.setMinimumWidth(380)
        self.auth = SupabaseAuth()
        self.pending_email = ""
        self.pending_access_token = ""
        self.code_requested = False
        self.signup_submitted = False
        self.resend_seconds = 0
        self.resend_timer = QtCore.QTimer(self)
        self.resend_timer.setInterval(1000)
        self.resend_timer.timeout.connect(self._tick_resend_cooldown)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Crea tu cuenta para continuar"))
        self.name = QtWidgets.QLineEdit()
        self.name.setPlaceholderText("Nombre completo")
        self.email = QtWidgets.QLineEdit()
        self.email.setPlaceholderText("Correo electronico")
        self.password = QtWidgets.QLineEdit()
        self.password.setPlaceholderText("Contrasena (minimo 8 caracteres)")
        self.password.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.confirm = QtWidgets.QLineEdit()
        self.confirm.setPlaceholderText("Confirma tu contrasena")
        self.confirm.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        self.code = QtWidgets.QLineEdit()
        self.code.setPlaceholderText("Codigo de verificacion enviado por correo")
        self.code.setMaxLength(12)
        self.code.setValidator(QtGui.QRegularExpressionValidator(
            QtCore.QRegularExpression(r"[0-9]{0,12}"), self.code
        ))
        self.code.setEnabled(False)
        for field in (self.name, self.email, self.password, self.confirm, self.code):
            layout.addWidget(field)
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.send_button = QtWidgets.QPushButton("Enviar / reenviar codigo")
        self.send_button.clicked.connect(self.send_code)
        layout.addWidget(self.send_button)
        self.create_button = QtWidgets.QPushButton("Verificar correo y solicitar acceso")
        self.create_button.setEnabled(False)
        self.create_button.clicked.connect(self.create_account)
        layout.addWidget(self.create_button)

    def send_code(self):
        name, email = self.name.text().strip(), self.email.text().strip()
        password = self.password.text()
        if not name or not email or "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            self.status.setText("Ingresa tu nombre y un correo valido.")
            return
        if len(password) < 8:
            self.status.setText("La contrasena debe tener al menos 8 caracteres.")
            return
        if password != self.confirm.text():
            self.status.setText("Las contrasenas no coinciden.")
            return

        try:
            if self.code_requested or self.signup_submitted:
                self.auth.resend_signup_code(email)
            else:
                self.auth.sign_up(name, email, password)
                self.signup_submitted = True
        except SupabaseAuthError as error:
            message = str(error)
            lowered = message.lower()
            if "already registered" in lowered or "already exists" in lowered:
                self.signup_submitted = True
                try:
                    self.auth.resend_signup_code(email)
                except SupabaseAuthError as resend_error:
                    self.status.setText(self._friendly_auth_error(resend_error))
                    return
            else:
                self.status.setText(self._friendly_auth_error(error))
                return

        self.pending_email = email
        self.code_requested = True
        self.email.setReadOnly(True)
        self.code.setEnabled(True)
        self.create_button.setEnabled(True)
        self.status.setText("Enviamos un codigo de 6 digitos a tu correo. Revisa tambien spam.")
        self.code.setFocus()
        self._start_resend_cooldown()

    def _start_resend_cooldown(self):
        self.resend_seconds = 60
        self.send_button.setEnabled(False)
        self._update_resend_button()
        self.resend_timer.start()

    @staticmethod
    def _friendly_auth_error(error):
        message = str(error)
        lowered = message.lower()
        if "email address not authorized" in lowered:
            return (
                "Supabase rechazo el envio: con el SMTP de prueba solo se puede "
                "enviar a correos autorizados del equipo del proyecto. Configura "
                "SMTP propio en Authentication > Emails > SMTP Settings."
            )
        if "email rate limit exceeded" in lowered or "rate limit" in lowered:
            return "Se alcanzo el limite de envios. Espera un momento y vuelve a intentar."
        if "error sending confirmation email" in lowered:
            return (
                "Supabase no pudo enviar el correo. Revisa SMTP Settings y que "
                "la plantilla Confirm signup incluya {{ .Token }}."
            )
        return message

    def _tick_resend_cooldown(self):
        self.resend_seconds -= 1
        if self.resend_seconds <= 0:
            self.resend_timer.stop()
            self.send_button.setEnabled(True)
            self.send_button.setText("Reenviar codigo")
        else:
            self._update_resend_button()

    def _update_resend_button(self):
        self.send_button.setText(f"Reenviar codigo en {self.resend_seconds} s")

    def create_account(self):
        if not self.code.text():
            self.status.setText("Ingresa el codigo recibido por correo.")
            return
        try:
            response = self.auth.verify_signup(self.pending_email, self.code.text())
        except SupabaseAuthError as error:
            self.status.setText(str(error))
            return
        self.pending_access_token = response.get("access_token", "")
        QtWidgets.QMessageBox.information(
            self, "Solicitud enviada",
            "Correo verificado. Tu solicitud de acceso esta pendiente de aprobacion por el administrador."
        )
        self.accept()
