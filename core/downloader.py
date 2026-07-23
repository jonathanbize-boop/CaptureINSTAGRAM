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
import gallery_dl.exception
import gallery_dl.job

# Extensions considérées comme des images (les vidéos sont ignorées).
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".heic"}

# Reproduit l'ancien `--filter` : on écarte les vidéos dès le téléchargement.
_IMAGE_FILTER = "extension not in ('mp4', 'webm', 'mov', 'mkv', 'm4v')"

INSTAGRAM = "instagram"
FACEBOOK = "facebook"
AUTO = "auto"
PLATFORMS = (AUTO, INSTAGRAM, FACEBOOK)

_INSTAGRAM_RE = re.compile(r"(?:[\w-]+\.)?instagram\.com", re.IGNORECASE)
# gallery-dl accepte n'importe quel sous-domaine de facebook.com
# (www, m, web, mbasic, fr-fr…). En revanche il ignore les raccourcis
# fb.com / fb.me / fb.watch : on les réécrit ou on les refuse.
_FACEBOOK_RE = re.compile(
    r"(?:[\w-]+\.)?(?:facebook\.com|fb\.com|fb\.me|fb\.watch)", re.IGNORECASE
)
_FB_SHORT_RE = re.compile(r"^(https?://)(?:[\w-]+\.)?fb\.(?:com|me)/", re.IGNORECASE)
_FB_WATCH_RE = re.compile(r"(?:[\w-]+\.)?fb\.watch/", re.IGNORECASE)

# Instagram : lettres, chiffres, points, underscores.
_IG_USERNAME_RE = re.compile(r"^@?[A-Za-z0-9._]{1,60}$")
# Facebook : les pages utilisent aussi des tirets (« Ma-Page-123 »).
_FB_USERNAME_RE = re.compile(r"^@?[A-Za-z0-9.\-]{1,80}$")
# Profil Facebook sans nom personnalisé : uniquement un identifiant numérique.
_FB_ID_RE = re.compile(r"^\d{5,}$")

# Préfixes explicites saisis par l'utilisateur : « fb:mapage », « ig:@compte ».
_PREFIXES = {
    "fb": FACEBOOK,
    "facebook": FACEBOOK,
    "ig": INSTAGRAM,
    "insta": INSTAGRAM,
    "instagram": INSTAGRAM,
}


class DownloadError(Exception):
    """Erreur levée quand le téléchargement échoue."""


def _split_prefix(source: str) -> tuple[str | None, str]:
    """Extrait un préfixe de plateforme (« fb: », « ig: ») s'il est présent."""
    prefix, sep, rest = source.partition(":")
    if sep and rest and prefix.lower() in _PREFIXES:
        return _PREFIXES[prefix.lower()], rest.strip()
    return None, source


def _facebook_url_from_name(name: str) -> str:
    """Construit l'URL du profil/page Facebook à partir d'un nom ou d'un id."""
    name = name.lstrip("@")
    if _FB_ID_RE.match(name):
        return f"https://www.facebook.com/profile.php?id={name}"
    if _FB_USERNAME_RE.match(name):
        return f"https://www.facebook.com/{name}/"
    raise DownloadError(
        f"Nom de page Facebook non reconnu : « {name} ». "
        "Utilisez le nom visible dans l'URL de la page, son identifiant "
        "numérique, ou collez directement l'URL Facebook."
    )


def _instagram_url_from_name(name: str) -> str:
    name = name.lstrip("@")
    if _IG_USERNAME_RE.match(name):
        return f"https://www.instagram.com/{name}/"
    raise DownloadError(
        f"Nom de compte Instagram non reconnu : « {name} ». "
        "Utilisez le nom d'utilisateur (sans espace) ou collez l'URL du profil."
    )


def _normalize_url(url: str) -> str:
    """Ramène une URL déjà complète à une forme que gallery-dl sait traiter."""
    if _FB_WATCH_RE.search(url):
        raise DownloadError(
            "Les liens fb.watch pointent vers des vidéos ; cet outil ne "
            "récupère que des photos. Utilisez l'URL d'une photo, d'un album "
            "ou d'une page Facebook."
        )
    # fb.com / fb.me sont de simples raccourcis vers facebook.com, que
    # l'extracteur Facebook de gallery-dl ne reconnaît pas.
    return _FB_SHORT_RE.sub(r"\1www.facebook.com/", url)


def normalize_source(source: str, platform: str = AUTO) -> str:
    """Transforme l'entrée utilisateur en URL exploitable.

    Accepte une URL Instagram/Facebook complète, un nom d'utilisateur préfixé
    (« fb:mapage », « ig:@compte »), ou un nom nu. Pour un nom nu, `platform`
    tranche : `auto` le traite comme un compte Instagram (comportement
    historique), `facebook` comme une page Facebook.
    """
    source = source.strip()
    if not source:
        raise DownloadError("Aucune URL ou nom de compte fourni.")

    if platform not in PLATFORMS:
        raise DownloadError(f"Plateforme inconnue : {platform}.")

    if not source.startswith(("http://", "https://")):
        prefix_platform, source = _split_prefix(source)
        if prefix_platform:
            platform = prefix_platform

    if source.startswith(("http://", "https://")):
        return _normalize_url(source)
    if _INSTAGRAM_RE.search(source) or _FACEBOOK_RE.search(source):
        return _normalize_url(f"https://{source}")

    if platform == FACEBOOK:
        return _facebook_url_from_name(source)
    if platform == INSTAGRAM or _IG_USERNAME_RE.match(source):
        return _instagram_url_from_name(source)

    raise DownloadError(
        f"Entrée non reconnue : « {source} ». "
        "Fournissez une URL instagram.com / facebook.com, un nom d'utilisateur "
        "Instagram, ou préfixez par « fb: » pour une page Facebook."
    )


def detect_platform(url: str) -> str:
    if _INSTAGRAM_RE.search(url):
        return INSTAGRAM
    if _FACEBOOK_RE.search(url):
        return FACEBOOK
    raise DownloadError(
        f"URL non prise en charge : {url}. Seuls Instagram et Facebook sont supportés."
    )


class _ProgressDownloadJob(gallery_dl.job.DownloadJob):
    """DownloadJob qui signale chaque photo téléchargée via un callback.

    Reproduit le suivi temps réel qu'offrait l'ancien parsing de la sortie
    du sous-processus gallery-dl.

    Les attributs sont posés sur la classe, pas sur l'instance : quand un
    extracteur met des URLs en file d'attente (albums Facebook), gallery-dl
    crée des jobs enfants via `self.__class__(...)`, qui partagent donc le
    même callback et le même compteur — indispensable pour que la limite
    soit globale et non « par album ».
    """

    report = None    # callback(message) injecté avant run()
    counter = None   # dict partagé {"n": …} pour compter tous les jobs
    limit = 0

    def handle_url(self, url, kwdict):
        cls = type(self)
        counter = cls.counter
        if counter is not None and cls.limit and counter["n"] >= cls.limit:
            # `depth` élevé : l'arrêt remonte jusqu'au job racine au lieu de
            # se contenter d'interrompre l'album en cours.
            raise gallery_dl.exception.StopExtraction(128)

        super().handle_url(url, kwdict)

        if counter is not None:
            counter["n"] += 1
        callback = cls.report
        if callback is not None:
            callback(f"Photo {counter['n'] if counter else '?'} téléchargée")


def _configure(platform: str, dest: Path, limit: int,
               cookies_file: Path | None, facebook_albums: bool) -> None:
    """Pose la configuration gallery-dl du job à venir.

    Les clés générales sont posées à la racine `()`, exactement comme le fait
    la ligne de commande de gallery-dl (`config.set((), key, value)`), ce qui
    garantit qu'elles sont bien prises en compte par l'extracteur.
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

    if platform == FACEBOOK:
        facebook = ("extractor", FACEBOOK)
        # Évite d'ouvrir puis de jeter chaque page vidéo (l'`image-filter`
        # les écarterait de toute façon, mais après la requête).
        gallery_dl.config.set(facebook, "videos", False)
        # Sur une URL de profil, gallery-dl ne visite par défaut que l'onglet
        # « Photos ». Les pages rangent souvent leurs images dans des albums.
        gallery_dl.config.set(
            facebook, "include", "photos,albums" if facebook_albums else "photos"
        )
        # Facebook renvoie une page HTML par photo : sans pause, la rafale de
        # requêtes se fait rapidement bloquer.
        gallery_dl.config.set(facebook, "sleep-request", "0.5-1.5")


def _download_in_process(url: str, platform: str, dest: Path, limit: int,
                         cookies_file: Path | None, facebook_albums: bool,
                         report) -> int:
    """Exécute gallery-dl en processus (compatible app gelée PyInstaller)."""
    _configure(platform, dest, limit, cookies_file, facebook_albums)

    _ProgressDownloadJob.report = staticmethod(report)
    _ProgressDownloadJob.counter = {"n": 0}
    _ProgressDownloadJob.limit = limit
    exit_code = 0
    try:
        job = _ProgressDownloadJob(url)
        exit_code = job.run()
    except gallery_dl.exception.StopExtraction:
        # Limite globale atteinte : ce n'est pas une erreur.
        report(f"Limite de {limit} photo(s) atteinte.")
    finally:
        _ProgressDownloadJob.report = None
        _ProgressDownloadJob.counter = None
        _ProgressDownloadJob.limit = 0
        # On ne laisse pas la config d'un job fuiter vers le suivant.
        gallery_dl.config.clear()

    report(f"gallery-dl terminé (code {exit_code}).")
    return exit_code


def _empty_result_hint(platform: str) -> str:
    if platform == FACEBOOK:
        return (
            "Aucune photo récupérée. La page est peut-être privée ou "
            "inexistante, ses photos peuvent être rangées dans des albums "
            "(activez « inclure les albums »), ou Facebook a bloqué la requête "
            "— les profils personnels et les groupes exigent presque toujours "
            "des cookies de connexion."
        )
    return (
        "Aucune photo récupérée. Le compte est peut-être privé, inexistant, "
        "ou la plateforme a bloqué la requête (Instagram bloque souvent les "
        "requêtes sans connexion — ajoutez vos cookies pour continuer)."
    )


def download_photos(
    source: str,
    dest: Path,
    limit: int = 50,
    cookies_file: Path | None = None,
    on_progress=None,
    platform: str = AUTO,
    facebook_albums: bool = False,
) -> list[Path]:
    """Télécharge jusqu'à `limit` photos du compte donné dans `dest`.

    Retourne la liste des fichiers image téléchargés.
    Appelle `on_progress(message)` à chaque événement notable.
    """
    url = normalize_source(source, platform)
    resolved = detect_platform(url)
    dest.mkdir(parents=True, exist_ok=True)

    def report(message: str) -> None:
        if on_progress:
            on_progress(message)

    report(f"Plateforme détectée : {resolved}")
    report(f"Téléchargement depuis {url} (max {limit} fichiers)…")

    _download_in_process(url, resolved, dest, limit, cookies_file,
                         facebook_albums, report)

    files = sorted(
        p for p in dest.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )

    if not files:
        raise DownloadError(_empty_result_hint(resolved))

    report(f"{len(files)} photo(s) téléchargée(s).")
    return files
