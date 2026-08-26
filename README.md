# MiniVid

MiniVid est une application web auto-hébergée légère qui permet de parcourir, organiser et lire vos vidéos locales depuis n’importe quel appareil.  
Pensée pour être simple, rapide et efficace, elle combine navigation par dossiers, tags automatiques, favoris, vidéos similaires, et un lecteur intégré compatible avec les formats vidéo modernes.

---

## Nouveautés v2.1

- **Vidéos similaires** : affiche sous chaque vidéo une grille de vidéos partageant des tags communs (configurable : 1, 2 ou 3 tags minimum).
- **Lecture directe prioritaire** : le fichier original est proposé en premier, sans supposer les capacités du navigateur à partir de son nom.
- **Fallback HLS automatique** : si le navigateur refuse la vidéo ou ne produit aucune image, MiniVid bascule vers HLS en conservant la position de lecture.
- **HLS plus fiable** : les ruptures d'horodatage sont signalées et les segments ne deviennent visibles qu'une fois leur écriture terminée.
- **Détection NVENC corrigée** : le test matériel utilise une dimension acceptée par les pilotes NVIDIA récents.
- **Gestion des sources** : association de plusieurs sources à un ou plusieurs clients qBittorrent ou ruTorrent depuis la WebUI.
- **Statistiques BitTorrent** : panneau « Fichier et partage » replié par défaut, avec nom exact, lien vers le client et un bloc distinct par torrent pour ses statistiques.
- **Suppression contrôlée et vérifiée** : suppression simple d'un fichier ou retrait de tous les torrents correspondant exactement au chemin, avec leurs données, activation globale, règle par source et confirmation par un second clic. MiniVid vérifie ensuite la disparition des hash et du fichier avant de retirer la vidéo de son index.
- **Maintenance compacte** : journal paginé par groupes de huit événements.

---

## Nouveautés v2.0

- **Interface moderne** : design avec police **Inter**, effets de transparence et animations fluides.
- **Lecture native** : priorité à la lecture sans transcodage pour les formats supportés par le navigateur.
- **Fallback intelligent** : bascule automatique en HLS lorsqu'une lecture directe n'est pas possible.
- **Optimisations HLS** : accélération matérielle **NVIDIA NVENC** et mise en cache des segments sur disque.
- **Grouper par date** : vue chronologique (Aujourd'hui, Cette semaine, Ce mois...) pour les vidéos.
- **Ergonomie et accessibilité** : chargement progressif, raccourcis clavier (J/K/L, F, M, Espace) et prise en charge des caractères cyrilliques.

---

## Fonctionnalités

### Navigation par dossiers
- Accédez à vos vidéos avec une arborescence claire

### Tags automatiques
- Extraction depuis les noms de fichiers  
- Tags globaux par dossier  
- Tags individuels par fichier  
- Multi-sélection et recherche par tags  
- Blacklist configurable pour supprimer les mots inutiles (`and`, `the`, `source`, etc.)

### Recherche avancée
- Par nom de fichier  
- Par tags multiples  
- Par favoris  
- Par statut **Lue / Non lue**

### Filtres et tris personnalisables
- Nom, Taille, Date de modification
- Statut **Lues / Non lues**
- **Grouper par date** (Vue chronologique)

### Favoris
- Marquez vos vidéos d’un clic
- Accédez à la vue dédiée **Favoris**

### Lecteur intégré (HTML5 natif / HLS)
- Tentative de lecture directe du fichier original dans tous les navigateurs
- Détection des fichiers dont seul l'audio est décodé, notamment certains MKV/HEVC
- Bascule automatique vers HLS si la lecture directe échoue ou ne produit aucune image
- Accélération NVIDIA NVENC lorsque le GPU est exposé au conteneur
- Reprise de la lecture au moment du basculement

Le support direct dépend du navigateur, du système, du conteneur et des codecs installés. Un fichier MKV/HEVC peut par exemple être lu directement dans un navigateur et nécessiter le fallback HLS dans un autre.

### Miniatures automatiques
- Générées avec `ffmpeg`  
- Capture par défaut à **5 secondes** (pour éviter logos/intro)  
- Ajustable via les variables `MINI_THUMB_OFFSET`, `MINI_THUMB_MAX`

### Interface responsive
- Design moderne Inter, Glassmorphism
- Desktop, tablette et mobile
- Skeleton loading pour un affichage fluide

### Mode clair / sombre
- Bascule instantanée

### Page Maintenance
- Rescan complet de la bibliothèque  
- Purge des miniatures et du cache HLS
- Journal d’événements en direct (logs des actions)

### Scan automatique
- Toutes les heures par défaut  
- Intervalle configurable via `MINI_SCAN_INTERVAL`

### Authentification optionnelle
- Mode public  
- Ou mono-utilisateur avec identifiant/mot de passe

### Configuration simple
- Tout se règle via **variables d’environnement** dans votre `docker-compose.yml`

### Gestion des sources et suppressions

- Activation indépendante de la liaison BitTorrent et de la suppression
- Plusieurs clients qBittorrent et ruTorrent configurables depuis la page Maintenance
- Un client peut être associé à plusieurs sources vidéo
- Tous les torrents correspondant au même fichier sont affichés et peuvent être supprimés ensemble avec leurs données
- Trois modes par source : désactivé, fichier uniquement, torrent et données
- Correspondance par chemin complet avant toute action sur un torrent
- Vérification après suppression : tous les hash doivent avoir disparu du client et le fichier doit être absent du disque
- Retrait de la vidéo de l'index, des favoris, de la progression et des caches uniquement après ces vérifications
- En cas d'échec, la vidéo reste indexée et MiniVid affiche l'erreur renvoyée

Cette fonction exige que l'authentification MiniVid soit activée. Les mots de passe des clients sont chiffrés sur disque à partir de `SECRET_KEY` et ne sont jamais renvoyés par l'API. Une modification de `SECRET_KEY` rendra les mots de passe enregistrés illisibles ; il faudra alors les saisir à nouveau.


## Captures et article

Pour découvrir MiniVid en images et lire la présentation complète, consultez l’article dédié sur mon blog :  

[MiniVid — Indexage, lecture, tags et favoris pour vos vidéos locales](https://upandclear.org/2025/09/03/minivid-indexage-lecture-tags-et-favoris-pour-vos-videos-locales/)

![MiniVid Screenshot](https://upandclear.org/wp-content/uploads/2026/01/minivid1.jpg)
![MiniVid Screenshot](https://upandclear.org/wp-content/uploads/2026/01/minivid2.jpg)
![MiniVid Screenshot](https://upandclear.org/wp-content/uploads/2026/01/minivid3.jpg)
![MiniVid Screenshot](https://upandclear.org/wp-content/uploads/2026/01/minivid4.jpg)

---

## Variables d'environnement

| Variable                         | Valeur par défaut                 | Description                                                                |
| -------------------------------- | --------------------------------- | -------------------------------------------------------------------------- |
| **MEDIA_DIRS**                   | *(vide)*                          | Liste des dossiers vidéos (séparés par `|`)                                |
| **MEDIA_NAMES**                  | `Dossier 1, Dossier 2…`           | Noms affichés pour chaque dossier (même ordre que `MEDIA_DIRS`)            |
| **MINI_ALLOWED_EXT**             | `.mp4,.webm,.mkv,.avi,.flv,.m2ts` | Extensions autorisées                                                      |
| **MINI_BANNED_TAGS**             | *(vide)*                          | Liste de mots à ignorer lors de la génération de tags (`and,the,source,…`) |
| **DATA_DIR**                     | `/data`                           | Dossier de stockage interne (état, favoris, prefs)                         |
| **THUMB_DIR**                    | `/cache/thumbs`                   | Dossier cache des miniatures                                               |
| **MINI_USER**                    | *(vide)*                          | Identifiant de connexion (optionnel)                                       |
| **MINI_PASS**                    | *(vide)*                          | Mot de passe de connexion (optionnel)                                      |
| **SECRET_KEY**                   | *(aléatoire)*                     | Clé de session Flask (authentification)                                    |
| **MINI_PLAYBACK**                | `direct`                          | Variable historique conservée pour compatibilité                                  |
| **MINI_TRANSCODE**               | `0`                               | Autoriser le transcodage H.264/AAC (1 = oui, 0 = non)                      |
| **MINI_FIREFOX_MKV_FALLBACK**    | `1`                               | Variable historique conservée pour compatibilité                                  |
| **MINI_HLS_SEGMENT_DURATION**    | `10`                              | Durée d'un segment HLS en secondes                                           |
| **MINI_AUTOSCAN**                | `1`                               | Activer le rescan automatique (1 = oui)                                    |
| **MINI_SCAN_INTERVAL**           | `3600`                            | Intervalle entre scans auto (en secondes)                                  |
| **MINI_THUMB_OFFSET**            | `5`                               | Seconde du screenshot miniature                                            |
| **MINI_THUMB_MAX**               | `30`                              | Offset max (si vidéo longue)                                               |
| **MINI_FFPROBE_TIMEOUT**         | `10`                              | Timeout en secondes pour `ffprobe`/`ffmpeg`                                |

---





L'indexation des fichiers se fait à la volée au 1er lancement, plus ou moins rapidement selon la quantité de vidéos et le CPU.
Le transcodage utilise NVENC si un GPU NVIDIA et la capacité `video` sont disponibles dans le conteneur.
Les vidéos, miniatures, tags et préférences restent locaux. Les fonctions optionnelles qui utilisent Gemini et le chargement de `hls.js` depuis son CDN nécessitent toutefois un accès externe. MiniVid fonctionne avec une adresse `http://IP:port` comme derrière un reverse proxy.




## Installation manuelle avec Docker

### 1. Copier et éditer le fichier `.env`

Un fichier `.env.example` est fourni comme base :

```bash
cp .env.example .env
```

Puis éditez `.env` selon vos besoins :

```bash
# URL interne du service
APP_URL=http://minivid:8080

# Auth (laisser vide pour désactiver l'auth)
MINI_USER=michel
MINI_PASS=m1ch3l

# Fréquence en secondes (3600 = 1h)
INTERVAL=3600

```

### 2. Générer la clé de session

```bash
openssl rand -hex 32
```

### 3. Configurer Docker Compose

```bash
services:
  minivid:
    image: ghcr.io/aerya/minivid:latest
    container_name: minivid
    restart: always
    environment:
      TZ: Europe/Paris
      NVIDIA_DRIVER_CAPABILITIES: compute,utility,video
      MEDIA_DIRS: /videos1|/videos2
      MEDIA_NAMES: ruTorrent|MeTube
      DATA_DIR: /data
      THUMB_DIR: /cache/thumbs
      MINI_ALLOWED_EXT: .mp4,.webm,.mkv,.avi,.flv,.m2ts,.ts
      MINI_PLAYBACK: "auto"
      MINI_TRANSCODE: 1
      MINI_FIREFOX_MKV_FALLBACK: 1
      MINI_THUMB_OFFSET: 5
      MINI_THUMB_MAX: 30
      MINI_AUTOSCAN: 1
      # Auth (prises du .env ; si vide => pas d'auth)
      MINI_USER: ${MINI_USER}
      MINI_PASS: ${MINI_PASS}
      # En console : openssl rand -hex 32
      SECRET_KEY: 
      # Liste noire tags (les mots de moins de 3 lettres sont automatiquement bannis)
      MINI_BANNED_TAGS:  >
        and,the,source,video,videos,vid,vids,film,movie,part,
        les,une,des,ils,elles,sur,sous,dans,par,pour,sans,avec,chez,
        cet,cette,ces,mon,mes,ton,tes,ses,notre,nos,votre,vos,leur,leurs,
        qui,que,quoi,dont,quand,comme,
        your,they,for,with,without,into,onto,about,this,that,these,those,
        here,there,then,than,are,was,being,been,have,had,just,only,
        over,under,very,more,most,less,were,com,net
    volumes:
      - /mnt/Fichiers/rutorrentdirect:/videos1:ro
      - /mnt/Fichiers/metube:/videos2:ro
      - /mnt/Docker/MiniVid/data:/data
      - /mnt/Docker/MiniVid/cache:/cache
    ports:
      - "8080:8080"
    # Nécessite nvidia-container-toolkit sur l'hôte.
    # Retirez cette ligne si aucun GPU NVIDIA n'est disponible.
    gpus: all

    # Scan toutes les INTERVAL secondes
  minivid-scheduler:
    image: curlimages/curl:8.10.1
    container_name: minivid-scheduler
    depends_on:
      - minivid
    restart: always
    environment:
      APP_URL: ${APP_URL}
      MINI_USER: ${MINI_USER}
      MINI_PASS: ${MINI_PASS}
      INTERVAL: ${INTERVAL}
    command: >
      sh -c '
        set -eu;
        for i in $(seq 1 60); do curl -fsS "$APP_URL/maintenance" >/dev/null 2>&1 && break || sleep 2; done
        while :; do
          if [ -n "$MINI_USER" ] && [ -n "$MINI_PASS" ]; then
            # login (remember=on)
            curl -sS -c /tmp/c.jar -X POST "$APP_URL/login" \
              -d "username=$MINI_USER" -d "password=$MINI_PASS" -d "remember=on" -o /dev/null || true
            if curl -sS -b /tmp/c.jar "$APP_URL/api/maintenance/progress" | grep -qi "\"running\"\\s*:\\s*true"; then
              sleep 120
            else
              curl -m 5 -sS -b /tmp/c.jar -X POST "$APP_URL/api/maintenance/rescan" -o /dev/null || true
            fi
          else
            curl -m 5 -sS -X POST "$APP_URL/api/maintenance/rescan" -o /dev/null || true
          fi
          sleep "$INTERVAL"
        done
      '
```


### Activer NVIDIA NVENC

Installez d'abord NVIDIA Container Toolkit sur l'hôte, configurez le runtime Docker puis redémarrez Docker. La syntaxe exacte d'installation dépend de la distribution. La section `minivid` du Compose doit ensuite contenir :

```yaml
services:
  minivid:
    gpus: all
    environment:
      NVIDIA_DRIVER_CAPABILITIES: compute,utility,video
```

Après le déploiement, ce message confirme que l'encodeur est disponible :

```text
Accélération matérielle NVIDIA NVENC détectée.
```

Sans GPU compatible, MiniVid conserve le fallback logiciel avec `libx264`.

### Configurer les clients et les suppressions

Ouvrez **Maintenance**, puis **Sources vidéo et clients BitTorrent**.

1. Ajoutez un ou plusieurs clients qBittorrent ou ruTorrent avec leur URL et leurs identifiants.
2. Enregistrez, puis utilisez **Tester** pour valider chaque connexion.
3. Associez chaque source au client qui gère ses fichiers. Un même client peut être choisi pour plusieurs sources.
4. Indiquez le chemin de la source tel qu'il est vu par le client, par exemple `/downloads`.
5. Choisissez le mode de suppression de chaque source.
6. Activez la liaison BitTorrent pour afficher les statistiques.
7. Activez séparément la suppression lorsque la configuration a été vérifiée.

Pour le mode **Fichier uniquement**, le volume correspondant doit être monté en lecture-écriture :

```yaml
volumes:
  - /chemin/videos-simples:/videos2:rw
```

Pour le mode **Torrent et données**, le volume MiniVid peut rester en lecture seule : le client BitTorrent supprime lui-même les données. MiniVid refuse l'action s'il ne peut pas faire correspondre exactement le chemin de la vidéo avec un torrent unique.

La prise en charge ruTorrent utilise le plugin officiel `httprpc` et son action `removewithdata`. Le plugin `erasedata` doit être disponible pour supprimer les données en plus de l'entrée rTorrent.

## Installation automatisée pour Windows

[Télécharger et lancer Windows-MiniVid.cmd](https://github.com/Aerya/MiniVid/blob/main/Windows-MiniVid.cmd)

- Il installera si nécessaire Docker Desktop sur la machine,
- Guidage complet pour la configuration de MiniVid (édition complète disponible),
- Ajout de dossiers locaux comme distants (SMB/CIFS avec ou sans user:pwd).

![MiniVid Windows](https://upandclear.org/wp-content/uploads/2025/09/minivid-windows.png.webp)
