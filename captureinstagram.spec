# captureinstagram.spec — spécification de build PyInstaller.
# Build : pyinstaller captureinstagram.spec --noconfirm
#
# gallery-dl et Flask embarquent des fichiers de données et des sous-modules
# chargés dynamiquement (les extracteurs de gallery-dl sont importés par nom).
# Il faut donc les collecter explicitement, sinon l'app gelée plantera au
# runtime avec un ModuleNotFoundError sur l'extracteur Instagram.
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
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name="CaptureINSTAGRAM",
    debug=False,
    strip=False,
    upx=True,
    console=False,          # pas de fenêtre terminal
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon="assets/icon.ico",   # (Windows) fournir une icône .ico si dispo
)

# Sous macOS, produire un bundle .app :
app = BUNDLE(
    exe,
    name="CaptureINSTAGRAM.app",
    icon=None,               # "assets/icon.icns" si dispo
    bundle_identifier="com.jonathanbize.captureinstagram",
)
