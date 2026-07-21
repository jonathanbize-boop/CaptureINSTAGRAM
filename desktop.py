"""Lanceur application bureau CaptureINSTAGRAM.

Démarre le serveur Flask en arrière-plan puis ouvre une fenêtre native.
Compatible avec l'empaquetage PyInstaller (mode « frozen »).

Développement (sans geler) :
    pip install -r requirements-desktop.txt
    python desktop.py
"""

import socket
import sys
import threading
import time
from pathlib import Path

import webview  # pywebview

from app import app


def _resource_dir() -> Path:
    """Répertoire racine des ressources (diffère en mode gelé PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _wait_until_up(port: int, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            return
        except OSError:
            time.sleep(0.1)


def main() -> None:
    port = _free_port()

    def _serve():
        app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)

    threading.Thread(target=_serve, daemon=True).start()
    _wait_until_up(port)

    webview.create_window(
        "CaptureINSTAGRAM",
        f"http://127.0.0.1:{port}/",
        width=1100,
        height=820,
    )
    webview.start()


if __name__ == "__main__":
    main()
