# Supabase Auth para Cancha

## Datos compartidos entre dispositivos

La app guarda productos, inventario y reservas en Supabase. Los dispositivos
comparten la informacion cuando inician sesion con la misma cuenta. Cada cuenta
mantiene un espacio de datos privado; crear varias cuentas no las agrupa en una
misma empresa.

Antes de usar la version con datos compartidos, abre **SQL Editor** en el
proyecto Supabase configurado en la app, pega y ejecuta el contenido de
`SUPABASE_SHARED_DATA.sql`. El script crea las tablas y activa politicas RLS
para que cada cuenta solo consulte sus propios registros. La instalacion requiere
conexion a Internet para leer y modificar esos datos.

Los registros que ya estan en `cancha_reservas.db` no se copian solos a Supabase.
Conserva una copia de ese archivo antes de migrar. Los datos antiguos deben
importarse a la cuenta que sera propietaria antes de usar otros equipos.

La app usa Supabase Auth con la Project URL y la Publishable key. No agregar una
Secret key ni una `service_role` key al cliente de escritorio.

## Plantillas de correo OTP

En Supabase abre **Authentication → Emails → Templates**. En cada plantilla
conserva su asunto y agrega al cuerpo una instruccion y el token:

- **Confirm signup**: agrega `Tu codigo de verificacion es: {{ .Token }}` y pide
  ingresar el token completo en la app (no asumas que tiene seis digitos).
- **Reset password**: agrega `Tu codigo para restablecer la contrasena es: {{ .Token }}`.

Guarda cada plantilla y confirma que **Confirm email** este activado en
**Authentication → Sign In / Providers → Email**.

La pestaña SMTP debe estar activada y mostrar el mensaje de guardado exitoso.
El servidor SMTP predeterminado de Supabase es de prueba: limita el volumen y
solo entrega a direcciones autorizadas para el equipo de la organizacion. Para
enviar codigos a cualquier usuario, configura SMTP propio en **Authentication
-> Emails -> SMTP Settings**. En Gmail se necesita una contrasena de aplicacion,
no la contrasena normal. Comprueba host, puerto, cifrado, usuario y remitente, y
guarda los cambios.

En el formulario de registro, **Enviar / reenviar codigo** crea una cuenta nueva
o reenvia el codigo de una cuenta pendiente. Si la cuenta ya existe pero no esta
confirmada, se puede volver a solicitar el codigo desde ese mismo formulario.
Espera al menos 60 segundos entre reenvios. La URL de sitio y las URL de
redireccion no controlan la entrega del OTP en esta app de escritorio.

## Aprobacion administrativa de nuevas cuentas

La verificacion del correo ocurre al registrarse mediante el OTP de Supabase.
Una vez confirmado, el usuario puede iniciar sesion normalmente; este flujo no
exige aprobacion administrativa.

Si en el futuro se requiere aprobacion administrativa para crear cuentas, debe
implementarse en un backend confiable que compruebe el rol del administrador.
Nunca incluyas una Secret key o `service_role` key en la aplicacion de escritorio.

## Ejecucion

Instala PySide6 en el entorno Python del proyecto y ejecuta `python home.py`.
La autenticacion ya no depende de `cancha_users.db`; las cuentas locales antiguas
no se migran automaticamente y deben volver a registrarse en Supabase.
