# MiniVid

MiniVid turns one or more video folders into a private web media library. It indexes files, generates thumbnails, and lets you browse, search and play your collection from a browser.

<p align="center">
  🇬🇧 English ·
  🇫🇷 <a href="https://github.com/Aerya/MiniVid/blob/main/README.fr.md">Français</a>
</p>

Direct playback is always attempted first. If the browser cannot decode a file, MiniVid can fall back to an H.264/AAC HLS stream without losing the playback position.

## Features

- Browse by source and folder, search, tags, favorites, collections, watched/unwatched filters and a strict never-watched view.
- Automatic thumbnails, similar videos, responsive light/dark interface and a persistent French/English language switcher.
- Direct playback with software HLS, NVIDIA NVENC or Intel/AMD VA-API fallback.
- Automatic rescans, optional single-user authentication, and multiple qBittorrent or ruTorrent clients.
- Controlled deletion of a video file or every associated torrent, including matching cross-seed variants.

## Screenshots

![MiniVid library](docs/screenshots/library.png)
![Player and BitTorrent information](docs/screenshots/player-sharing.png)
![Maintenance and source configuration](docs/screenshots/maintenance.png)

## Installation

```bash
git clone https://github.com/Aerya/MiniVid.git
cd MiniVid
./minivid.sh
```

MiniVid creates its configuration and required folders, then starts with `./videos`. Open `http://SERVER_IP:8080`.

To use another folder, change this line in `.env`, then run `./minivid.sh` again:

```dotenv
MINIVID_MEDIA_PATH=/mnt/movies
```

Compose automatically detects NVIDIA, Intel and AMD, including from Dockge. If Docker cannot use the GPU, MiniVid safely falls back to CPU. You can force a mode in `.env`:

```dotenv
MINIVID_GPU=cpu
# auto, cpu, nvidia, vaapi, intel or amd
MINIVID_GPU_FALLBACK=1
```

For an advanced setup, edit the extra video volumes in `docker-compose.yml`, then set matching `MEDIA_DIRS` and `MEDIA_NAMES` values in `.env`. The lists use `|` as their separator.

```yaml
volumes:
  - /mnt/movies:/videos1:ro
  - /mnt/archive:/videos2:ro
```

```dotenv
MEDIA_DIRS=/videos1|/videos2
MEDIA_NAMES=Movies|Archive
```

Use `:ro` for a read-only library. A source intended for direct file deletion must be mounted with `:rw`.

The launcher creates a session key when `openssl` is available. To create one yourself:

```bash
openssl rand -hex 32
```

Put the result in `SECRET_KEY`, then start MiniVid without the launcher if desired:

```bash
docker compose up -d
```

## Playback and GPU acceleration

MiniVid sends browser-compatible files directly. AVI, FLV and M2TS are sent straight to HLS so that playback works consistently in Firefox/LibreWolf, Vivaldi and Chromium. If another direct playback fails or no video frame is decoded, the player switches to HLS. Disable all transcoding with `MINI_TRANSCODE=0`.

An ephemeral helper prepares GPU access before MiniVid starts. It tests the encoder from Docker, repairs stale NVIDIA CDI metadata with `nvidia-ctk` when needed, then exposes NVIDIA or `/dev/dri` to the main container. The MiniVid container is not privileged and no Compose override or `gpus: all` is required.

NVIDIA requires the host driver and NVIDIA Container Toolkit. Intel/AMD requires `/dev/dri/renderD128`. Docker Engine 25 or later is required for CDI. With the default `MINIVID_GPU_FALLBACK=1`, a failed detection selects CPU instead of blocking the stack. ARM64 CPU mode is fully supported; VA-API is attempted with the Mesa drivers in the image.

## BitTorrent clients and deletion

Configure this from **Maintenance > Video sources and BitTorrent clients**:

1. Add a qBittorrent or ruTorrent client and test its connection.
2. Associate each video source with its client and the path seen by that client.
3. Choose the source deletion mode, then separately enable BitTorrent integration and deletion.

MiniVid displays every torrent matching a file. "Torrent and data" deletion removes associated torrents, including matching cross-seed variants, and verifies the result before removing the video from its index. Deleting a favorite displays an additional warning and still requires the final confirmation. Deletion requires MiniVid authentication. Client passwords are encrypted with `SECRET_KEY`; changing that key requires entering them again.

## Useful configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `MINIVID_MEDIA_PATH` | `./videos` | First video directory on the host |
| `MEDIA_DIRS` | `/videos1` | Internal video paths, separated with `|` |
| `MEDIA_NAMES` | `Videos` | Display names in the same order |
| `MINI_ALLOWED_EXT` | common formats | Indexed extensions |
| `MINI_BANNED_TAGS` | supplied list | Words ignored for automatic tags |
| `MINI_TRANSCODE` | `1` | Enables HLS fallback |
| `MINI_AUTOSCAN` | `1` | Enables automatic rescanning |
| `MINI_SCAN_INTERVAL` | `3600` | Scan interval in seconds |
| `MINI_USER` / `MINI_PASS` | empty | Enables authentication when both are set |
| `SECRET_KEY` | random | Sessions and client-password encryption |

## Maintenance and updates

The Maintenance page can rescan the library, clear caches and show the recent journal. Periodic scanning runs inside MiniVid, so no separate scheduler is required.

```bash
docker compose pull
docker compose up -d
```

Application data stays in `./data`; thumbnails and temporary segments stay in `./cache`.

## Windows

[Windows-MiniVid.cmd](https://github.com/Aerya/MiniVid/blob/main/Windows-MiniVid.cmd) offers an interactive English/French selection at startup. It targets Windows 10/11 x64 with PowerShell 5.1, WSL2 and Docker Desktop. It can install and start Docker Desktop, build a configuration for local folders or SMB/CIFS shares, test network mounts, configure authentication and validate Compose before deployment.

The script is provided **as is**. It has not been tested on a local Windows machine by the project maintainer, so review it and keep backups before using destructive menu entries. The default profile uses `C:\Videos`; the wizard can add up to ten sources and choose another port.

## Privacy

Videos, the index, thumbnails and preferences remain on your installation. Loading `hls.js` from its CDN requires external network access.
