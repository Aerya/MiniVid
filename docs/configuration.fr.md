# Configuration de MiniVid

[← README](../README.fr.md) · [English](configuration.md)

Les réglages courants sont dans `.env` et dans **Maintenance**. Redémarrez avec `docker compose up -d` après une modification de `.env`.

## Plusieurs sources

Ajoutez vos volumes au service `minivid` dans `docker-compose.yml` :

```yaml
volumes:
  - /mnt/videos:/videos1:ro
  - /mnt/archives:/videos2:ro
  - ./data:/data
  - ./cache:/cache
```

Puis renseignez les chemins **internes** et les noms, dans le même ordre :

```dotenv
MEDIA_DIRS=/videos1|/videos2
MEDIA_NAMES=Vidéos|Archives
```

Les dossiers `cross-seed-links` sont exclus par défaut. `MINI_EXCLUDED_DIRS` permet de définir une liste de noms séparés par des virgules.

## Accès protégé et données

```dotenv
MINI_USER=votre-utilisateur
MINI_PASS=votre-mot-de-passe
SECRET_KEY=une-cle-longue-et-aleatoire
```

Générez une clé avec `openssl rand -hex 32`. Le lanceur `minivid.sh` en crée déjà une au premier démarrage.

Conservez **`data/` et `SECRET_KEY`** lors des mises à jour : les mots de passe des clients sont chiffrés avec cette clé. `cache/` contient les miniatures et segments de lecture temporaires. Pour un accès public, utilisez un reverse proxy HTTPS et l’authentification.

## Suppression et nettoyage

Dans **Maintenance → Sources et clients BitTorrent** :

1. Ajoutez un client qBittorrent ou ruTorrent, puis testez sa connexion.
2. Associez vos sources. Le « chemin vu par le client » doit correspondre au préfixe exact de son `content_path`, pas au montage MiniVid.
3. Choisissez le mode par source, puis activez séparément la liaison et la suppression.

La suppression directe d’un fichier nécessite un montage `:rw`. La suppression « torrent et données » passe par le client. Les torrents associés et les variantes cross-seed reconnues sont vérifiés avant de retirer la vidéo de l’index.

Dans **Stockage**, comparez les doublons SHA-256 ou examinez une sélection de fichiers. Les favoris, protections, liens physiques et associations torrent invérifiables peuvent bloquer la suppression. Les gains restent estimatifs avec les snapshots et reflinks.

Sur une page de lecture, choisissez **conserver**, **protéger** ou **autoriser le nettoyage**, puis vos conditions. Une règle ne s’applique qu’à la version exacte du fichier. Le seuil d’arrêt d’un nettoyage doit dépasser son seuil de déclenchement : par exemple, démarrer sous 15 % libres et arrêter à 20 %.

L’automatisation exige une fédération configurée, un propriétaire unique, l’authentification, des sources autorisées et un client qBittorrent compatible. Elle reste désactivée tant que vous ne l’activez pas dans **Stockage → Règles de nettoyage**. Un temps de seed inconnu bloque toute condition temporelle, notamment avec ruTorrent.

## Synchronisation entre instances

Configurez un identifiant distinct par instance avant son premier démarrage, un secret commun d’au moins 16 caractères et les URL des autres instances joignables depuis les conteneurs :

```dotenv
MINI_INSTANCE_ID=mini-a
MINI_SYNC_SECRET=remplacer-par-un-long-secret-commun
MINI_SYNC_PEERS=http://adresse-instance-b:8080
```

Sur B, utilisez `MINI_INSTANCE_ID=mini-b` et l’adresse de A. Le fichier `data/instance-id` existant prime sur la variable : conservez-le.

Les favoris et règles sont synchronisés par empreinte de contenu, même si les chemins diffèrent. La synchronisation fonctionne au mieux : un pair indisponible ne reçoit pas automatiquement les changements manqués. Vérifiez les deux instances avant d’activer l’automatisation et choisissez un seul propriétaire.

## Réglages utiles

| Variable | Utilité |
| --- | --- |
| `MINIVID_PORT=8080` | Port web publié par Docker |
| `MINI_AUTOSCAN=1` | Actualisation périodique de l’index |
| `MINI_SCAN_INTERVAL=3600` | Intervalle en secondes |
| `MINI_ALLOWED_EXT` | Extensions autorisées, séparées par des virgules |
| `MINI_BANNED_TAGS` | Mots à ignorer dans les tags automatiques |
| `MINI_TRANSCODE=0` | Désactiver la conversion HLS |
| `MINIVID_GPU=cpu` | Fonctionner sans GPU |
| `MINIVID_GPU_FALLBACK=1` | Revenir au CPU si le GPU est indisponible |

Le Compose fourni prépare automatiquement l’accès GPU. Son helper accède au socket Docker et aux répertoires CDI de l’hôte ; le conteneur principal n’est pas privilégié. NVIDIA exige le pilote et NVIDIA Container Toolkit ; Intel/AMD utilise `/dev/dri`. Consultez [le Compose](../docker-compose.yml) avant un déploiement personnalisé.

## Windows

[`Windows-MiniVid.cmd`](../Windows-MiniVid.cmd) propose une configuration FR/EN pour Windows 10/11 x64 avec PowerShell 5.1, WSL2 et Docker Desktop, avec dossiers locaux ou SMB/CIFS. Il est fourni tel quel et n’a pas été validé sur une machine Windows par le mainteneur.
