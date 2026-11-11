$ErrorActionPreference = "Stop"

$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$distributionPath = Join-Path $projectPath "dist\App 1.0"
$version = "1.2.0"
$outputPath = Join-Path $projectPath "dist\installer\App-1.0-Setup-$version.exe"
$iexpressPath = Join-Path $env:WINDIR "System32\iexpress.exe"
$temporaryRoot = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
$stagingPath = Join-Path $env:TEMP ("AppInstaller-" + [guid]::NewGuid().ToString('N'))

if (-not (Test-Path -LiteralPath (Join-Path $distributionPath "App 1.0.exe"))) {
    throw "Primero debe generarse dist\App 1.0 con PyInstaller."
}
if (-not (Test-Path -LiteralPath $iexpressPath)) {
    throw "No se encontró IExpress, incluido con Windows."
}

New-Item -ItemType Directory -Force -Path $stagingPath | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $outputPath) | Out-Null
$archivePath = Join-Path $stagingPath "App 1.0.zip"
$payloadPath = Join-Path $stagingPath "payload"
New-Item -ItemType Directory -Force -Path $payloadPath | Out-Null
$archiveReady = $false
for ($attempt = 1; $attempt -le 5 -and -not $archiveReady; $attempt++) {
    try {
        Start-Sleep -Seconds 2
        Copy-Item -Path (Join-Path $distributionPath "*") -Destination $payloadPath -Recurse -Force -ErrorAction Stop
        Compress-Archive -Path (Join-Path $payloadPath "*") -DestinationPath $archivePath -CompressionLevel Optimal -ErrorAction Stop
        $archiveReady = $true
    } catch {
        Remove-Item -LiteralPath $archivePath -Force -ErrorAction SilentlyContinue
        if ($attempt -eq 5) {
            throw "No se pudo preparar el paquete. Cierra App 1.0 y vuelve a ejecutar este script. Detalle: $_"
        }
        Start-Sleep -Seconds 3
    }
}

$installScript = @'
$ErrorActionPreference = "Stop"
$installDir = Join-Path $env:LOCALAPPDATA "Programs\App 1.0"
$menuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\App 1.0"
$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\App 1.0"

try {
    if (Get-Process -Name "App 1.0" -ErrorAction SilentlyContinue) {
        throw "Cierra App 1.0 antes de instalar la actualización."
    }
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
    Expand-Archive -LiteralPath (Join-Path $PSScriptRoot "App 1.0.zip") -DestinationPath $installDir -Force
    Set-Content -LiteralPath (Join-Path $installDir "version.txt") -Value $version -Encoding ASCII
    $uninstaller = Join-Path $installDir "uninstall.ps1"
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "uninstall.ps1") -Destination $uninstaller -Force

    New-Item -ItemType Directory -Force -Path $menuDir | Out-Null
    $shell = New-Object -ComObject WScript.Shell
    $appShortcut = $shell.CreateShortcut((Join-Path $menuDir "App 1.0.lnk"))
    $appShortcut.TargetPath = Join-Path $installDir "App 1.0.exe"
    $appShortcut.WorkingDirectory = $installDir
    $appShortcut.Save()
    $uninstallShortcut = $shell.CreateShortcut((Join-Path $menuDir "Desinstalar App 1.0.lnk"))
    $uninstallShortcut.TargetPath = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
    $uninstallShortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$uninstaller`""
    $uninstallShortcut.Save()
    $desktopShortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "App 1.0.lnk"))
    $desktopShortcut.TargetPath = Join-Path $installDir "App 1.0.exe"
    $desktopShortcut.WorkingDirectory = $installDir
    $desktopShortcut.Save()

    New-Item -Path $uninstallKey -Force | Out-Null
    New-ItemProperty -Path $uninstallKey -Name DisplayName -Value "App 1.0" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $uninstallKey -Name DisplayVersion -Value $version -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $uninstallKey -Name InstallLocation -Value $installDir -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $uninstallKey -Name UninstallString -Value "`"$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe`" -NoProfile -ExecutionPolicy Bypass -File `"$uninstaller`"" -PropertyType String -Force | Out-Null

    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show("App 1.0 se instalo correctamente. Encontraras los accesos en el Escritorio y el menu Inicio.", "App 1.0") | Out-Null
} catch {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show("No se pudo completar la instalación:`n$_", "Instalación de App 1.0") | Out-Null
    exit 1
}
'@
Set-Content -LiteralPath (Join-Path $stagingPath "install.ps1") -Value $installScript -Encoding UTF8

$uninstallScript = @'
$installDir = Join-Path $env:LOCALAPPDATA "Programs\App 1.0"
$menuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\App 1.0"
Remove-Item -LiteralPath (Join-Path $menuDir "App 1.0.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $menuDir "Desinstalar App 1.0.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $menuDir -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path ([Environment]::GetFolderPath("Desktop")) "App 1.0.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\App 1.0" -Recurse -Force -ErrorAction SilentlyContinue
# Se conservan las preferencias guardadas bajo HKCU:\Software\Cancha.
$command = "timeout /t 2 /nobreak >nul & rmdir /s /q `"$installDir`""
Start-Process -FilePath "$env:WINDIR\System32\cmd.exe" -ArgumentList "/c $command" -WindowStyle Hidden
'@
Set-Content -LiteralPath (Join-Path $stagingPath "uninstall.ps1") -Value $uninstallScript -Encoding UTF8

$temporaryInstaller = Join-Path $stagingPath "App-1.0-Setup-$version.exe"
$sedContent = @"
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=1
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=1
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=
DisplayLicense=
FinishMessage=
TargetName=$temporaryInstaller
FriendlyName=App 1.0 $version
AppLaunched=powershell.exe -NoProfile -ExecutionPolicy Bypass -File install.ps1
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles
[Strings]
FILE0="App 1.0.zip"
FILE1="install.ps1"
FILE2="uninstall.ps1"
[SourceFiles]
SourceFiles0=$stagingPath\
[SourceFiles0]
%FILE0%=
%FILE1%=
%FILE2%=
"@
$sedPath = Join-Path $stagingPath "App-1.0-installer.sed"
Set-Content -LiteralPath $sedPath -Value $sedContent -Encoding Default

Push-Location $env:TEMP
$installerBuilt = $false
try {
    & $iexpressPath /N /Q /M $sedPath
    $deadline = (Get-Date).AddMinutes(10)
    $previousLength = -1
    $stableReads = 0
    while ((Get-Date) -lt $deadline -and $stableReads -lt 3) {
        if (Test-Path -LiteralPath $temporaryInstaller) {
            $length = (Get-Item -LiteralPath $temporaryInstaller).Length
            if ($length -gt 0 -and $length -eq $previousLength) {
                $stableReads++
            } else {
                $stableReads = 0
                $previousLength = $length
            }
        }
        if ($stableReads -lt 3) { Start-Sleep -Seconds 2 }
    }
    if ($stableReads -lt 3) {
        throw "IExpress no terminó de crear el instalador de App 1.0."
    }
    Move-Item -LiteralPath $temporaryInstaller -Destination $outputPath -Force
    $installerBuilt = $true
} finally {
    Pop-Location
    $resolvedStage = [System.IO.Path]::GetFullPath($stagingPath)
    if ($installerBuilt -and $resolvedStage.StartsWith($temporaryRoot, [StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $resolvedStage -Recurse -Force
    } elseif (-not $installerBuilt) {
        Write-Host "Archivos para revisar el error: $resolvedStage"
    }
}
Write-Host "Instalador creado: $outputPath"
