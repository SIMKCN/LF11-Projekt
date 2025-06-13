@echo off
REM Dieses Skript führt die main.py mit der eingebetteten Python-Version aus.

REM Ermittelt den Pfad zum Verzeichnis, in dem dieses Skript liegt.
SET "SCRIPT_DIR=%~dp0"

REM Definiert den Pfad zur eingebetteten Python-Anwendung.
SET "PYTHON_EXE=%SCRIPT_DIR%python_embedded\python.exe"

REM Definiert den Pfad zur Python-Hauptdatei.
SET "MAIN_PY=%SCRIPT_DIR%main.py"

REM Prüft, ob die Python.exe existiert.
if not exist "%PYTHON_EXE%" (
    echo Fehler: Die Python-Executable wurde nicht unter "%PYTHON_EXE%" gefunden.
    pause
    exit /b 1
)

REM Prüft, ob die main.py existiert.
if not exist "%MAIN_PY%" (
    echo Fehler: Die Hauptdatei main.py wurde nicht unter "%MAIN_PY%" gefunden.
    pause
    exit /b 1
)

echo Starte main.py mit der eingebetteten Python-Version...
echo.

REM Führt die main.py mit der spezifizierten Python-Version aus.
"%PYTHON_EXE%" "%MAIN_PY%"

echo.
echo Das Skript wurde beendet. Druecken Sie eine beliebige Taste, um das Fenster zu schliessen.
pause
