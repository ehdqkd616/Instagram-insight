@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo   Instagram Analyzer - Setup
echo ============================================================
echo.

:: Find Python
set PYTHON=

where py >nul 2>&1
if not errorlevel 1 (
    set PYTHON=py
    goto :found_python
)

where python >nul 2>&1
if not errorlevel 1 (
    for /f "delims=" %%V in ('python -c "import sys; print(sys.version_info.major)"') do set PY_MAJOR=%%V
    if "!PY_MAJOR!"=="3" (
        set PYTHON=python
        goto :found_python
    )
)

where python3 >nul 2>&1
if not errorlevel 1 (
    set PYTHON=python3
    goto :found_python
)

echo [ERROR] Python 3 not found.
echo         Install Python 3.10+ from https://www.python.org
pause
exit /b 1

:found_python
for /f "delims=" %%V in ('!PYTHON! --version 2^>^&1') do set PY_VER=%%V
echo [OK] !PY_VER! (command: !PYTHON!)
echo.

echo [1/2] Installing packages ...
!PYTHON! -m pip install -q -r "%~dp0instagram_analyzer\requirements.txt"
if errorlevel 1 (
    echo [WARNING] pip install had errors. Check your connection.
    pause
)
echo       Done.
echo.

echo [2/2] Creating desktop shortcut ...
!PYTHON! "%~dp0instagram_analyzer\make_shortcut.py"
if errorlevel 1 (
    echo [ERROR] Shortcut creation failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Done! Double-click [Instagram Analyzer] on your Desktop.
echo ============================================================
pause
