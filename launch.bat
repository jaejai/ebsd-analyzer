@echo off
REM ===================================================================
REM  EBSD Analyzer - launch
REM  Runs the app inside its private pixi environment. The user never
REM  activates anything; pixi does it internally. No console stays open.
REM ===================================================================
setlocal
cd /d "%~dp0"

set "PIXI=%~dp0.pixi-bin\pixi.exe"
if not exist "%PIXI%" (
  echo  The app is not set up yet. Please run  install.bat  first.
  pause
  exit /b 1
)

REM launch the GUI without a lingering console window
start "" /b "%PIXI%" run app
endlocal
