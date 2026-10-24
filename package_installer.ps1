$ErrorActionPreference = "Stop"

$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$distributionPath = Join-Path $projectPath "dist\Cancha"
$version = "1.1.0"
$outputPath = Join-Path $projectPath "dist\installer\Cancha-Setup-$version.exe"
$iexpressPath = Join-Path $env:WINDIR "System32\iexpress.exe"
$temporaryRoot = [System.IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
$stagingPath = Join-Path $env:TEMP ("CanchaInstaller-" + [guid]::NewGuid().ToString('N'))

if (-not (Test-Path -LiteralPath (Join-Path $distributionPath "Cancha.exe"))) {
    throw "Primero debe generarse dist\Cancha con PyInstaller."
}
if (-not (Test-Path -LiteralPath $iexpressPath)) {
    throw "No se encontró IExpress, incluido con Windows."
}

New-Item -ItemType Directory -Force -Path $stagingPath | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $outputPath) | Out-Null
$archivePath = Join-Path $stagingPath "Cancha.zip"
Compress-Archive -Path (Join-Path $distributionPath "*") -DestinationPath $archivePath -CompressionLevel Optimal

$installScript = @'
$ErrorActionPreference = "Stop"
$installDir = Join-Path $env:LOCALAPPDATA "Programs\Cancha"
$menuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Cancha"
$uninstallKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Cancha"

try {
    if (Get-Process -Name "Cancha" -ErrorAction SilentlyContinue) {
        throw "Cierra Cancha antes de instalar la actualización."
    }
    New-Item -ItemType Directory -Force -Path $installDir | Out-Null
    Expand-Archive -LiteralPath (Join-Path $PSScriptRoot "Cancha.zip") -DestinationPath $installDir -Force
    Set-Content -LiteralPath (Join-Path $installDir "version.txt") -Value "1.1.0" -Encoding ASCII
    $uninstaller = Join-Path $installDir "uninstall.ps1"
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot "uninstall.ps1") -Destination $uninstaller -Force

    New-Item -ItemType Directory -Force -Path $menuDir | Out-Null
    $shell = New-Object -ComObject WScript.Shell
    $appShortcut = $shell.CreateShortcut((Join-Path $menuDir "Cancha.lnk"))
    $appShortcut.TargetPath = Join-Path $installDir "Cancha.exe"
    $appShortcut.WorkingDirectory = $installDir
    $appShortcut.Save()
    $uninstallShortcut = $shell.CreateShortcut((Join-Path $menuDir "Desinstalar Cancha.lnk"))
    $uninstallShortcut.TargetPath = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"
    $uninstallShortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$uninstaller`""
    $uninstallShortcut.Save()
    $desktopShortcut = $shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "Cancha.lnk"))
    $desktopShortcut.TargetPath = Join-Path $installDir "Cancha.exe"
    $desktopShortcut.WorkingDirectory = $installDir
    $desktopShortcut.Save()

    New-Item -Path $uninstallKey -Force | Out-Null
    New-ItemProperty -Path $uninstallKey -Name DisplayName -Value "Cancha" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $uninstallKey -Name DisplayVersion -Value "1.1.0" -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $uninstallKey -Name InstallLocation -Value $installDir -PropertyType String -Force | Out-Null
    New-ItemProperty -Path $uninstallKey -Name UninstallString -Value "`"$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe`" -NoProfile -ExecutionPolicy Bypass -File `"$uninstaller`"" -PropertyType String -Force | Out-Null

    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show("Cancha se instaló correctamente. Encontrarás accesos en el Escritorio y en el menú Inicio.", "Cancha") | Out-Null
} catch {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show("No se pudo completar la instalación:`n$_", "Instalación de Cancha") | Out-Null
    exit 1
}
'@
Set-Content -LiteralPath (Join-Path $stagingPath "install.ps1") -Value $installScript -Encoding UTF8

$uninstallScript = @'
$installDir = Join-Path $env:LOCALAPPDATA "Programs\Cancha"
$menuDir = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Cancha"
Remove-Item -LiteralPath (Join-Path $menuDir "Cancha.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path $menuDir "Desinstalar Cancha.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $menuDir -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath (Join-Path ([Environment]::GetFolderPath("Desktop")) "Cancha.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\Cancha" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath "HKCU:\Software\Cancha" -Recurse -Force -ErrorAction SilentlyContinue
$command = "timeout /t 2 /nobreak >nul & rmdir /s /q `"$installDir`""
Start-Process -FilePath "$env:WINDIR\System32\cmd.exe" -ArgumentList "/c $command" -WindowStyle Hidden
'@
Set-Content -LiteralPath (Join-Path $stagingPath "uninstall.ps1") -Value $uninstallScript -Encoding UTF8

$temporaryInstaller = Join-Path $stagingPath "Cancha-Setup-$version.exe"
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
FriendlyName=Cancha $version
AppLaunched=powershell.exe -NoProfile -ExecutionPolicy Bypass -File install.ps1
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles
[Strings]
FILE0="Cancha.zip"
FILE1="install.ps1"
FILE2="uninstall.ps1"
[SourceFiles]
SourceFiles0=$stagingPath\
[SourceFiles0]
%FILE0%=
%FILE1%=
%FILE2%=
"@
$sedPath = Join-Path $stagingPath "Cancha-installer.sed"
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
        throw "IExpress no terminó de crear el instalador de Cancha."
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
