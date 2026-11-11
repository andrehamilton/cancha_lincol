# Crear e instalar App 1.0 en Windows

## Crear el instalador

La compilación se hace en Windows. Se necesita Python 3.10 o superior. El script usa IExpress, incluido en Windows, para empaquetar el instalador.

Desde PowerShell, en la carpeta del proyecto, ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

El instalador aparecerá en `dist\installer\App-1.0-Setup-<version>.exe`. Cambia la versión en `$version` al inicio de `package_installer.ps1` en cada actualización, por ejemplo, `1.2.1`, `1.2.2` o `1.2.3`.

## Instalar en otro equipo

Copia el instalador generado en `dist\installer` a un equipo Windows y ejecútalo. Se instala para el usuario actual en `%LOCALAPPDATA%\Programs\App 1.0` y crea accesos en el menú Inicio y el Escritorio. La desinstalación está disponible desde Windows o desde el acceso del menú Inicio.

La app requiere Internet para iniciar sesión, registrar cuentas y recuperar contraseñas mediante Supabase. Cada cuenta de Windows guarda sus productos, inventarios y reservas localmente en `%AppData%\Cancha\cancha_reservas.db`. La base no se comparte automáticamente entre dispositivos; para compartir los datos entre equipos hace falta sincronización mediante un servidor.
