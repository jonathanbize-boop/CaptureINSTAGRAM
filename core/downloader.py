"""Téléchargement des photos Instagram / Facebook via gallery-dl."""

import re
import subprocess
import sys
from pathlib import Path

# Extensions considérées comme des images (les vidéos sont ignorées).
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic"}

_INSTAGRAM_RE = re.compile(r"(www\.)?instagram\.com", re.IGNORECASE)
_FACEBOOK_RE = re.compile(r"(www\.|m\.)?(facebook\.com|fb\.com|fb\.watch)", re.IGNORECASE)
_USERNAME_RE = re.compile(r"^@?[A-Za-z0-9._]{1,60}$")


class DownloadError(Exception):
    """Erreur levée quand le téléchargement échoue."""


def normalize_source(source: str) -> str:
    """Transforme l'entrée utilisateur en URL exploitable.

    Accepte une URL Instagram/Facebook complète, ou un simple nom
    d'utilisateur (traité comme un profil Instagram).
    """
    source = source.strip()
    if not source:
        raise DownloadError("Aucune URL ou nom de compte fourni.")

    if source.startswith(("http://", "https://")):
        return source
    if _INSTAGRAM_RE.search(source) or _FACEBOOK_RE.search(source):
        return f"https://{source}"
    if _USERNAME_RE.match(source):
        return f"https://www.instagram.com/{source.lstrip('@')}/"

    raise DownloadError(
        f"Entrée non reconnue : « {source} ». "
        "Fournissez une URL instagram.com / facebook.com ou un nom d'utilisateur Instagram."
    )


def detect_platform(url: str) -> str:
    if _INSTAGRAM_RE.search(url):
        return "instagram"
    if _FACEBOOK_RE.search(url):
        return "facebook"
    raise DownloadError(
        f"URL non prise en charge : {url}. Seuls Instagram et Facebook sont supportés."
    )


def download_photos(
    source: str,
    dest: Path,
    limit: int = 50,
    cookies_file: Path | None = None,
    on_progress=None,
) -> list[Path]:
    """Télécharge jusqu'à `limit` photos du compte donné dans `dest`.

    Retourne la liste des fichiers image téléchargés.
    Appelle `on_progress(message)` à chaque événement notable.
    """
    url = normalize_source(source)
    platform = detect_platform(url)
    dest.mkdir(parents=True, exist_ok=True)

    def report(message: str) -> None:
        if on_progress:
            on_progress(message)

    report(f"Plateforme détectée : {platform}")
    report(f"Téléchargement depuis {url} (max {limit} fichiers)…")

    cmd = [
        sys.executable, "-m", "gallery_dl",
        "--dest", str(dest),
        "--range", f"1-{limit}",
        # Photos uniquement : on écarte les vidéos dès le téléchargement.
        "--filter", "extension not in ('mp4', 'webm', 'mov', 'mkv', 'm4v')",
        "--no-part",
    ]
    if cookies_file:
        cmd += ["--cookies", str(cookies_file)]
    cmd.append(url)

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    downloaded = 0
    output_lines: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        line = line.rstrip()
        if not line:
            continue
        output_lines.append(line)
        # gallery-dl affiche le chemin de chaque fichier téléchargé.
        if Path(line.lstrip("# ")).suffix.lower() in IMAGE_EXTENSIONS:
            downloaded += 1
            report(f"Photo {downloaded} téléchargée")
    process.wait()

    files = sorted(
        p for p in dest.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not files:
        tail = "\n".join(output_lines[-10:])
        hint = (
            "Aucune photo récupérée. Le compte est peut-être privé, inexistant, "
            "ou la plateforme exige une connexion (fournissez un fichier de cookies)."
        )
        raise DownloadError(f"{hint}\nSortie de gallery-dl :\n{tail}")

    report(f"{len(files)} photo(s) téléchargée(s).")
    return files
