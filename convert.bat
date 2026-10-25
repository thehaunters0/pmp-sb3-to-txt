@echo off
setlocal
cd /d "%~dp0"

rem Find Python (the "py" launcher first, then "python")
set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo Python was not found.
  echo Install it from https://www.python.org/downloads/
  echo and tick "Add Python to PATH" in the installer.
  echo.
  pause
  exit /b 1
)

if "%~1"=="" (
  rem Double-clicked: open the file picker
  %PY% pmp_to_txt.py
) else (
  rem Files dragged onto this file: convert each one
  for %%F in (%*) do %PY% pmp_to_txt.py "%%~F"
)

echo.
pause
