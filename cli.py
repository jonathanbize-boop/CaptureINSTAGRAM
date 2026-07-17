"""CLI : télécharge les photos d'un compte Instagram/Facebook et les convertit en WebP.

Exemples :
    python cli.py @natgeo --limit 20 --quality 80 --out ./export
    python cli.py https://www.facebook.com/pagepublique --max-size 1920
"""

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from core.converter import convert_directory
from core.downloader import DownloadError, download_photos


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Télécharge les photos Instagram/Facebook et les convertit en WebP."
    )
    parser.add_argument("source", help="URL Instagram/Facebook ou nom d'utilisateur Instagram")
    parser.add_argument("--limit", type=int, default=50, help="Nombre max de photos (défaut : 50)")
    parser.add_argument("--quality", type=int, default=85, help="Qualité WebP 1-100 (défaut : 85)")
    parser.add_argument("--lossless", action="store_true", help="Compression sans perte")
    parser.add_argument("--max-size", type=int, default=None,
                        help="Redimensionne si le plus grand côté dépasse N pixels")
    parser.add_argument("--cookies", type=Path, default=None,
                        help="Fichier cookies.txt (format Netscape) pour les contenus nécessitant une connexion")
    parser.add_argument("--out", type=Path, default=Path("./webp"),
                        help="Dossier de sortie (défaut : ./webp)")
    parser.add_argument("--keep-originals", action="store_true",
                        help="Conserve aussi les fichiers originaux dans <out>/originaux")
    args = parser.parse_args()

    raw_dir = args.out / "originaux" if args.keep_originals \
        else Path(tempfile.mkdtemp(prefix="captureinsta-"))
    try:
        download_photos(args.source, raw_dir, limit=args.limit,
                        cookies_file=args.cookies, on_progress=print)
        converted = convert_directory(
            raw_dir, args.out, quality=args.quality,
            lossless=args.lossless, max_size=args.max_size, on_progress=print,
        )
        print(f"\n✅ {len(converted)} image(s) WebP dans {args.out.resolve()}")
        return 0
    except DownloadError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    finally:
        if not args.keep_originals:
            shutil.rmtree(raw_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
