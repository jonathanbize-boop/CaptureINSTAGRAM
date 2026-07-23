@echo off
REM Lanceur de secours pour CaptureINSTAGRAM.
REM
REM Windows marque « provenant d'Internet » chaque fichier extrait d'une archive
REM telechargee. .NET refuse alors de charger Python.Runtime.dll, dont depend la
REM fenetre native de l'application, qui plante au demarrage.
REM
REM Ce script retire ce marquage sur les fichiers de l'application, puis la
REM lance. A n'utiliser qu'une fois : le marquage ne revient pas.
REM
REM Equivalent manuel : clic droit sur l'archive ZIP -> Proprietes -> Debloquer,
REM AVANT de l'extraire.

echo Deblocage des fichiers de l'application...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Get-ChildItem -LiteralPath '%~dp0' -Recurse -File | Unblock-File"

if errorlevel 1 (
  echo.
  echo Le deblocage a echoue. Essayez le clic droit sur le ZIP -^> Proprietes -^> Debloquer,
  echo puis extrayez a nouveau l'archive.
  pause
  exit /b 1
)

echo Lancement de CaptureINSTAGRAM...
start "" "%~dp0CaptureINSTAGRAM.exe"
