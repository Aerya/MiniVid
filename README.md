# 🎬 MiniVid

MiniVid est une application web auto-hébergée légère qui permet de parcourir, organiser et lire vos vidéos locales depuis n’importe quel appareil.  
Pensée pour être simple, rapide et efficace, elle combine navigation par dossiers, tags automatiques, favoris, et un lecteur intégré compatible avec les formats vidéo modernes.

---

## ✨ Fonctionnalités

### 📂 Navigation par dossiers
- Accédez à vos vidéos avec une arborescence claire

### 🔖 Tags automatiques
- Extraction depuis les noms de fichiers  
- Tags globaux par dossier  
- Tags individuels par fichier  
- Multi-sélection et recherche par tags  
- Blacklist configurable pour supprimer les mots inutiles (`and`, `the`, `source`, etc.)

### 🔍 Recherche avancée
- Par nom de fichier  
- Par tags multiples  
- Par favoris  
- Par statut **Lue / Non lue**

### 🗂 Filtres et tris personnalisables
- Nom  
- Taille  
- Date de modification  
- Statut **Lues / Non lues**

### ⭐ Favoris
- Marquez vos vidéos d’un clic (★)  
- Accédez à la vue dédiée **Favoris**

### 🎥 Lecteur intégré (HTML5 natif)
- Supporte **mp4**, **webm** et **mkv** (Chrome/Chromium)  
- Les fichiers non compatibles avec Firefox (`.mkv`, `.avi`, `.flv`, `.m2ts`)  
  → automatiquement basculés en **remux/transcodage à la volée** avec `ffmpeg` si activé  
  ⚠️ Peut solliciter fortement le CPU

### 🖼️ Miniatures automatiques
- Générées avec `ffmpeg`  
- Capture par défaut à **5 secondes** (pour éviter logos/intro)  
- Ajustable via les variables `MINI_THUMB_OFFSET`, `MINI_THUMB_MAX`

### 📱 Interface responsive
- Desktop, tablette et mobile

### 🌙 Mode clair / sombre
- Bascule instantanée

### 🛠️ Page Maintenance
- Rescan complet de la bibliothèque  
- Purge des miniatures  
- Journal d’événements en direct (logs des actions)

### ⏱️ Scan automatique
- Toutes les heures par défaut  
- Intervalle configurable via `MINI_SCAN_INTERVAL`

### 🔐 Authentification optionnelle
- Mode public  
- Ou mono-utilisateur avec identifiant/mot de passe

### ⚙️ Configuration simple
- Tout se règle via **variables d’environnement** dans votre `docker-compose.yml`

---

## ⚙️ Variables d’environnement

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
| **MINI_PLAYBACK**                | `direct`                          | Mode lecture : `direct`, `auto`, `remux`                                   |
| **MINI_TRANSCODE**               | `0`                               | Autoriser le transcodage H.264/AAC (1 = oui, 0 = non)                      |
| **MINI_FIREFOX_MKV_FALLBACK**    | `1`                               | Force le remux des `.mkv` dans Firefox                                     |
| **MINI_AUTOSCAN**                | `1`                               | Activer le rescan automatique (1 = oui)                                    |
| **MINI_SCAN_INTERVAL**           | `3600`                            | Intervalle entre scans auto (en secondes)                                  |
| **MINI_THUMB_OFFSET**            | `5`                               | Seconde du screenshot miniature                                            |
| **MINI_THUMB_MAX**               | `30`                              | Offset max (si vidéo longue)                                               |
| **MINI_FFPROBE_TIMEOUT**         | `10`                              | Timeout en secondes pour `ffprobe`/`ffmpeg`                                |
| **API_READ_KEY**                 | *(vide)*                          | Clé API (optionnelle) pour accès en lecture seule                          |

---




L'indexation des fichiers se fait à la volée au 1er lancement, plus ou moins rapidement selon la quantité de vidéos et le CPU.
Le transcodage sous Firefox/LibreWolf peut faire souffrir le CPU sur une petite machine, je ne l'ai pas optimisé vu qu'il est plus simple de passer par un autre navigateur.
Aucun appel externe, tout est 100% local. Fonctionne en http://IP:port comme en reverse proxy.




## 🛠️ Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/Aerya/MiniVid.git
cd MiniVid
```

### 2. Construire l'image Docker

```bash
docker build --no-cache
```

### 3. Si vous voulez utiliser l'authentificaiton, éditer le .env en conséquence 

```bash
# URL interne du service
APP_URL=http://minivid:8080

# Auth (laisser vide pour désactiver l'auth)
MINI_USER=
MINI_PASS=

# Fréquence en secondes (3600 = 1h)
INTERVAL=3600
```

### 4. Editer le docker-compose pour configurer les dossiers, noms et volumes 

```bash
services:
  minivid:
    build: .
    container_name: minivid
    restart: always
    environment:
      TZ: Europe/Paris
      MEDIA_DIRS: /videos1|/videos2|/videos3|/videos4|/videos5
      MEDIA_NAMES: ruTorrent|MeTube|Docs|Concerts|Tests formats vidéo
      DATA_DIR: /data
      THUMB_DIR: /cache/thumbs
      MINI_ALLOWED_EXT: .mp4,.webm,.mkv,.avi,.flv,.m2ts
      MINI_PLAYBACK	Mode de lecture : auto
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
      - /mnt/user/rutorrent-direct:/videos1:ro
      - /mnt/user/MeTube:/videos2:ro
      - /mnt/user/TEST/Docs:/videos3:ro
      - /mnt/user/TEST/Concerts:/videos4:ro
      - /mnt/user/TEST/Formats:/videos5:ro
      - /mnt/user/appdata/MiniVid/data:/data
      - /mnt/user/appdata/MiniVid/cache:/cache
      - /etc/localtime:/etc/localtime:ro
      - /etc/timezone:/etc/timezone:ro
    ports:
      - "8080:8080"

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

### 5. Lancer le Docker MiniVid

```bash
docker compose up -d
```
