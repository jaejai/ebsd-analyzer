@echo off
setlocal
cd /d "%~dp0"

echo.
echo  ============================================================
echo    EBSD Analyzer - installing components
echo    first run only; needs an internet connection
echo  ============================================================
echo.

set "PIXI=%~dp0.pixi-bin\pixi.exe"

if not exist "%PIXI%" (
  echo  Downloading the environment manager pixi ...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0get_pixi.ps1"
)

if not exist "%PIXI%" (
  echo.
  echo  ERROR: could not download the environment manager.
  echo  Please check your internet connection and run this again.
  echo.
  pause
  exit /b 1
)

echo.
echo  Building the analysis environment from conda-forge ...
echo  this downloads a few hundred MB the first time - please wait
echo.
"%PIXI%" install
if errorlevel 1 (
  echo.
  echo  ERROR: environment setup did not complete.
  echo  This is almost always a network issue or a corporate proxy/firewall
  echo  blocking conda-forge. Check your connection and run this again.
  echo.
  pause
  exit /b 1
)

echo.
echo  ============================================================
echo    Setup complete.  Launch the app with  launch.bat
echo  ============================================================
echo.
pause
endlocal
