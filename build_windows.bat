@echo off
REM Build de l'application bureau Windows (.exe).
REM A executer sur une machine Windows (PyInstaller ne cross-compile pas).
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements-desktop.txt
pyinstaller captureinstagram.spec --noconfirm
echo Termine. Application dans dist\CaptureINSTAGRAM\
echo Lancez CaptureINSTAGRAM.exe depuis ce dossier (il contient ses dependances).
echo Pour distribuer, zippez le dossier entier.
