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
echo Dieses Skript muss im selben Ordner wie main.py,
echo uiDS.py und vault.py liegen.
echo.

if not exist main.py (
    echo [Fehler] main.py wurde in diesem Ordner nicht gefunden.
    echo Bitte build.bat in den MangoSafe-Projektordner legen und erneut starten.
    pause
    exit /b 1
)

where python >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
    goto python_ready
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 --version >nul 2>nul
    if !errorlevel!==0 (
        set "PYTHON_CMD=py -3"
        goto python_ready
    )
)

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
    for /d %%D in ("%PF86%\Python*") do (
        if exist "%%~D\python.exe" set "PYTHON_CMD=%%~D\python.exe"
    )
)

if defined PYTHON_CMD goto python_ready

echo [Setup] Python wurde nicht gefunden.
echo [Setup] Python %PY_VERSION% wird automatisch installiert.
echo [Setup] Internetverbindung erforderlich.
echo.

where curl >nul 2>nul
if %errorlevel%==0 (
    echo [Setup] Download mit curl...
    curl -L --fail -o "%PY_INSTALLER%" "%PY_URL%"
    if !errorlevel! neq 0 goto download_failed
) else (
    echo [Setup] Download mit PowerShell...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_INSTALLER%'"
    if !errorlevel! neq 0 goto download_failed
)

echo.
echo [Setup] Python wird installiert.
echo Falls eine Windows-Abfrage erscheint, bitte bestaetigen.
echo.

start /wait "" "%PY_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0 Include_tcltk=1 Include_doc=0 Include_dev=0 Include_symbols=0 Include_pip=1 AssociateFiles=0 Shortcuts=0

if errorlevel 1 goto install_failed

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

echo [Fehler] Python wurde installiert, aber nicht gefunden.
echo Starte die build.bat bitte nochmal oder starte Windows neu.
pause
exit /b 1

:download_failed
echo.
echo [Fehler] Python konnte nicht heruntergeladen werden.
echo Bitte Internetverbindung, Firewall oder Antivirus pruefen.
pause
exit /b 1

:install_failed
echo.
echo [Fehler] Die automatische Python-Installation ist fehlgeschlagen.
echo Bitte Python manuell von python.org installieren.
pause
exit /b 1

:python_ready
echo [Info] Python gefunden:
"%PYTHON_CMD%" --version
if errorlevel 1 (
    echo [Fehler] Python konnte nicht ausgefuehrt werden.
    pause
    exit /b 1
)

echo.
echo [1/4] Benoetigte Pakete werden installiert...
"%PYTHON_CMD%" -m ensurepip --upgrade >nul 2>nul
"%PYTHON_CMD%" -m pip install --upgrade pip
"%PYTHON_CMD%" -m pip install pyinstaller customtkinter pillow cryptography pywin32 winsdk

if errorlevel 1 (
    echo.
    echo [Fehler] Die Pakete konnten nicht installiert werden.
    pause
    exit /b 1
)

echo.
echo [2/4] Alte Build-Ordner werden aufgeraeumt...

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MangoSafe.spec del /q MangoSafe.spec

echo.
echo [3/4] MangoSafe.exe wird erstellt...
echo.

set "ICON_ARG="
if exist mango.ico set "ICON_ARG=--icon=mango.ico"

"%PYTHON_CMD%" -m PyInstaller ^
--name "MangoSafe" ^
--onefile ^
--windowed ^
--noconfirm ^
--clean ^
--collect-all customtkinter ^
--collect-all winsdk ^
--hidden-import "PIL._tkinter_finder" ^
--hidden-import "win32timezone" ^
%ICON_ARG% ^
main.py

if errorlevel 1 (
    echo.
    echo [Fehler] Der Build ist fehlgeschlagen.
    pause
    exit /b 1
)

echo.
echo [4/4] Fertig.
echo.
echo Deine fertige MangoSafe.exe liegt hier:
echo   dist\MangoSafe.exe
echo.
echo Diese .exe kann ohne Python auf anderen PCs gestartet werden.
echo.
pause
exit /b 0