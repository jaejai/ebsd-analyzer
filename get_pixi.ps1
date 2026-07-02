# Downloads the pixi binary (BSD-3, from prefix.dev) into .pixi-bin next to
# this script. Called by install.bat. Kept as a separate file so batch-file
# caret-escaping doesn't corrupt the PowerShell.
$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dst  = Join-Path $here '.pixi-bin'
New-Item -ItemType Directory -Force -Path $dst | Out-Null
$exe = Join-Path $dst 'pixi.exe'
if (Test-Path $exe) { Write-Host 'pixi already present'; exit 0 }

$url = 'https://github.com/prefix-dev/pixi/releases/latest/download/pixi-x86_64-pc-windows-msvc.zip'
$zip = Join-Path $env:TEMP 'pixi_dl.zip'
Write-Host 'Downloading pixi...'
Invoke-WebRequest -UseBasicParsing $url -OutFile $zip
Expand-Archive -Force $zip $dst
Remove-Item $zip -ErrorAction SilentlyContinue
if (-not (Test-Path $exe)) { throw 'pixi.exe not found after extraction' }
Write-Host 'pixi ready'
