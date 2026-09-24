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

## Storage review and cleanup

The **Storage** page (`/storage`) offers a sortable list or thumbnail gallery, with standard, wide and full-width layouts saved in the browser. It sorts videos by size, file age, playback starts, latest play and highest reached playback position. Stats start accumulating after this update; the old watched flag cannot reconstruct historical play counts. A duplicate scan hashes equal-sized, distinct physical files with SHA-256 and shows hardlinks separately. The `cross-seed` tag is displayed but never used as proof that two torrents share a file. Group deletion is limited to verified copies on unlinked, non-BitTorrent sources. You can also tick videos across pages, preview eligible and blocked items, and confirm a manual bulk deletion; favorites, protected videos, hardlinks and unverifiable torrents are blocked. The global deletion switch still applies.

Each video's **Cleanup candidate** policy records ratio and seeding-time requirements (AND/OR) and chooses immediate cleanup or disk-pressure cleanup. In disk-pressure mode, **start below 15% free** means cleanup may start once available space drops below 15%; **stop at 20% free** means it stops once free space reaches 20%. The stop threshold must be higher than the start threshold. Set the default values for **new** cleanup candidates on `/storage`; existing decisions do not change. Favorites and protected videos are excluded. A rule is bound to the exact local file version and is invalidated if the file changes. When ruTorrent does not report seeding time, a time condition is unknown rather than treated as zero.

Automatic deletion is **off by default**, including after an image update or migration. To connect two instances, set the following in each instance's `.env` (loaded by Docker Compose); use a shared random secret of at least 16 characters, distinct IDs, and URLs reachable from the *other container*:

| Instance A | Instance B |
| --- | --- |
| `MINI_INSTANCE_ID=mini-a` | `MINI_INSTANCE_ID=mini-b` |
| `MINI_SYNC_SECRET=<same-long-random-secret>` | `MINI_SYNC_SECRET=<same-long-random-secret>` |
| `MINI_SYNC_PEERS=http://mini-b:8080` | `MINI_SYNC_PEERS=http://mini-a:8080` |

Replace the hostnames with your real peer addresses; `mini-a` and `mini-b` are examples, not Docker Compose service names. Preserve each instance's `/data/instance-id`: on an existing installation the saved ID takes precedence over `MINI_INSTANCE_ID`. Restart both containers after changing their environment. The Storage page shows the actual local ID and whether a peer is configured. Favorites, protections, candidates, conditions, the **new-candidate default rule**, and the global paused/active state are sent as signed events. Video decisions use SHA-256 content identity, so Docker paths may differ without treating hardlinks as copies. Peer delivery is best-effort: if a peer is offline when a change is made, the change is not automatically replayed later; check synchronization before enabling cleanup. Select one owner ID shown on the page, then explicitly enable automation. A legacy `MINI_CLEANUP_OWNER` value is ignored.

The worker runs every ten minutes and requires authentication, configured peer synchronization, a named owner, an enabled deletion switch, a single qBittorrent client and a `torrent` source. It rechecks every associated torrent, paths, file identity and hardlinks immediately before deletion. A per-storage filesystem lock prevents simultaneous workers from deleting the same physical data. Any unavailable client or unverifiable path blocks the item and records the reason. The default Docker Compose media mount is read-only; manual file deletion requires a writable mount, while BitTorrent data deletion is performed by the BitTorrent client.

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
| `MINI_INSTANCE_ID` | persisted in `/data/instance-id` | Distinct instance identity for federation (set before first start) |
| `MINI_SYNC_SECRET` | empty | Shared federation signing secret (at least 16 characters) |
| `MINI_SYNC_PEERS` | empty | Comma-separated, mutually reachable peer base URLs |

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
