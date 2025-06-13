@echo off

title Rechnungsverwaltung Starter

REM Setzt das aktuelle Verzeichnis als Basisverzeichnis und wechselt dorthin
set "BASE_DIR=%~dp0"
cd /d "%BASE_DIR%"

REM Definiert eine Log-Datei fuer Fehler und leert sie beim Start
set "LOG_FILE=%BASE_DIR%error_log.txt"
echo. > "%LOG_FILE%"

echo =================================================================
echo  Rechnungsverwaltung - Starter
echo =================================================================
echo.

REM --- Schritt 1: Pruefen, ob Python installiert ist ---
echo [1/4] Pruefe auf Python-Installation...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   FEHLER: Python scheint nicht im System-PATH gefunden zu werden.
    echo   Bitte installieren Sie Python und waehlen Sie 'Add Python to PATH' aus.
    echo.
    echo   Download: https://www.python.org/downloads/
    echo.
    exit /b 1
)
echo       ...Python gefunden.

REM --- Schritt 2: Virtuelle Umgebung erstellen (Best Practice) ---
echo.
echo [2/4] Ueberpruefe virtuelle Umgebung...
if exist "venv" goto venv_exists

REM Dieser Code wird nur ausgefuehrt, wenn "venv" NICHT existiert.
echo       ...Erstelle eine neue virtuelle Umgebung (venv). Dies kann einen Moment dauern.
python -m venv venv
if %errorlevel% neq 0 (
    echo.
    echo ============================ FEHLER ============================
    echo Die Erstellung der virtuellen Umgebung ist fehlgeschlagen.
    echo.
    echo Moegliche Gruende:
    echo   - Keine Schreibrechte im aktuellen Ordner (als Administrator ausfuehren?).
    echo   - Ein Antivirenprogramm blockiert den Prozess.
    echo ================================================================
    echo.
    exit /b 2
)
echo       ...Virtuelle Umgebung erfolgreich erstellt.
goto install_dependencies

:venv_exists
echo       ...Virtuelle Umgebung 'venv' bereits vorhanden.

:install_dependencies
REM --- Schritt 3: Abhaengigkeiten installieren (direkter Aufruf) ---
echo.
echo [3/4] Installiere/Ueberpruefe Bibliotheken (aus requirements.txt)...
"venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet > "%LOG_FILE%" 2>&1
if %errorlevel% neq 0 (
    echo.
    echo   FEHLER: Die Installation der Bibliotheken ist fehlgeschlagen.
    echo   Details finden Sie in der Log-Datei: %LOG_FILE%
    echo.
    exit /b 3
)
echo       ...Alle Bibliotheken sind auf dem neuesten Stand.

REM --- Schritt 4: Hauptprogramm starten (direkter Aufruf) ---
echo.
echo [4/4] Starte die Rechnungsverwaltungs-Anwendung...
echo.
"venv\Scripts\python.exe" main.py >> "%LOG_FILE%" 2>&1
if %errorlevel% neq 0 (
    echo =================================================================
    echo   FEHLER BEIM STARTEN DER ANWENDUNG!
    echo =================================================================
    echo.
    echo   Das Python-Programm wurde unerwartet beendet.
    echo   Eine genaue Fehlermeldung finden Sie in der Datei: %LOG_FILE%
    echo.
) else (
    echo Die Anwendung wurde erfolgreich beendet.
)

echo Druecken Sie eine beliebige Taste, um das Fenster zu schliessen...
>nul
