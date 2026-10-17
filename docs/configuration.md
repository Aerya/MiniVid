# MiniVid configuration

[← README](../README.md) · [Français](configuration.fr.md)

Common settings live in `.env` and **Maintenance**. Restart with `docker compose up -d` after changing `.env`.

## Multiple sources

Add volumes to the `minivid` service in `docker-compose.yml`:

```yaml
volumes:
  - /mnt/videos:/videos1:ro
  - /mnt/archive:/videos2:ro
  - ./data:/data
  - ./cache:/cache
```

Set the **container paths** and display names in the same order:

```dotenv
MEDIA_DIRS=/videos1|/videos2
MEDIA_NAMES=Videos|Archive
```

Folders named `cross-seed-links` are excluded by default. `MINI_EXCLUDED_DIRS` accepts a comma-separated list of directory names.

## Password protection and data

```dotenv
MINI_USER=your-username
MINI_PASS=your-password
SECRET_KEY=a-long-random-key
```

Generate a key with `openssl rand -hex 32`. The `minivid.sh` launcher already creates one on first start.

Keep **`data/` and `SECRET_KEY`** when updating: client passwords are encrypted with this key. `cache/` holds thumbnails and temporary playback segments. For public access, use an HTTPS reverse proxy and authentication.

## Deletion and cleanup

In **Maintenance → Sources and BitTorrent clients**:

1. Add a qBittorrent or ruTorrent client and test its connection.
2. Associate your sources. The “path seen by the client” must match its exact `content_path` prefix, not the MiniVid mount.
3. Choose a deletion mode per source, then enable the connection and deletion separately.

Direct file deletion needs a `:rw` mount. “Torrent and data” deletion goes through the client. Associated torrents and recognized cross-seed variants are checked before the video leaves the index.

In **Storage**, compare SHA-256 duplicates or review a selection of files. Favorites, protections, hardlinks and unverifiable torrent associations may block deletion. Savings remain estimates with snapshots and reflinks.

On a playback page, choose to **keep**, **protect** or **allow cleanup**, then set conditions. A rule applies only to the exact file version. A cleanup stop threshold must exceed its start threshold: for example, start below 15% free space and stop at 20%.

Automation requires configured federation, one owner, authentication, authorized sources and a compatible qBittorrent client. It stays off until explicitly enabled in **Storage → Cleanup rules**. Unknown seeding time blocks time-based conditions, including with ruTorrent.

## Synchronizing instances

Before first start, set a distinct ID per instance, a shared secret of at least 16 characters, and peer URLs reachable from the containers:

```dotenv
MINI_INSTANCE_ID=mini-a
MINI_SYNC_SECRET=replace-with-a-long-shared-secret
MINI_SYNC_PEERS=http://instance-b-address:8080
```

On B, use `MINI_INSTANCE_ID=mini-b` and A’s address. An existing `data/instance-id` takes precedence over the variable: keep that file.

Favorites and rules synchronize by content fingerprint even when paths differ. Delivery is best effort: an unavailable peer does not automatically receive missed changes later. Check both instances before enabling automation and select only one owner.

## Useful settings

| Variable | Purpose |
| --- | --- |
| `MINIVID_PORT=8080` | Web port published by Docker |
| `MINI_AUTOSCAN=1` | Periodic library refresh |
| `MINI_SCAN_INTERVAL=3600` | Refresh interval in seconds |
| `MINI_ALLOWED_EXT` | Comma-separated allowed extensions |
| `MINI_BANNED_TAGS` | Words excluded from automatic tags |
| `MINI_TRANSCODE=0` | Disable HLS conversion |
| `MINIVID_GPU=cpu` | Run without a GPU |
| `MINIVID_GPU_FALLBACK=1` | Fall back to CPU if the GPU is unavailable |

The supplied Compose prepares GPU access automatically. Its helper accesses the Docker socket and host CDI directories; the main container is not privileged. NVIDIA needs the host driver and NVIDIA Container Toolkit; Intel/AMD uses `/dev/dri`. Review [the Compose file](../docker-compose.yml) before a custom deployment.

## Windows

[`Windows-MiniVid.cmd`](../Windows-MiniVid.cmd) provides an English/French setup for Windows 10/11 x64 with PowerShell 5.1, WSL2 and Docker Desktop, using local or SMB/CIFS folders. It is provided as is and has not been validated on Windows by the maintainer.
