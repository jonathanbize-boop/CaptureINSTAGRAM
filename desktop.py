"""Lanceur application bureau CaptureINSTAGRAM.

Démarre le serveur Flask en arrière-plan puis ouvre une fenêtre native.
Compatible avec l'empaquetage PyInstaller (mode « frozen »).

Développement (sans geler) :
    pip install -r requirements-desktop.txt
    python desktop.py
"""

import shutil
import socket
import sys
import threading
import time
import urllib.request
from pathlib import Path

import webview  # pywebview

from app import app


def _resource_dir() -> Path:
    """Répertoire racine des ressources (diffère en mode gelé PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent


class Api:
    """Pont Python ↔ JavaScript exposé à la fenêtre pywebview.

    La fenêtre native n'a pas de gestionnaire de téléchargement : un lien
    `href` classique ne déclenche rien. On expose donc `save_zip`, qui ouvre
    une boîte de dialogue « Enregistrer sous » native puis copie le ZIP à
    l'emplacement choisi.
    """

    def __init__(self) -> None:
        self.port = 0

    def save_zip(self, job_id: str):
        """Enregistre le ZIP du job à l'emplacement choisi par l'utilisateur.

        Retourne le chemin de destination, ou None si l'utilisateur annule.
        """
        windows = webview.windows
        if not windows:
            return None
        result = windows[0].create_file_dialog(
            webview.SAVE_DIALOG, save_filename="photos-webp.zip",
        )
        if not result:
            return None  # dialogue annulé
        # Selon la version de pywebview : une chaîne ou une liste de chemins.
        dest = result if isinstance(result, str) else result[0]

        url = f"http://127.0.0.1:{self.port}/api/jobs/{job_id}/download"
        # Opener sans proxy : le serveur tourne en local sur 127.0.0.1.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url) as resp, open(dest, "wb") as fh:
            shutil.copyfileobj(resp, fh)
        return dest


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

    api = Api()
    api.port = port
    webview.create_window(
        "CaptureINSTAGRAM",
        f"http://127.0.0.1:{port}/",
        js_api=api,
        width=1100,
        height=820,
    )
    webview.start()


if __name__ == "__main__":
    main()
