@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "PY_VERSION=3.11.9"
set "PY_URL=https://www.python.org/ftp/python/%PY_VERSION%/python-%PY_VERSION%-amd64.exe"
set "PY_INSTALLER=%TEMP%\python-%PY_VERSION%-amd64.exe"
set "PYTHON_CMD="

echo ================================================
echo   MangoSafe - Build-Skript
echo ================================================
echo.

if not exist main.py (
    echo [Fehler] main.py wurde in diesem Ordner nicht gefunden.
    pause
    exit /b 1
)

REM --- SCHRITT 1: ECHTES PYTHON SUCHEN ---
REM 1. Versuch: python im PATH (aber prüfen ob es echt ist)
where python >nul 2>nul
if %errorlevel%==0 (
    python --version >nul 2>nul
    if !errorlevel!==0 (
        set "PYTHON_CMD=python"
        goto python_ready
    )
)

REM 2. Versuch: py launcher
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 --version >nul 2>nul
    if !errorlevel!==0 (
        set "PYTHON_CMD=py -3"
        goto python_ready
    )
)

REM 3. Versuch: Typische Installationspfade durchsuchen
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%~D\python.exe" set "PYTHON_CMD=%%~D\python.exe"
)
if defined PYTHON_CMD goto python_ready

for /d %%D in ("%ProgramFiles%\Python*") do (
    if exist "%%~D\python.exe" set "PYTHON_CMD=%%~D\python.exe"
)
if defined PYTHON_CMD goto python_ready

set "PF86=%ProgramFiles(x86)%"
if defined PF86 (
    for /d %%D in ("!PF86!\Python*") do (
        if exist "%%~D\python.exe" set "PYTHON_CMD=%%~D\python.exe"
    )
)
if defined PYTHON_CMD goto python_ready

REM --- SCHRITT 2: PYTHON AUTOMATISCH INSTALLIEREN ---
echo [Setup] Python wurde nicht gefunden (oder nur der Microsoft Store Alias).
echo [Setup] Python %PY_VERSION% wird jetzt automatisch installiert.
echo [Setup] Internetverbindung erforderlich...
echo.

where curl >nul 2>nul
if %errorlevel%==0 (
    echo [Download] Starte mit curl...
    curl -L --fail -o "%PY_INSTALLER%" "%PY_URL%"
    if !errorlevel! neq 0 goto download_failed
) else (
    echo [Download] Starte mit PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_INSTALLER%'"
    if !errorlevel! neq 0 goto download_failed
)

echo.
echo [Install] Installation laeuft... (Bitte UAC-Abfrage bestaetigen falls noetig)
start /wait "" "%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0 Include_tcltk=1 Include_doc=0 Include_dev=0 Include_pip=1 AssociateFiles=0 Shortcuts=0
if errorlevel 1 goto install_failed

echo [Install] Suche neu installiertes Python...
REM Erneute Suche nach der Installation
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
    if exist "%%~D\python.exe" set "PYTHON_CMD=%%~D\python.exe"
)
if defined PYTHON_CMD goto python_ready

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 --version >nul 2>nul
    if !errorlevel!==0 (
        set "PYTHON_CMD=py -3"
        goto python_ready
    )
)

echo [Fehler] Installation lief durch, aber Python wurde nicht gefunden.
echo Bitte starte den PC neu oder die build.bat erneut.
pause
exit /b 1

:download_failed
echo.
echo [Fehler] Download fehlgeschlagen. Internetverbindung pruefen.
pause
exit /b 1

:install_failed
echo.
echo [Fehler] Installation fehlgeschlagen.
pause
exit /b 1

REM --- SCHRITT 3: BUILD PROZESS ---
:python_ready
echo [Info] Verwende Python: %PYTHON_CMD%
"%PYTHON_CMD%" --version
echo.

echo [1/4] Pakete installieren...
"%PYTHON_CMD%" -m ensurepip --upgrade >nul 2>nul
"%PYTHON_CMD%" -m pip install --upgrade pip >nul
"%PYTHON_CMD%" -m pip install pyinstaller customtkinter pillow cryptography pywin32
if errorlevel 1 (
    echo [Fehler] Pakete konnten nicht installiert werden.
    pause
    exit /b 1
)

echo.
echo [Info] Optionale Windows-Hello-Bindungen werden versucht (Fehler hier sind unkritisch)...
"%PYTHON_CMD%" -m pip install winsdk >nul 2>nul
if errorlevel 1 echo [Hinweis] winsdk nicht installierbar - Windows Hello bleibt optional.
"%PYTHON_CMD%" -m pip install pywinrt-Windows.Security.Credentials.UI >nul 2>nul
if errorlevel 1 echo [Hinweis] pywinrt-Paket nicht verfuegbar - der winsdk-Fallback wird verwendet.

echo.
echo [2/4] Aufraeumen...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MangoSafe.spec del /q MangoSafe.spec
echo.

echo [3/4] Erstelle MangoSafe.exe...
echo.

set "ICON_ARG="
if exist mango.ico set "ICON_ARG=--icon=mango.ico"

set "ICONSDATA_ARG="
if exist ICONS set "ICONSDATA_ARG=--add-data ICONS;ICONS"

REM Nur die WinRT-Bindungen bundeln, die wirklich importierbar sind
set "HELLO_ARGS="
"%PYTHON_CMD%" -c "import winsdk" >nul 2>nul
if !errorlevel!==0 set "HELLO_ARGS=--collect-all winsdk"
"%PYTHON_CMD%" -c "import pywinrt" >nul 2>nul
if !errorlevel!==0 set "HELLO_ARGS=!HELLO_ARGS! --collect-submodules pywinrt"
"%PYTHON_CMD%" -c "import winrt" >nul 2>nul
if !errorlevel!==0 set "HELLO_ARGS=!HELLO_ARGS! --collect-submodules winrt"

"%PYTHON_CMD%" -m PyInstaller ^
    --name "MangoSafe" ^
    --onefile ^
    --windowed ^
    --noconfirm ^
    --clean ^
    --collect-all customtkinter ^
    --hidden-import "PIL._tkinter_finder" ^
    --hidden-import "win32timezone" ^
    %ICON_ARG% ^
    %ICONSDATA_ARG% ^
    %HELLO_ARGS% ^
    main.py
if errorlevel 1 (
    echo.
    echo [Fehler] Build fehlgeschlagen.
    pause
    exit /b 1
)

echo.
echo [4/4] Fertig!
echo Deine exe liegt in: dist\MangoSafe.exe
echo.
pause
exit /b 0
