# CaptureINSTAGRAM

Outil pour designers : télécharge les photos d'un compte **Instagram** ou **Facebook** et les convertit automatiquement en **WebP**, prêtes à intégrer sur le web.

- 📥 Téléchargement des photos d'un profil, d'une page ou d'un post (moteur [gallery-dl](https://github.com/mikf/gallery-dl))
- 🔄 Conversion WebP avec qualité réglable, mode sans perte et redimensionnement optionnel
- 🖥️ Interface web avec suivi en temps réel et export ZIP
- ⌨️ CLI pour l'automatisation

## 🖥️ Application bureau (Windows & macOS) — recommandé

> **Pourquoi ?** Instagram bloque quasi systématiquement les IP de datacenters (erreurs `403 Forbidden` puis `NotFoundError`). Un hébergement cloud (Render, VPS…) échoue donc la plupart du temps. L'**application bureau** tourne en local sur votre machine et utilise votre **connexion internet résidentielle**, beaucoup moins bloquée. Aucune installation de Python côté utilisateur : un double-clic suffit.

L'application enveloppe exactement le même moteur (Flask + gallery-dl + Pillow) dans une fenêtre native (via [pywebview](https://pywebview.flowrl.com/)), empaquetée avec [PyInstaller](https://pyinstaller.org/).

### Tester en développement (sans empaqueter)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements-desktop.txt
python desktop.py                # ouvre une fenêtre native
```

### Construire l'exécutable

PyInstaller **ne fait pas de cross-compilation** : construisez le `.exe` sur une machine **Windows** et le `.app` sur un **Mac**.

- **Windows** : double-cliquez sur `build_windows.bat` (ou lancez-le dans un terminal). L'application est produite dans `dist\CaptureINSTAGRAM\` — lancez `CaptureINSTAGRAM.exe` **depuis ce dossier**, qui contient aussi ses dépendances. Pour la distribuer, zippez le dossier entier.
- **macOS** : `./build_macos.sh`. L'application est produite dans `dist/CaptureINSTAGRAM.app`.

Le fichier `captureinstagram.spec` collecte automatiquement les templates Flask et les extracteurs de gallery-dl (chargés dynamiquement). Testez toujours l'app **gelée** avec un vrai téléchargement avant de la distribuer.

### ⚠️ Antivirus : pourquoi le build est en mode dossier

Windows Defender signale fréquemment les applications PyInstaller en **faux positif**, typiquement `Trojan:Win32/Sabsik.TE.A!ml` — le suffixe `!ml` indique un verdict heuristique, pas une signature de malware connu.

La cause principale est le mode « fichier unique » (*onefile*) : l'exécutable se décompresse dans `%TEMP%` avant de s'exécuter, exactement le comportement que cherche l'heuristique. Le projet est donc construit en **mode dossier** (*onedir*), et **sans UPX**, la compression de binaires étant un autre signal fort pour les antivirus.

Cela réduit nettement les faux positifs sans les éliminer avec certitude. Si un blocage persiste sur un binaire que vous avez vous-même construit ou publié :

1. Signalez-le comme faux positif à Microsoft : <https://www.microsoft.com/en-us/wdsi/filesubmission> (gratuit, correction typique en 24-72 h, valable pour tous vos utilisateurs). L'empreinte changeant à chaque build, l'opération est à refaire à chaque version publiée.
2. À terme, seule la **signature de code** (certificat OV ou EV, payant) règle durablement le problème, et supprime au passage l'avertissement SmartScreen.

Un détail utile au diagnostic : Defender est bien plus strict sur les fichiers **téléchargés depuis internet** que sur ceux construits localement. Un binaire qui passe sur votre machine peut être bloqué chez celui qui le télécharge.

### Distribution

- **macOS** : Gatekeeper bloque une app non signée (« développeur non identifié »). Usage perso : clic droit → **Ouvrir**. Distribution propre : compte Apple Developer (99 $/an), `codesign` + notarisation `notarytool`, puis `.dmg`.
- **Windows** : SmartScreen affiche un avertissement pour un `.exe` non signé. Usage interne : **Informations complémentaires** → **Exécuter quand même**. Un certificat de signature de code (payant) supprime l'avertissement.
- Partage interne simple : zippez le dossier `dist/` et documentez la procédure de contournement.

### Cookies (souvent nécessaires même en local)

Certains comptes ou volumes déclenchent la demande de connexion d'Instagram. L'interface possède déjà un champ **Cookies** :

1. Installez l'extension **« Get cookies.txt LOCALLY »** (Chrome/Firefox).
2. Connectez-vous à instagram.com, exportez les cookies au **format Netscape**.
3. Collez leur contenu dans la section « Cookies » de l'application.

Les cookies sont supprimés du disque après chaque job (déjà géré par le code). Sans cookies, l'app échoue **rapidement** avec un message clair invitant à les ajouter.

> Instagram tolère un certain volume de requêtes anonymes par adresse IP, puis renvoie `401` et exige une session. Le seuil est atteint sans prévenir : un compte qui fonctionnait hier sans cookies peut les réclamer aujourd'hui. Facebook est plus permissif sur les pages publiques.

#### Se souvenir des cookies (application bureau uniquement)

Recoller ses cookies à chaque lancement est fastidieux. L'app bureau propose donc une case **« Se souvenir de mes cookies sur cet ordinateur »**, sous la section Cookies.

**Ce que cela implique.** Un cookie de session vaut un mot de passe : qui l'obtient accède à votre compte sans avoir à s'authentifier. Le stockage est donc limité au strict nécessaire :

| | |
|---|---|
| Windows | Chiffré par **DPAPI**, lié à votre compte Windows. Le fichier copié sur une autre machine, ou lu par un autre compte, est inexploitable. |
| macOS / Linux | Fichier en clair, restreint au propriétaire (mode 600) — pas d'équivalent DPAPI sans dépendance supplémentaire. |
| Emplacement | `%LOCALAPPDATA%\CaptureINSTAGRAM\cookies.bin` (Windows), `~/Library/Application Support/CaptureINSTAGRAM/` (macOS) |
| Effacement | Bouton **« Oublier les cookies enregistrés »**, ou simplement décocher la case avant de lancer un téléchargement. |

L'option n'existe **pas** dans la version web : sur une instance partagée, conserver les cookies d'un visiteur les exposerait aux autres. Le comportement du serveur est inchangé — les cookies transmis à un job sont toujours effacés dès qu'il se termine.

## 🌐 Mettre l'outil en ligne pour toute l'équipe

L'objectif : héberger l'application **une seule fois**, puis chaque membre de l'équipe l'utilise depuis son navigateur via une simple URL — aucun Python, aucune installation côté utilisateur.

### Option A — Render (gratuit, sans serveur à gérer)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/jonathanbize-boop/CaptureINSTAGRAM)

1. Cliquez sur le bouton ci-dessus (ou créez un « Web Service » sur [render.com](https://render.com) pointant vers ce dépôt — le fichier `render.yaml` configure tout automatiquement).
2. Renseignez la variable `ACCESS_CODE` avec un code de votre choix : c'est le code que votre équipe saisira pour utiliser l'outil (laissez vide pour un accès libre, déconseillé sur une URL publique).
3. Render vous donne une URL du type `https://captureinstagram.onrender.com` → partagez-la à l'équipe, c'est tout.

> Sur le plan gratuit, le service s'endort après 15 min d'inactivité : le premier chargement peut prendre ~30 s. Passez au plan payant (7 $/mois) pour l'éviter. Railway, Fly.io ou Koyeb fonctionnent de la même façon avec le `Dockerfile` fourni.

### Option B — Serveur de l'entreprise / VPS (Docker)

```bash
git clone https://github.com/jonathanbize-boop/CaptureINSTAGRAM.git
cd CaptureINSTAGRAM
ACCESS_CODE=motdepasse-equipe docker compose up -d
```

L'outil est disponible sur `http://<ip-du-serveur>:8000`. Mettez un reverse proxy (Caddy, nginx) devant pour avoir HTTPS et un nom de domaine.

### ⚠️ Important pour un hébergement cloud

Instagram et Facebook bloquent quasi systématiquement les IP de datacenters en accès anonyme. En pratique, **chaque utilisateur devra coller ses cookies** (section « Cookies » de l'interface, voir plus bas) pour que les téléchargements aboutissent. Les cookies ne sont jamais conservés après le traitement.

## Installation locale (développement)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

Python 3.10 ou plus récent est requis.

## Interface web

```bash
python app.py
```

Ouvrez ensuite <http://localhost:5000> :

1. Choisissez la plateforme (la détection automatique suffit dès que vous collez une URL).
2. Collez l'URL du compte (`https://www.instagram.com/nomducompte/`, `https://www.facebook.com/nomdelapage`) ou tapez simplement `@nomducompte` (Instagram) / `fb:nomdelapage` (Facebook).
3. Réglez le nombre de photos, la qualité WebP (85 par défaut) et éventuellement une taille max en pixels.
4. Lancez, suivez la progression, puis téléchargez le ZIP contenant les WebP.

## 📘 Sources Facebook acceptées

| Ce que vous collez | Résultat |
|---|---|
| `https://www.facebook.com/mapage` | Onglet « Photos » de la page |
| `https://www.facebook.com/mapage/photos` | Idem, explicitement |
| `https://www.facebook.com/media/set/?set=a.123…` | Un album précis |
| `https://www.facebook.com/mapage/posts/…` | Les photos d'une publication |
| `https://www.facebook.com/photo/?fbid=…` | Une photo et son album |
| `https://www.facebook.com/groups/…/posts/…` | Les photos d'un post de groupe |
| `https://www.facebook.com/profile.php?id=1000…` | Profil sans nom personnalisé |
| `fb:mapage`, `facebook:Ma-Page-123` | Page à partir de son nom seul |

Les raccourcis `fb.com` / `fb.me` sont réécrits automatiquement. Les liens `fb.watch` sont refusés : ils pointent vers des vidéos, alors que l'outil ne récupère que des photos.

**Albums.** Sur une URL de page, seul l'onglet « Photos » est parcouru par défaut. Beaucoup de pages rangent leurs images dans des albums : cochez **« Parcourir aussi les albums photos »** (ou `--facebook-albums` en CLI) pour les inclure. La limite de photos reste globale, tous albums confondus.

**Cookies.** Les pages publiques fonctionnent souvent sans connexion. Les profils personnels, les groupes et les contenus restreints exigent vos cookies (voir plus bas). Les vidéos sont ignorées sans même être ouvertes, et une courte pause est appliquée entre les requêtes Facebook pour éviter les blocages — un lot de photos Facebook est donc plus lent qu'Instagram.

## Ligne de commande

```bash
python cli.py @natgeo --limit 20 --quality 80 --out ./export
python cli.py https://www.facebook.com/pagepublique --max-size 1920
python cli.py mapage --platform facebook --facebook-albums
python cli.py @moncompte --cookies cookies.txt --keep-originals
```

| Option | Description |
|---|---|
| `--platform {auto,instagram,facebook}` | Plateforme visée quand la source est un simple nom (défaut : `auto` = Instagram). Sans effet sur une URL. |
| `--facebook-albums` | Sur une page Facebook, parcourt aussi les albums photos |
| `--limit N` | Nombre max de photos (défaut : 50) |
| `--quality N` | Qualité WebP 1-100 (défaut : 85) |
| `--lossless` | Compression sans perte |
| `--max-size N` | Redimensionne si le plus grand côté dépasse N px |
| `--cookies FICHIER` | Cookies (format Netscape) pour les contenus nécessitant une connexion |
| `--out DOSSIER` | Dossier de sortie (défaut : `./webp`) |
| `--keep-originals` | Conserve aussi les fichiers originaux |

## Connexion requise (cookies)

Instagram et Facebook limitent fortement l'accès anonyme : pour de nombreux comptes, un **fichier de cookies** de votre propre session est nécessaire.

1. Installez une extension navigateur type « Get cookies.txt LOCALLY » (Chrome/Firefox).
2. Connectez-vous à Instagram ou Facebook, exportez les cookies au format Netscape.
3. Passez le fichier via `--cookies` (CLI) ou collez son contenu dans la section « Cookies » de l'interface web.

Les cookies sont utilisés uniquement le temps du traitement puis supprimés du disque.

## Variables d'environnement (déploiement)

| Variable | Description |
|---|---|
| `ACCESS_CODE` | Si défini, l'interface et l'API exigent ce code (protège l'instance publique). |
| `JOB_TTL` | Durée de rétention des ZIP générés en secondes (défaut : 7200 = 2 h). |
| `PORT` | Port d'écoute (défaut : 8000 en Docker, 5000 en local). |

## Bonnes pratiques

- Utilisez cet outil uniquement sur des contenus que vous avez le droit d'exploiter (vos propres comptes, ceux de vos clients avec leur accord, contenus libres de droits).
- Respectez les conditions d'utilisation d'Instagram et de Facebook ainsi que le droit d'auteur des photographes.
- Évitez les limites trop élevées et les lancements en rafale : les plateformes peuvent restreindre temporairement votre IP ou votre compte.
