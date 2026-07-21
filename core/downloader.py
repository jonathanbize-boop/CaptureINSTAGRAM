"""Téléchargement des photos Instagram / Facebook via gallery-dl.

gallery-dl est appelé **en processus** (via son API Python) plutôt qu'en
sous-processus. C'est indispensable pour que l'outil fonctionne une fois
empaqueté avec PyInstaller : dans une app gelée (« frozen »), `sys.executable`
ne pointe plus vers l'interpréteur Python mais vers l'exécutable de l'app,
donc un `subprocess` du type `[sys.executable, "-m", "gallery_dl", ...]`
échouerait silencieusement.
"""

import re
from pathlib import Path

import gallery_dl.config
import gallery_dl.job

# Extensions considérées comme des images (les vidéos sont ignorées).
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic"}

# Reproduit l'ancien `--filter` : on écarte les vidéos dès le téléchargement.
_IMAGE_FILTER = "extension not in ('mp4', 'webm', 'mov', 'mkv', 'm4v')"

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


class _ProgressDownloadJob(gallery_dl.job.DownloadJob):
    """DownloadJob qui signale chaque photo téléchargée via un callback.

    Reproduit le suivi temps réel qu'offrait l'ancien parsing de la sortie
    du sous-processus gallery-dl.
    """

    report = None  # callback(message) injecté avant run()

    def handle_url(self, url, kwdict):
        super().handle_url(url, kwdict)
        callback = type(self).report
        if callback is not None:
            self._downloaded = getattr(self, "_downloaded", 0) + 1
            callback(f"Photo {self._downloaded} téléchargée")


def _download_in_process(url: str, dest: Path, limit: int,
                         cookies_file: Path | None, report) -> int:
    """Exécute gallery-dl en processus (compatible app gelée PyInstaller).

    Les clés de configuration sont posées à la racine `()`, exactement comme
    le fait la ligne de commande de gallery-dl (`config.set((), key, value)`),
    ce qui garantit qu'elles sont bien prises en compte par l'extracteur.
    """
    gallery_dl.config.clear()
    gallery_dl.config.set((), "base-directory", str(dest))
    # Photos uniquement : ignorer les vidéos.
    gallery_dl.config.set((), "image-filter", _IMAGE_FILTER)
    gallery_dl.config.set((), "image-range", f"1-{limit}")
    gallery_dl.config.set((), "part", False)
    # Sans cookies, Instagram bloque et gallery-dl réessaie longuement.
    # On limite les tentatives pour échouer vite avec un message clair.
    gallery_dl.config.set((), "retries", 1)
    if cookies_file:
        gallery_dl.config.set((), "cookies", str(cookies_file))

    _ProgressDownloadJob.report = staticmethod(report)
    try:
        job = _ProgressDownloadJob(url)
        exit_code = job.run()
    finally:
        _ProgressDownloadJob.report = None
        # On ne laisse pas la config d'un job fuiter vers le suivant.
        gallery_dl.config.clear()

    report(f"gallery-dl terminé (code {exit_code}).")
    return exit_code


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

    _download_in_process(url, dest, limit, cookies_file, report)

    files = sorted(
        p for p in dest.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not files:
        hint = (
            "Aucune photo récupérée. Le compte est peut-être privé, inexistant, "
            "ou la plateforme a bloqué la requête (Instagram bloque souvent les "
            "requêtes sans connexion — ajoutez vos cookies pour continuer)."
        )
        raise DownloadError(hint)

    report(f"{len(files)} photo(s) téléchargée(s).")
    return files
