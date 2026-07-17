"""Conversion des images téléchargées au format WebP."""

import zipfile
from pathlib import Path

from PIL import Image

from .downloader import IMAGE_EXTENSIONS


def convert_to_webp(
    src: Path,
    out_dir: Path,
    quality: int = 85,
    lossless: bool = False,
    max_size: int | None = None,
) -> Path:
    """Convertit une image en WebP dans `out_dir` et retourne le chemin créé."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / (src.stem + ".webp")
    # Évite d'écraser deux fichiers homonymes venant de dossiers différents.
    counter = 1
    while out_path.exists():
        out_path = out_dir / f"{src.stem}-{counter}.webp"
        counter += 1

    with Image.open(src) as img:
        # Les GIF animés sont réduits à leur première image.
        if getattr(img, "is_animated", False):
            img.seek(0)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA" if "transparency" in img.info else "RGB")
        if max_size and max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.LANCZOS)
        img.save(out_path, "WEBP", quality=quality, lossless=lossless, method=6)
    return out_path


def convert_directory(
    src_dir: Path,
    out_dir: Path,
    quality: int = 85,
    lossless: bool = False,
    max_size: int | None = None,
    on_progress=None,
) -> list[Path]:
    """Convertit toutes les images de `src_dir` (récursif) en WebP."""
    sources = sorted(
        p for p in src_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )
    converted: list[Path] = []
    for index, src in enumerate(sources, start=1):
        try:
            converted.append(
                convert_to_webp(src, out_dir, quality=quality,
                                lossless=lossless, max_size=max_size)
            )
            if on_progress:
                on_progress(f"Conversion WebP {index}/{len(sources)} : {src.name}")
        except Exception as exc:  # image corrompue → on continue avec les autres
            if on_progress:
                on_progress(f"⚠️ Impossible de convertir {src.name} : {exc}")
    return converted


def zip_files(files: list[Path], zip_path: Path) -> Path:
    """Regroupe les fichiers dans une archive ZIP (sans recompression)."""
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_STORED) as archive:
        for file in files:
            archive.write(file, arcname=file.name)
    return zip_path
