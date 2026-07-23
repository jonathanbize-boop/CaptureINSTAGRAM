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
import webbrowser
from pathlib import Path

import webview  # pywebview

from app import app
from core import cookie_store


def _resource_dir() -> Path:
    """Répertoire racine des ressources (diffère en mode gelé PyInstaller)."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).parent


def _unique_path(path: Path) -> Path:
    """Retourne `path`, suffixé d'un numéro s'il existe déjà."""
    if not path.exists():
        return path
    counter = 1
    while True:
        candidate = path.with_name(f"{path.stem}-{counter}{path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


class Api:
    """Pont Python ↔ JavaScript exposé à la fenêtre pywebview.

    La fenêtre native n'a pas de gestionnaire de téléchargement : un lien
    `href` classique ne déclenche rien. On expose donc `save_zip`, qui ouvre
    une boîte de dialogue « Enregistrer sous » native puis copie le ZIP à
    l'emplacement choisi.
    """

    def __init__(self) -> None:
        self.port = 0

    # --- Mémorisation optionnelle des cookies -----------------------------
    # Réservé à l'app bureau : ces méthodes n'existent pas côté navigateur,
    # où le serveur peut être partagé entre plusieurs personnes.

    def cookies_status(self) -> dict:
        return cookie_store.status()

    def cookies_load(self) -> str:
        return cookie_store.load()

    def cookies_save(self, cookies_text: str) -> dict:
        cookie_store.save(cookies_text or "")
        return cookie_store.status()

    def cookies_forget(self) -> dict:
        cookie_store.clear()
        return cookie_store.status()

    def save_zip(self, job_id: str):
        """Enregistre le ZIP du job à l'emplacement choisi par l'utilisateur.

        Retourne le chemin de destination, ou None si l'utilisateur annule.
        """
        windows = webview.windows
        if not windows:
            return None
        result = windows[0].create_file_dialog(
            webview.SAVE_DIALOG, save_filename="photos-webp.zip",
            file_types=("Archive ZIP (*.zip)",),
        )
        if not result:
            return None  # dialogue annulé
        # Selon la version de pywebview : une chaîne ou une liste de chemins.
        dest = result if isinstance(result, str) else result[0]
        # Si l'utilisateur saisit un nom sans « .zip », la boîte de dialogue ne
        # complète pas toujours l'extension selon le backend : on obtient une
        # archive valide que Windows ne sait plus ouvrir. On la remet nous-mêmes.
        if not dest.lower().endswith(".zip"):
            # Le nom final n'est plus celui validé dans le dialogue : ce dernier
            # n'a donc pas pu demander confirmation d'écrasement. On ne touche
            # pas à un fichier existant.
            # Concaténation plutôt que with_suffix() : « archive.v2 » doit
            # devenir « archive.v2.zip », pas « archive.zip ».
            dest = str(_unique_path(Path(dest + ".zip")))

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

    url = f"http://127.0.0.1:{port}/"
    api = Api()
    api.port = port
    try:
        webview.create_window(
            "CaptureINSTAGRAM", url, js_api=api, width=1100, height=820,
        )
        webview.start()
    except Exception as exc:  # noqa: BLE001 — l'app doit rester utilisable
        _fallback_to_browser(url, exc)


def _fallback_to_browser(url: str, exc: Exception) -> None:
    """Ouvre l'interface dans le navigateur quand la fenêtre native échoue.

    Cas réel rencontré : les fichiers extraits d'une archive téléchargée
    héritent du « Mark of the Web », et .NET refuse alors de charger
    `Python.Runtime.dll`, dont dépend la fenêtre native. Plutôt que de
    planter sur une trace illisible, on sert l'interface dans le navigateur.
    """
    message = (
        "La fenêtre de l'application n'a pas pu s'ouvrir :\n"
        f"{type(exc).__name__} : {exc}\n\n"
        "CaptureINSTAGRAM continue de fonctionner et vient de s'ouvrir dans "
        "votre navigateur.\n\n"
        "Cause probable : les fichiers extraits d'une archive téléchargée sont "
        "marqués « provenant d'Internet » par Windows. Pour rétablir la "
        "fenêtre native, lancez « Debloquer-et-lancer.bat », ou faites un clic "
        "droit sur l'archive ZIP → Propriétés → Débloquer avant de l'extraire.\n\n"
        "Fermez cette boîte de dialogue pour quitter l'application."
    )
    webbrowser.open(url)
    if sys.platform == "win32":
        # Boîte modale : tant qu'elle est ouverte, le serveur local tourne.
        # Sans elle, l'app se terminerait aussitôt et le navigateur afficherait
        # une page morte.
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, "CaptureINSTAGRAM", 0x40)
    else:
        print(message)
        input("Appuyez sur Entrée pour quitter…")


if __name__ == "__main__":
    main()
