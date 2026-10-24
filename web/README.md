# Cancha Web

Interfaz web adaptable a celular, tablet y laptop. Usa Supabase Auth y tablas
Supabase con aislamiento de datos por cuenta.

## Configuración

1. En un proyecto Supabase, ejecuta el
   script `../SUPABASE_SHARED_DATA.sql` desde **SQL Editor**.
   Si ese proyecto ya tiene tablas con datos antiguos, primero hay que asignar
   esas filas a su cuenta usando el UUID correspondiente; el script se detiene
   si encuentra filas sin propietario para evitar exponerlas.
2. `config.js` ya está conectado al mismo Project URL y Publishable key usados
   por la app de escritorio. Son valores públicos para clientes; nunca uses una
   clave `service_role` aquí.
3. Sirve la carpeta `web/` desde un hosting estático con HTTPS (por ejemplo,
   GitHub Pages, Netlify o Vercel). No abras la página como `file://`.
4. En Supabase **Authentication → URL Configuration**, configura la URL publicada
   como Site URL / Redirect URL. Para restablecimiento de contraseña, permite
   también la URL de la página de recuperación.
5. La URL web debe estar autorizada en Supabase Authentication → URL
   Configuration. PostgREST autoriza el origen mediante sus respuestas CORS; si
   hay un proxy o CDN propio, permite también las peticiones al endpoint `/rest/v1`.

Para una vista local de desarrollo, usa un servidor estático desde esta carpeta,
por ejemplo `python -m http.server 8000`, y abre `http://localhost:8000`.

El registro envía un enlace/código de confirmación según la configuración de
correo de Supabase. Los datos se comparten entre navegadores que inician sesión
con la misma cuenta; el acceso queda aislado por Row Level Security.

La interfaz implementa inicio de sesión, registro, recuperación de contraseña,
productos, inventario diario, reservas, cierre de reservas, reportes básicos y
perfil. Esta versión web es una interfaz independiente. La versión de escritorio
actual aún no usa consultas autenticadas con `owner_id` en todos sus módulos, así
que no deben considerarse sincronizadas entre sí hasta adaptar y probar también el
cliente de escritorio. La configuración y publicación requieren acceso al proyecto
Supabase y al proveedor de hosting.
