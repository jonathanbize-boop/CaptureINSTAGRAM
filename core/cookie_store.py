"""Mémorisation optionnelle des cookies, pour l'application bureau uniquement.

Les cookies d'une session Instagram/Facebook valent un mot de passe : les
conserver sur le disque est un compromis, activé explicitement par
l'utilisateur. On le rend le moins risqué possible :

- Sous Windows, le contenu est chiffré par **DPAPI** (`CryptProtectData`),
  qui lie la clé au compte Windows courant : le fichier copié ailleurs, ou
  lu par un autre compte de la machine, est inexploitable. Aucune
  dépendance : l'API système est appelée via `ctypes`.
- Ailleurs (macOS, Linux), le fichier est écrit en clair mais restreint au
  seul propriétaire (mode 600), faute d'équivalent sans dépendance.

Ce module ne doit **jamais** être utilisé par le serveur web partagé : y
persister les cookies d'un visiteur les exposerait à tous les autres.
"""

import os
import sys
from pathlib import Path

APP_NAME = "CaptureINSTAGRAM"
_FILENAME = "cookies.bin"
# Marqueur de description DPAPI, visible dans les outils système.
_DESCRIPTION = "CaptureINSTAGRAM cookies"


def store_dir() -> Path:
    """Dossier de configuration de l'app, selon le système."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config"
    return Path(base) / APP_NAME


def store_path() -> Path:
    return store_dir() / _FILENAME


# --------------------------------------------------------------------------
# Chiffrement DPAPI (Windows uniquement)
# --------------------------------------------------------------------------

def _dpapi_available() -> bool:
    return sys.platform == "win32"


def _dpapi(func_name: str, data: bytes) -> bytes:
    """Appelle CryptProtectData / CryptUnprotectData sur `data`."""
    import ctypes
    from ctypes import wintypes

    class Blob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32
    func = getattr(crypt32, func_name)
    func.restype = wintypes.BOOL

    buffer_in = ctypes.create_string_buffer(data, len(data))
    blob_in = Blob(len(data), ctypes.cast(buffer_in, ctypes.POINTER(ctypes.c_char)))
    blob_out = Blob()

    description = ctypes.c_wchar_p(_DESCRIPTION) if func_name.endswith("ProtectData") \
        else None
    ok = func(ctypes.byref(blob_in), description, None, None, None, 0,
              ctypes.byref(blob_out))
    if not ok:
        raise OSError(f"{func_name} a échoué "
                      f"(code {ctypes.windll.kernel32.GetLastError()})")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def _encrypt(text: str) -> bytes:
    raw = text.encode("utf-8")
    return _dpapi("CryptProtectData", raw) if _dpapi_available() else raw


def _decrypt(blob: bytes) -> str:
    raw = _dpapi("CryptUnprotectData", blob) if _dpapi_available() else blob
    return raw.decode("utf-8")


# --------------------------------------------------------------------------
# API publique
# --------------------------------------------------------------------------

def save(cookies_text: str) -> Path:
    """Mémorise les cookies. Un texte vide efface la sauvegarde."""
    if not cookies_text.strip():
        clear()
        return store_path()

    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Écriture puis remplacement atomique : une interruption ne laisse jamais
    # un fichier tronqué que l'on croirait valide.
    tmp = path.with_suffix(".tmp")
    tmp.write_bytes(_encrypt(cookies_text))
    if os.name == "posix":
        os.chmod(tmp, 0o600)
    os.replace(tmp, path)
    return path


def load() -> str:
    """Retourne les cookies mémorisés, ou une chaîne vide s'il n'y en a pas.

    Un fichier illisible (compte Windows différent, copie depuis une autre
    machine, corruption) est traité comme une absence : mieux vaut redemander
    les cookies que planter au démarrage.
    """
    path = store_path()
    if not path.exists():
        return ""
    try:
        return _decrypt(path.read_bytes())
    except Exception:  # noqa: BLE001 — jamais bloquer l'app sur un cache abîmé
        return ""


def clear() -> bool:
    """Supprime les cookies mémorisés. Retourne True s'il y avait un fichier."""
    path = store_path()
    existed = path.exists()
    path.unlink(missing_ok=True)
    return existed


def status() -> dict:
    """Résumé affichable dans l'interface (sans jamais exposer le contenu)."""
    path = store_path()
    return {
        "saved": path.exists(),
        "path": str(path),
        "encrypted": _dpapi_available(),
    }
