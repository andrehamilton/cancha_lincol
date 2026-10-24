# Cancha Web

Interfaz web adaptable a celular, tablet y laptop. Usa Supabase Auth y tablas
Supabase con aislamiento de datos por cuenta.

## Configuración

1. En el proyecto Supabase asociado a esta aplicación, ejecuta el script
   `../SUPABASE_SHARED_DATA.sql` desde **SQL Editor**. Si ya hay datos antiguos,
   asigna las filas a la cuenta correcta mediante su UUID antes de ejecutar el
   script; se detiene si encuentra filas sin propietario.
2. `config.js` contiene el Project URL y la Publishable key. Esa clave es pública
   para clientes web; nunca uses una clave `service_role` o Secret key aquí.
   Confirma que las políticas RLS del SQL se aplicaron correctamente antes de
   guardar datos reales.
3. El repositorio incluye GitHub Actions para publicar el contenido de `web/`
   en GitHub Pages.
   En GitHub abre **Settings → Pages**, selecciona **GitHub Actions** como
   origen de despliegue y confirma que Pages esté habilitado para el repositorio.
   La app quedará en `https://andrehamilton.github.io/cancha_lincol/` cuando
   termine el workflow. No abras la página como `file://`.
4. En Supabase **Authentication → URL Configuration**, configura la URL
   publicada como Site URL y agrega las URL de producción y desarrollo a
   Redirect URLs. Incluye la página publicada en las URL permitidas para los
   enlaces de recuperación.
5. En Supabase Authentication → URL Configuration agrega
   `https://andrehamilton.github.io` a Redirect URLs. PostgREST autoriza el
   origen mediante sus respuestas CORS; si hay un proxy o CDN propio, permite
   también las peticiones a `/rest/v1`.

Para una vista local de desarrollo, ejecuta `python -m http.server 8000` desde
esta carpeta y abre `http://localhost:8000`.

El registro envía un enlace/código de confirmación según la configuración de
correo de Supabase. Antes del uso real, confirma que SMTP entrega correo a las
direcciones esperadas y prueba registro, recuperación y operaciones de datos en
el dominio publicado. Los datos quedan aislados por Row Level Security y se
comparten entre navegadores que inician sesión con la misma cuenta.

La interfaz implementa inicio de sesión, registro, recuperación de contraseña,
productos, inventario diario, reservas, cierre de reservas, reportes básicos y
perfil. La aplicación de escritorio puede tener módulos que aún no consultan
datos autenticados con `owner_id`; no asumas sincronización completa con
escritorio hasta adaptar y validar ese cliente. La primera publicación requiere
habilitar GitHub Pages para el repositorio. El workflow se ejecutará después de
subir estos cambios a `main`; la URL responderá una vez que GitHub complete el
despliegue.
