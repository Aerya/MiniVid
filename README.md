# MiniVid

MiniVid transforme un ou plusieurs dossiers vidéo en médiathèque web privée. L'application indexe les fichiers, génère les miniatures et permet de parcourir, rechercher et lire la collection depuis un navigateur.

La lecture directe est toujours tentée en premier. Si le navigateur ne sait pas décoder le fichier, MiniVid bascule automatiquement vers un flux HLS H.264/AAC, sans perdre la position de lecture.

## Ce que MiniVid propose

- navigation par source et par dossier ;
- recherche, tags, favoris, filtres et statut lu/non lu ;
- miniatures automatiques et vidéos similaires ;
- interface responsive avec thèmes clair et sombre ;
- lecture directe avec fallback HLS logiciel ou NVIDIA NVENC ;
- rescans automatiques et page Maintenance ;
- authentification mono-utilisateur facultative ;
- liaison à plusieurs clients qBittorrent ou ruTorrent ;
- suppression contrôlée d'un fichier ou de tous ses torrents associés, variantes cross-seed comprises.

## Aperçu

![Bibliothèque MiniVid](docs/screenshots/library.png)
![Lecteur et informations BitTorrent](docs/screenshots/player-sharing.png)
![Maintenance et configuration des sources](docs/screenshots/maintenance.png)

D'autres captures et une présentation détaillée sont disponibles dans [l'article consacré à MiniVid](https://upandclear.org/2025/09/03/minivid-indexage-lecture-tags-et-favoris-pour-vos-videos-locales/).

## Installation

```bash
git clone https://github.com/Aerya/MiniVid.git
cd MiniVid
cp .env.example .env
```

Éditez ensuite :

1. les volumes vidéo dans `docker-compose.yml` ;
2. `MEDIA_DIRS` et `MEDIA_NAMES` dans `.env` ;
3. les identifiants et la clé de session si l'authentification est souhaitée.

Générez une clé de session avec :

```bash
openssl rand -hex 32
```

Placez le résultat dans `SECRET_KEY`, puis démarrez MiniVid :

```bash
docker compose up -d
```

L'interface est disponible sur `http://IP_DU_SERVEUR:8080`.

Le premier scan peut prendre quelques minutes selon la taille de la collection et les performances du stockage.

## Ajouter des sources

Chaque volume vidéo doit correspondre à un chemin de `MEDIA_DIRS`. Les noms de `MEDIA_NAMES` suivent le même ordre et les listes sont séparées par `|`.

```yaml
volumes:
  - /mnt/films:/videos1:ro
  - /mnt/archives:/videos2:ro
```

```dotenv
MEDIA_DIRS=/videos1|/videos2
MEDIA_NAMES=Films|Archives
```

Utilisez `:ro` pour une médiathèque en lecture seule. Une source configurée pour la suppression directe de fichiers doit être montée en `:rw`.

## Lecture et transcodage

MiniVid envoie d'abord le fichier original au navigateur. La lecture reste donc immédiate et sans transcodage lorsque le conteneur et les codecs sont pris en charge. En cas d'échec ou d'absence d'image décodée, le lecteur passe automatiquement en HLS.

Le support direct dépend du navigateur et du système. Un MKV/HEVC peut être lu nativement sur une machine et nécessiter le fallback sur une autre.

Pour désactiver tout transcodage :

```dotenv
MINI_TRANSCODE=0
```

### NVIDIA NVENC

Après installation de NVIDIA Container Toolkit sur l'hôte, décommentez dans le Compose :

```yaml
gpus: all
environment:
  NVIDIA_DRIVER_CAPABILITIES: compute,utility,video
```

MiniVid utilise alors NVENC s'il est disponible, sinon `libx264`.

## Clients BitTorrent et suppression

La configuration se fait dans **Maintenance > Sources vidéo et clients BitTorrent**.

1. Ajoutez un client qBittorrent ou ruTorrent et testez la connexion.
2. Associez chaque source au client concerné et indiquez le chemin vu par celui-ci.
3. Choisissez le mode de suppression de la source.
4. Activez séparément la liaison BitTorrent et l'autorisation de suppression.

MiniVid affiche tous les torrents correspondant au fichier. Lors d'une suppression « torrent et données », il retire tous les torrents associés, y compris les variantes cross-seed reconnues par nom et taille, puis vérifie la disparition des torrents et du fichier avant de retirer la vidéo de l'index.

La suppression exige l'authentification MiniVid. Les mots de passe des clients sont chiffrés avec `SECRET_KEY` ; changer cette clé oblige à les saisir de nouveau.

Pour ruTorrent, le plugin `httprpc` est utilisé. La suppression des données nécessite aussi l'action `removewithdata` fournie par le plugin `erasedata`.

## Configuration utile

| Variable | Défaut | Rôle |
| --- | --- | --- |
| `MEDIA_DIRS` | vide | Chemins vidéo internes, séparés par `|` |
| `MEDIA_NAMES` | automatique | Noms affichés, dans le même ordre |
| `MINI_ALLOWED_EXT` | formats courants | Extensions indexées |
| `MINI_TRANSCODE` | `0` | Autorise le fallback HLS |
| `MINI_AUTOSCAN` | `1` | Active le rescan automatique |
| `MINI_SCAN_INTERVAL` | `3600` | Intervalle de scan en secondes |
| `MINI_THUMB_OFFSET` | `5` | Position de la miniature en secondes |
| `MINI_USER` / `MINI_PASS` | vides | Active l'authentification si les deux sont définis |
| `SECRET_KEY` | aléatoire | Sessions et chiffrement des identifiants clients |

Toutes les valeurs prêtes à personnaliser sont regroupées dans `.env.example`.

## Maintenance et mises à jour

La page Maintenance permet de rescanner la bibliothèque, purger les caches et consulter le journal récent. Le rescan périodique est assuré directement par MiniVid ; aucun conteneur planificateur séparé n'est nécessaire.

```bash
docker compose pull
docker compose up -d
```

Les données d'application sont conservées dans `./data` et les miniatures ainsi que les segments temporaires dans `./cache`.

## Windows

Le script [Windows-MiniVid.cmd](https://github.com/Aerya/MiniVid/blob/main/Windows-MiniVid.cmd) est prévu pour Windows 10/11 x64 avec PowerShell 5.1, WSL2 et Docker Desktop. Il peut installer et démarrer Docker Desktop, générer une configuration pour des dossiers locaux ou SMB/CIFS, tester les montages réseau, configurer l'authentification et valider le Compose avant le déploiement.

Le profil initial utilise `C:\Videos`. L'assistant permet ensuite d'ajouter jusqu'à dix sources et de choisir un autre port.

## Vie privée

Les vidéos, l'index, les miniatures et les préférences restent sur votre installation. La génération facultative de tags avec Gemini et le chargement de `hls.js` depuis son CDN nécessitent un accès externe.
