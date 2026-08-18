@echo off
setlocal

echo ================================================
echo   MangoSafe - Build-Skript (.exe erstellen)
echo ================================================
echo.
echo Dieses Skript muss im selben Ordner wie main.py,
echo ui.py und vault.py liegen und ausgefuehrt werden.
echo.

if not exist main.py (
    echo [Fehler] main.py wurde in diesem Ordner nicht gefunden.
    echo Bitte build.bat in den MangoSafe-Projektordner legen und erneut starten.
    pause
    exit /b 1
)

where python >nul 2>nul
if errorlevel 1 (
    echo [Fehler] Python wurde nicht gefunden.
    echo Bitte Python 3.10 oder neuer installieren ^(python.org^) und
    echo beim Setup "Add python.exe to PATH" ankreuzen.
    pause
    exit /b 1
)

echo [1/4] Benoetigte Pakete werden installiert...
python -m pip install --upgrade pip >nul
python -m pip install pyinstaller customtkinter pillow cryptography pywin32 winsdk
if errorlevel 1 (
    echo.
    echo [Fehler] Die Pakete konnten nicht installiert werden ^(siehe oben^).
    pause
    exit /b 1
)

echo.
echo [2/4] Alte Build-Ordner werden aufgeraeumt...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist MangoSafe.spec del /q MangoSafe.spec

echo.
echo [3/4] MangoSafe.exe wird erstellt ^(das kann ein paar Minuten dauern^)...
echo.

REM --onefile     -> alles in einer einzigen .exe, keine losen Dateien drumherum
REM --windowed    -> kein schwarzes Konsolenfenster im Hintergrund
REM --collect-all -> customtkinter/winsdk brauchen ihre mitgelieferten
REM                  Daten- bzw. Binaerdateien, die PyInstaller sonst nicht
REM                  automatisch findet
REM --icon=mango.ico -> optional: eigenes Icon, falls im Ordner vorhanden
set ICON_ARG=
if exist mango.ico set ICON_ARG=--icon=mango.ico

python -m PyInstaller ^
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
    echo [Fehler] Der Build ist fehlgeschlagen - siehe Fehlermeldung oben.
    pause
    exit /b 1
)

echo.
echo [4/4] Fertig!
echo.
echo Deine fertige MangoSafe.exe liegt hier:
echo   dist\MangoSafe.exe
echo.
echo Diese eine Datei kannst du ueberall hin kopieren/verschieben und
echo direkt per Doppelklick starten - main.py/ui.py/vault.py und
echo Python selbst werden dafuer nicht mehr gebraucht.
echo.
echo Tipp: falls Windows SmartScreen beim ersten Start warnt ^(normal bei
echo selbst erstellten, unsignierten .exe-Dateien^), auf "Weitere
echo Informationen" und dann "Trotzdem ausfuehren" klicken.
echo.
pause