"""Construit l'archive Windows de distribution à partir de dist/CaptureINSTAGRAM.

    python packaging/make_windows_zip.py

Pourquoi ne pas utiliser Compress-Archive : sous PowerShell 5.1, il écrit les
chemins avec des antislashes, ce que la spécification ZIP interdit. Selon
l'outil d'extraction, l'utilisateur obtient alors un unique fichier nommé
« CaptureINSTAGRAM\\CaptureINSTAGRAM.exe » au lieu de l'arborescence.
"""

import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP_DIR = ROOT / "dist" / "CaptureINSTAGRAM"
LAUNCHER = Path(__file__).resolve().parent / "Debloquer-et-lancer.bat"
OUTPUT = ROOT / "dist" / "CaptureINSTAGRAM-windows.zip"


def main() -> int:
    if not APP_DIR.is_dir():
        print(f"Introuvable : {APP_DIR}\nLancez d'abord le build PyInstaller.",
              file=sys.stderr)
        return 1

    # Le lanceur de secours voyage avec l'application, à côté de l'exécutable.
    shutil.copy2(LAUNCHER, APP_DIR / LAUNCHER.name)

    OUTPUT.unlink(missing_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(APP_DIR.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(APP_DIR.parent).as_posix())

    with zipfile.ZipFile(OUTPUT) as zf:
        names = zf.namelist()
        problems = []
        if any("\\" in name for name in names):
            problems.append("des chemins contiennent des antislashes")
        if "CaptureINSTAGRAM/CaptureINSTAGRAM.exe" not in names:
            problems.append("l'exécutable est absent")
        if not any(n.startswith("CaptureINSTAGRAM/_internal/") for n in names):
            problems.append("le dossier _internal est absent")
        if f"CaptureINSTAGRAM/{LAUNCHER.name}" not in names:
            problems.append("le lanceur de secours est absent")
        if (bad := zf.testzip()) is not None:
            problems.append(f"archive corrompue : {bad}")

    if problems:
        print("ÉCHEC :\n- " + "\n- ".join(problems), file=sys.stderr)
        return 1

    size = OUTPUT.stat().st_size / 1024 / 1024
    # Console Windows en cp1252 : pas de caractères hors Latin-1 ici.
    print(f"{len(names)} fichiers -> {OUTPUT} ({size:.1f} Mo)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
