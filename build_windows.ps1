$ErrorActionPreference = "Stop"

$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectPath

$pythonPath = Join-Path $projectPath ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "No se encontró .venv\Scripts\python.exe. Crea un entorno virtual de Python 3.10 o superior."
}

& $pythonPath -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "No se pudieron instalar las dependencias de empaquetado." }

& $pythonPath -m PyInstaller --noconfirm --clean Cancha.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller no pudo crear dist\Cancha." }

& (Join-Path $projectPath "package_installer.ps1")
