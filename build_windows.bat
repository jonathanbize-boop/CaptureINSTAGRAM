@echo off
REM Build de l'application bureau Windows (.exe).
REM A executer sur une machine Windows (PyInstaller ne cross-compile pas).
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements-desktop.txt
pyinstaller captureinstagram.spec --noconfirm
echo Termine. Executable dans dist\CaptureINSTAGRAM\ (ou dist\CaptureINSTAGRAM.exe)
