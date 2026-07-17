# CaptureINSTAGRAM

Outil pour designers : télécharge les photos d'un compte **Instagram** ou **Facebook** et les convertit automatiquement en **WebP**, prêtes à intégrer sur le web.

- 📥 Téléchargement des photos d'un profil, d'une page ou d'un post (moteur [gallery-dl](https://github.com/mikf/gallery-dl))
- 🔄 Conversion WebP avec qualité réglable, mode sans perte et redimensionnement optionnel
- 🖥️ Interface web avec suivi en temps réel et export ZIP
- ⌨️ CLI pour l'automatisation

## Installation

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

1. Collez l'URL du compte (`https://www.instagram.com/nomducompte/`, `https://www.facebook.com/nomdelapage`) ou tapez simplement `@nomducompte` (Instagram).
2. Réglez le nombre de photos, la qualité WebP (85 par défaut) et éventuellement une taille max en pixels.
3. Lancez, suivez la progression, puis téléchargez le ZIP contenant les WebP.

## Ligne de commande

```bash
python cli.py @natgeo --limit 20 --quality 80 --out ./export
python cli.py https://www.facebook.com/pagepublique --max-size 1920
python cli.py @moncompte --cookies cookies.txt --keep-originals
```

| Option | Description |
|---|---|
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

## Bonnes pratiques

- Utilisez cet outil uniquement sur des contenus que vous avez le droit d'exploiter (vos propres comptes, ceux de vos clients avec leur accord, contenus libres de droits).
- Respectez les conditions d'utilisation d'Instagram et de Facebook ainsi que le droit d'auteur des photographes.
- Évitez les limites trop élevées et les lancements en rafale : les plateformes peuvent restreindre temporairement votre IP ou votre compte.
