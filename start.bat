@echo off
PAUSE
title Rechnungsverwaltung Starter
PAUSE

REM Setzt das aktuelle Verzeichnis als Basisverzeichnis und wechselt dorthin
set "BASE_DIR=%~dp0"
PAUSE
cd /d "%BASE_DIR%"
PAUSE

REM Definiert eine Log-Datei fuer Fehler und leert sie beim Start
set "LOG_FILE=%BASE_DIR%error_log.txt"
PAUSE
echo. > "%LOG_FILE%"
PAUSE

echo =================================================================
PAUSE
echo  Rechnungsverwaltung - Starter
PAUSE
echo =================================================================
PAUSE
echo.
PAUSE

REM --- Schritt 1: Pruefen, ob Python installiert ist ---
echo [1/4] Pruefe auf Python-Installation...
PAUSE
python --version >nul 2>&1
PAUSE
if %errorlevel% neq 0 (
    echo.
    PAUSE
    echo   FEHLER: Python scheint nicht im System-PATH gefunden zu werden.
    PAUSE
    echo   Bitte installieren Sie Python und waehlen Sie 'Add Python to PATH' aus.
    PAUSE
    echo.
    PAUSE
    echo   Download: https://www.python.org/downloads/
    PAUSE
    echo.
    PAUSE
    PAUSE
    exit /b 1
)
echo       ...Python gefunden.
PAUSE

REM --- Schritt 2: Virtuelle Umgebung erstellen (Best Practice) ---
echo.
PAUSE
echo [2/4] Ueberpruefe virtuelle Umgebung...
PAUSE

REM Springe zum Label :venv_exists, wenn der Ordner bereits da ist.
if exist "venv" goto venv_exists
PAUSE

REM Dieser Code wird nur ausgefuehrt, wenn "venv" NICHT existiert.
echo       ...Erstelle eine neue virtuelle Umgebung (venv). Dies kann einen Moment dauern.
PAUSE
python -m venv venv
PAUSE
if %errorlevel% neq 0 (
    echo.
    PAUSE
    echo ============================ FEHLER ============================
    PAUSE
    echo Die Erstellung der virtuellen Umgebung ist fehlgeschlagen.
    PAUSE
    echo.
    PAUSE
    echo Moegliche Gruende:
    PAUSE
    echo   - Keine Schreibrechte im aktuellen Ordner (als Administrator ausfuehren?).
    PAUSE
    echo   - Ein Antivirenprogramm blockiert den Prozess.
    PAUSE
    echo ================================================================
    PAUSE
    echo.
    PAUSE
    PAUSE
    exit /b 2
)
echo       ...Virtuelle Umgebung erfolgreich erstellt.
PAUSE
goto install_dependencies
PAUSE

:venv_exists
echo       ...Virtuelle Umgebung 'venv' bereits vorhanden.
PAUSE

:install_dependencies
REM --- Schritt 3: Abhaengigkeiten installieren (direkter Aufruf) ---
echo.
PAUSE
echo [3/4] Installiere/Ueberpruefe Bibliotheken (aus requirements.txt)...
PAUSE
"venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet > "%LOG_FILE%" 2>&1
PAUSE
if %errorlevel% neq 0 (
    echo.
    PAUSE
    echo   FEHLER: Die Installation der Bibliotheken ist fehlgeschlagen.
    PAUSE
    echo   Details finden Sie in der Log-Datei: %LOG_FILE%
    PAUSE
    echo.
    PAUSE
    PAUSE
    exit /b 3
)
echo       ...Alle Bibliotheken sind auf dem neuesten Stand.
PAUSE

REM --- Schritt 4: Hauptprogramm starten (direkter Aufruf) ---
echo.
PAUSE
echo [4/4] Starte die Rechnungsverwaltungs-Anwendung...
PAUSE
echo.
PAUSE
"venv\Scripts\python.exe" main.py >> "%LOG_FILE%" 2>&1
PAUSE
if %errorlevel% neq 0 (
    echo =================================================================
    PAUSE
    echo   FEHLER BEIM STARTEN DER ANWENDUNG!
    PAUSE
    echo =================================================================
    PAUSE
    echo.
    PAUSE
    echo   Das Python-Programm wurde unerwartet beendet.
    PAUSE
    echo   Eine genaue Fehlermeldung finden Sie in der Datei: %LOG_FILE%
    PAUSE
    echo.
) else (
    echo Die Anwendung wurde erfolgreich beendet.
)
PAUSE

echo Druecken Sie eine beliebige Taste, um das Fenster zu schliessen...
PAUSE
PAUSE >nul
