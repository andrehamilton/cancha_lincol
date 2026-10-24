# Crear e instalar Cancha en Windows

## Crear el instalador

La compilación se hace en Windows. Se necesita Python 3.10 o superior. El script usa IExpress, incluido en Windows, para empaquetar el instalador.

Desde PowerShell, en la carpeta del proyecto, ejecuta:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

El instalador aparecerá en `dist\installer\Cancha-Setup-1.0.0.exe`.

## Instalar en otro equipo

Copia `Cancha-Setup-1.0.0.exe` a un equipo Windows y ejecútalo. Se instala para el usuario actual en `%LOCALAPPDATA%\Programs\Cancha` y crea accesos en el menú Inicio y el Escritorio. La desinstalación está disponible desde Windows o desde el acceso del menú Inicio.

La app requiere Internet para iniciar sesión, registrar cuentas y recuperar contraseñas mediante Supabase. Cada cuenta de Windows guarda sus productos, inventarios y reservas localmente en `%AppData%\Cancha\cancha_reservas.db`. La base no se comparte automáticamente entre dispositivos; para compartir los datos entre equipos hace falta sincronización mediante un servidor.
