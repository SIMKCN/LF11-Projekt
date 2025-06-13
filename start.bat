@echo off
title Rechnungsverwaltung Starter

set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"
set "LOG_FILE=%BASE_DIR%error_log.txt"
echo. > "%LOG_FILE%"

echo =================================================================
echo  Rechnungsverwaltung - Starter
echo =================================================================
echo.

REM --- Schritt 1: Python Installation prüfen ---
echo [1/4] Prüfe auf Python-Installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   FEHLER: Python scheint nicht im System-PATH gefunden zu werden.
    echo   Bitte installieren Sie Python und wählen Sie 'Add Python to PATH' aus.
    echo.
    echo   Download: https://www.python.org/downloads/
    echo.
    exit /b 1
)
echo       ...Python gefunden.

REM --- Schritt 2: Virtuelle Umgebung erstellen/überprüfen ---
echo.
echo [2/4] Überprüfe virtuelle Umgebung...
if exist "venv\Scripts\python.exe" goto venv_exists

echo       ...Erstelle neue virtuelle Umgebung (venv)...
python -m venv venv
if %errorlevel% neq 0 (
    echo.
    echo ============================ FEHLER ============================
    echo Die Erstellung der virtuellen Umgebung ist fehlgeschlagen.
    echo.
    echo Mögliche Gründe:
    echo   - Keine Schreibrechte im aktuellen Ordner
    echo   - Antivirenprogramm blockiert den Prozess
    echo   - Python-Installation beschädigt
    echo ================================================================
    echo.
    exit /b 2
)

REM Warte auf Existenz der Python-Executable
echo       ...Warte auf Fertigstellung...
set "VENV_READY=0"
for /l %%i in (1,1,30) do (
    if exist "venv\Scripts\python.exe" (
        set "VENV_READY=1"
        goto venv_created
    )
    timeout /t 1 /nobreak >nul
)
:venv_created

if %VENV_READY% equ 0 (
    echo.
    echo ============================ FEHLER ============================
    echo Virtuelle Umgebung wurde nicht vollständig erstellt.
    echo Bitte überprüfen Sie den venv-Ordner manuell.
    echo ================================================================
    echo.
    exit /b 4
)
echo       ...Virtuelle Umgebung erfolgreich erstellt.
goto install_dependencies

:venv_exists
echo       ...Virtuelle Umgebung 'venv' bereits vorhanden.

:install_dependencies
REM --- Schritt 3: Abhängigkeiten installieren ---
echo.
echo [3/4] Installiere/Überprüfe Bibliotheken...
"venv\Scripts\python.exe" -m pip install --upgrade pip --quiet >nul 2>&1
"venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet > "%LOG_FILE%" 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   FEHLER: Die Installation der Bibliotheken ist fehlgeschlagen.
    echo   Details finden Sie in der Log-Datei: %LOG_FILE%
    echo.
    exit /b 3
)
echo       ...Alle Bibliotheken sind auf dem neuesten Stand.

REM --- Schritt 4: Hauptprogramm starten ---
echo.
echo [4/4] Starte die Rechnungsverwaltungs-Anwendung...
echo.
start "" "%BASE_DIR%venv\Scripts\python.exe" "%BASE_DIR%main.py"

echo Die Anwendung wurde gestartet. Sie können dieses Fenster schließen.
timeout /t 5 >nul
