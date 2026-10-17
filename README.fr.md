<p align="center">
  <img src="static/logo.svg" alt="MiniVid" width="84">
</p>
<h1 align="center">MiniVid</h1>
<p align="center"><strong>Vos dossiers vidéo, enfin agréables à parcourir.</strong><br>Une médiathèque web personnelle, à héberger chez vous.</p>
<p align="center"><a href="README.md">English</a> · <strong>Français</strong></p>
<p align="center"><a href="#fonctionnalités">Fonctionnalités</a> · <a href="#installation">Installation</a> · <a href="#gpu">GPU</a> · <a href="#stockage">Stockage</a> · <a href="#aperçus">Aperçus</a> · <a href="#documentation">Documentation</a></p>

![La bibliothèque MiniVid](docs/screenshots/library.png)

## Fonctionnalités

- **Parcourir** vos vidéos : dossiers, recherche, tags et favoris.
- **Regarder** depuis un navigateur, avec reprise de lecture et plein écran.
- **Retrouver** les vidéos jamais lues et les contenus similaires.
- **Faire le tri** : espace utilisé, doublons vérifiés et suppression avec confirmation.
- **Personnaliser** les couleurs et les thèmes. Interface en français et en anglais.
- **Connecter** qBittorrent ou ruTorrent pour consulter les informations de partage.

Les statuts utilisent le temps réellement regardé : **non lue < 30 %**, **en cours de 30 à moins de 70 %**, **lue dès 70 %**. Les tags à ignorer se gèrent dans **Maintenance**.

## Installation

Sur Linux avec **Docker Engine 25+ et Docker Compose** :

```bash
git clone https://github.com/Aerya/MiniVid.git
cd MiniVid
./minivid.sh
```

Ouvrez **`http://IP_DU_SERVEUR:8080`**. Placez vos vidéos dans `./videos`, ou modifiez `.env` :

```dotenv
MINIVID_MEDIA_PATH=/mnt/videos
```

Relancez `./minivid.sh` après modification. Les vidéos sont montées **en lecture seule** par défaut.

**Dockge :** utilisez le [`docker-compose.yml`](docker-compose.yml) et le [modèle `.env`](.env.example). [Plusieurs dossiers ou accès protégé →](docs/configuration.fr.md)

**Mise à jour :** `docker compose pull` puis `docker compose up -d`. Conservez `data/`, qui contient vos réglages et votre historique.

## GPU

**Pourquoi ?** Certaines vidéos doivent être converties pour être lues dans le navigateur. Le GPU peut accélérer cette conversion et soulager le CPU. Il n’apporte rien aux fichiers lus directement.

**Comment ?** Dans `.env`, choisissez puis relancez MiniVid :

```dotenv
MINI_TRANSCODE=1
MINIVID_GPU=auto
# Remplacez auto par cpu pour utiliser uniquement le processeur.
```

NVIDIA : pilote et NVIDIA Container Toolkit sur l’hôte. Intel/AMD : accès à `/dev/dri`. Si le GPU est indisponible, le CPU prend le relais par défaut.

## Stockage

**Stockage → Analyser les doublons → choisir la copie à garder.**

MiniVid compare le contenu des fichiers. Les liens physiques et le dossier `cross-seed-links` ne sont pas comptés comme des copies supplémentaires. Le gain affiché est une estimation.

La suppression exige une authentification et une autorisation explicite. Le nettoyage automatique est **désactivé par défaut**. [Configurer les clients et le nettoyage →](docs/configuration.fr.md#suppression-et-nettoyage)

## Aperçus

Captures réalisées avec des vidéos de démonstration, sans contenu explicite.

| Lecture | Stockage |
| --- | --- |
| [![Lecteur MiniVid](docs/screenshots/player-sharing.png)](docs/screenshots/player-sharing.png) | [![Espace et doublons](docs/screenshots/storage.png)](docs/screenshots/storage.png) |

![Maintenance MiniVid](docs/screenshots/maintenance.png)

## Documentation

[Configuration et plusieurs sources](docs/configuration.fr.md) · [Windows — assistant fourni tel quel, non testé par le mainteneur](Windows-MiniVid.cmd) · [Signaler un problème](https://github.com/Aerya/MiniVid/issues) · [Licence MIT](LICENSE)

Les vidéos et les données restent sur votre installation. Le lecteur HLS charge sa bibliothèque JavaScript depuis un CDN.

### Compagnon facultatif

MiniVid peut afficher un compagnon externe sous **◇**. Relier les deux services par un réseau Docker privé, puis définir `MINI_EXTENSION_URL` et `MINI_EXTENSION_TOKEN` (même jeton des deux côtés, au moins 24 caractères). Une connexion administrateur est nécessaire. Le compagnon peut ajouter des tags en conservant les tags manuels. Aucun service externe n’est contacté sans cette configuration.
