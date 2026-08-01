# Prepara Martix como un ejecutable de escritorio y, opcionalmente, lo arranca
# al iniciar sesión mediante una Tarea Programada. El usuario final abre
# Martix.exe en la carpeta principal; no necesita Python, Flask ni un navegador.
#
# Ejecutar desde PowerShell (no hace falta ser administrador):
#   powershell -ExecutionPolicy Bypass -File install_windows.ps1

$ErrorActionPreference = "Stop"

$BackendDir = Split-Path -Parent $PSScriptRoot
$ProjectDir = Split-Path -Parent $BackendDir
$VenvDir = Join-Path $BackendDir ".venv"

Write-Host "==> Creando entorno virtual e instalando dependencias..."
python -m venv $VenvDir
& "$VenvDir\Scripts\pip.exe" install --quiet --upgrade pip
& "$VenvDir\Scripts\pip.exe" install --quiet -r (Join-Path $BackendDir "requirements.txt")
& "$VenvDir\Scripts\pip.exe" install --quiet -r (Join-Path $BackendDir "requirements-desktop.txt")

Write-Host "==> Construyendo Martix.exe..."
& "$VenvDir\Scripts\python.exe" (Join-Path $BackendDir "build_desktop.py")

$ExePath = Join-Path $ProjectDir "Martix.exe"
if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "No se encontró el ejecutable generado: $ExePath"
}

Write-Host "==> Registrando la tarea programada 'Martix'..."
$Action = New-ScheduledTaskAction -Execute $ExePath -WorkingDirectory (Split-Path -Parent $ExePath)
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -Hidden -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName "Martix" -Action $Action -Trigger $Trigger -Settings $Settings `
    -Description "Martix - organizador automatico de descargas" -Force | Out-Null

Start-ScheduledTask -TaskName "Martix"

Write-Host ""
Write-Host "Martix esta instalado como aplicacion de escritorio."
Write-Host "Ejecutable: $ExePath"
Write-Host "Ver la tarea:   Get-ScheduledTask -TaskName Martix"
Write-Host "Detenerla:      Stop-ScheduledTask -TaskName Martix"
