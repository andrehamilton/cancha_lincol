# Configurar envio de codigos

El codigo de verificacion y el de recuperacion se envian al correo que la persona
ingresa. Para enviar mensajes, Gmail requiere que la aplicacion se autentique con
una cuenta remitente y una contrasena de aplicacion (no la contrasena normal).

En PowerShell, antes de iniciar la aplicacion, configura estas variables con una
cuenta remitente a la que tengas acceso:

```powershell
$env:CANCHA_SMTP_USER = "cuenta.remitente@gmail.com"
$env:CANCHA_SMTP_APP_PASSWORD = "clave-de-aplicacion-de-16-caracteres"
python home.py
```

La clave de aplicacion se crea en la seguridad de la cuenta Google remitente con
verificacion en dos pasos habilitada. No publiques ni compartas esa clave.
Al cerrar PowerShell, las variables de esa sesion dejan de estar configuradas.
