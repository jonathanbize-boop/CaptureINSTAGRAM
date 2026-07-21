#!/usr/bin/env bash
# Build de l'application bureau macOS (.app).
# À exécuter sur un Mac (PyInstaller ne cross-compile pas : impossible de
# produire un .app depuis Windows ou Linux).
set -e
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-desktop.txt
pyinstaller captureinstagram.spec --noconfirm
echo "Terminé. Application dans dist/CaptureINSTAGRAM.app"
