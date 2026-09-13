# Visual Dynamics for Windows: a folder, then an installer around it.
#
#     powershell -ExecutionPolicy Bypass -File packaging\build_windows.ps1
#
# Needs Inno Setup (`winget install JRSoftware.InnoSetup`) for the
# installer step; without it the folder under dist\ is still a working
# application, just not something to hand to somebody.
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)

# the local venv when there is one, the ambient python otherwise —
# a CI runner installs into its own interpreter and has no .venv
$python = if ($env:PYTHON) { $env:PYTHON }
          elseif (Test-Path '.\.venv\Scripts\python.exe') { '.\.venv\Scripts\python.exe' }
          else { 'python' }
$version = & $python -c "import visualdynamics; print(visualdynamics.__version__)"

Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
& $python -m PyInstaller packaging\visualdynamics.spec --noconfirm `
  --distpath dist --workpath build

$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if ($iscc) {
  & $iscc.Source /DMyAppVersion=$version packaging\installer.iss
  Write-Host "built dist\VisualDynamics-$version-windows-x64-setup.exe"
} else {
  Write-Warning "Inno Setup not found; dist\VisualDynamics\ is the application."
}
