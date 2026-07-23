# captureinstagram.spec — spécification de build PyInstaller.
# Build : pyinstaller captureinstagram.spec --noconfirm
#
# gallery-dl et Flask embarquent des fichiers de données et des sous-modules
# chargés dynamiquement (les extracteurs de gallery-dl sont importés par nom).
# Il faut donc les collecter explicitement, sinon l'app gelée plantera au
# runtime avec un ModuleNotFoundError sur l'extracteur Instagram.
#
# Mode « onedir » (dossier) et non « onefile » : un exécutable unique se
# décompresse dans %TEMP% avant de s'exécuter, comportement que l'heuristique
# de Windows Defender associe aux malwares (Trojan:Win32/Sabsik.TE.A!ml, un
# faux positif classique des applications PyInstaller). Le mode dossier évite
# cette auto-extraction. Il supprime aussi l'avertissement de dépréciation
# PyInstaller sur les bundles macOS, incompatibles avec onefile.
# Pour la même raison, UPX est désactivé : la compression de binaires est un
# autre signal fort pour les antivirus.
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [("templates", "templates")]
datas += collect_data_files("gallery_dl")

hiddenimports = []
hiddenimports += collect_submodules("gallery_dl")            # extracteurs chargés dynamiquement
hiddenimports += collect_submodules("gallery_dl.extractor")

block_cipher = None

a = Analysis(
    ["desktop.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,   # les binaires vont dans COLLECT (mode dossier)
    name="CaptureINSTAGRAM",
    debug=False,
    strip=False,
    upx=False,
    console=False,          # pas de fenêtre terminal
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico",   # (Windows) fournir une icône .ico si dispo
)

# Rassemble l'exécutable et ses dépendances dans dist/CaptureINSTAGRAM/.
coll = COLLECT(
    exe, a.binaries, a.datas,
    strip=False,
    upx=False,
    name="CaptureINSTAGRAM",
)

# Sous macOS, produire un bundle .app à partir du dossier collecté :
app = BUNDLE(
    coll,
    name="CaptureINSTAGRAM.app",
    icon=None,               # "assets/icon.icns" si dispo
    bundle_identifier="com.jonathanbize.captureinstagram",
)
