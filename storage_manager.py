"""Inventory and cleanup rules. Database records are tied to a physical file version."""

import hashlib
import json
import os
import sqlite3
import time
from collections import defaultdict
from contextlib import contextmanager


@contextmanager
def connect(db_path):
    db = sqlite3.connect(db_path, timeout=15)
    try:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("""CREATE TABLE IF NOT EXISTS cleanup_rules (
            vid TEXT PRIMARY KEY, identity TEXT NOT NULL, mode TEXT NOT NULL,
            trigger_mode TEXT NOT NULL DEFAULT 'pressure', ratio REAL NOT NULL DEFAULT 1,
            seed_seconds INTEGER NOT NULL DEFAULT 604800, seed_operator TEXT NOT NULL DEFAULT 'and',
            free_below REAL NOT NULL DEFAULT 15, free_until REAL NOT NULL DEFAULT 20,
            updated_at INTEGER NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS playback_stats (
            vid TEXT PRIMARY KEY, starts INTEGER NOT NULL DEFAULT 0,
            completions INTEGER NOT NULL DEFAULT 0, max_percent REAL NOT NULL DEFAULT 0,
            watched_seconds REAL NOT NULL DEFAULT 0, last_played INTEGER NOT NULL DEFAULT 0)""")
        db.execute("""CREATE TABLE IF NOT EXISTS inventory (
            vid TEXT PRIMARY KEY, dev INTEGER NOT NULL, ino INTEGER NOT NULL,
            size INTEGER NOT NULL, allocated INTEGER NOT NULL, links INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL, digest TEXT, scanned_at INTEGER NOT NULL,
            first_seen INTEGER NOT NULL DEFAULT 0)""")
        # These records are deliberately keyed by content, not MiniVid's local
        # root/path id. Different containers can mount the same bytes elsewhere.
        db.execute("""CREATE TABLE IF NOT EXISTS synced_policies (
            content_key TEXT PRIMARY KEY, payload TEXT NOT NULL, revision INTEGER NOT NULL,
            origin TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS cleanup_settings (
            id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL DEFAULT 0,
            owner_id TEXT NOT NULL DEFAULT '', revision INTEGER NOT NULL DEFAULT 0,
            origin TEXT NOT NULL DEFAULT '')""")
        db.execute("INSERT OR IGNORE INTO cleanup_settings(id) VALUES(1)")
        if "first_seen" not in {row[1] for row in db.execute("PRAGMA table_info(inventory)")}:
            db.execute("ALTER TABLE inventory ADD COLUMN first_seen INTEGER NOT NULL DEFAULT 0")
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def identity(stat):
    return f"{stat.st_dev}:{stat.st_ino}:{stat.st_size}:{stat.st_mtime_ns}"


def get_rule(db_path, vid, stat):
    with connect(db_path) as db:
        row = db.execute("SELECT * FROM cleanup_rules WHERE vid=?", (vid,)).fetchone()
    return dict(row) if row and row["identity"] == identity(stat) else None


def set_rule(db_path, vid, stat, data):
    mode = str(data.get("mode", "none"))
    if mode not in ("none", "protect", "candidate"):
        raise ValueError("Mode invalide")
    if mode == "none":
        with connect(db_path) as db:
            db.execute("DELETE FROM cleanup_rules WHERE vid=?", (vid,))
        return None
    trigger = str(data.get("trigger_mode", "pressure"))
    operator = str(data.get("seed_operator", "and"))
    if trigger not in ("pressure", "immediate") or operator not in ("and", "or"):
        raise ValueError("Conditions invalides")
    try:
        ratio = float(data.get("ratio", 1))
        seed = int(data.get("seed_seconds", 604800))
        below = float(data.get("free_below", 15))
        until = float(data.get("free_until", 20))
    except (TypeError, ValueError) as exc:
        raise ValueError("Seuil invalide") from exc
    if not (0 <= ratio <= 1000 and 0 <= seed <= 315360000 and 0 < below < until < 100):
        raise ValueError("Seuil hors limites : seuil de sortie > seuil d'entrée")
    with connect(db_path) as db:
        db.execute("""INSERT OR REPLACE INTO cleanup_rules
            (vid, identity, mode, trigger_mode, ratio, seed_seconds, seed_operator,
             free_below, free_until, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (vid, identity(stat), mode, trigger, ratio, seed, operator, below, until, int(time.time())))
    return get_rule(db_path, vid, stat)


def playback(db_path, vid, *, start=False, complete=False, percent=0, watched=0):
    with connect(db_path) as db:
        db.execute("INSERT OR IGNORE INTO playback_stats(vid) VALUES(?)", (vid,))
        db.execute("""UPDATE playback_stats SET starts=starts+?, completions=completions+?,
            max_percent=max(max_percent, ?), watched_seconds=watched_seconds+?,
            last_played=CASE WHEN ? THEN ? ELSE last_played END WHERE vid=?""",
            (int(start), int(complete), min(100, max(0, float(percent))),
             min(30, max(0, float(watched))), bool(start or watched or complete), int(time.time()), vid))


def _hash(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_key(path, stat=None):
    """Stable logical identity, only returned if the exact file stayed put."""
    stat = stat or os.stat(path)
    digest = _hash(path)
    if identity(os.stat(path)) != identity(stat):
        raise ValueError("Fichier modifié pendant l'empreinte")
    return f"sha256:{stat.st_size}:{digest}"


def settings(db_path):
    with connect(db_path) as db:
        return dict(db.execute("SELECT enabled,owner_id,revision,origin FROM cleanup_settings WHERE id=1").fetchone())


def set_settings(db_path, enabled, owner_id, revision, origin):
    if not isinstance(enabled, bool) or not isinstance(owner_id, str) or len(owner_id) > 120:
        raise ValueError("Paramètres de nettoyage invalides")
    with connect(db_path) as db:
        current = db.execute("SELECT revision,origin FROM cleanup_settings WHERE id=1").fetchone()
        if (revision, origin) < (current[0], current[1]):
            return False
        db.execute("UPDATE cleanup_settings SET enabled=?,owner_id=?,revision=?,origin=? WHERE id=1",
                   (enabled, owner_id.strip(), revision, origin))
    return True


def set_synced_policy(db_path, key, payload, revision, origin):
    if not key.startswith("sha256:") or not isinstance(payload, dict):
        raise ValueError("Décision synchronisée invalide")
    with connect(db_path) as db:
        current = db.execute("SELECT revision,origin FROM synced_policies WHERE content_key=?", (key,)).fetchone()
        if current and (revision, origin) < (current[0], current[1]):
            return False
        db.execute("INSERT OR REPLACE INTO synced_policies(content_key,payload,revision,origin) VALUES(?,?,?,?)",
                   (key, json.dumps(payload, sort_keys=True), revision, origin))
    return True


def synced_policy(db_path, key):
    with connect(db_path) as db:
        row = db.execute("SELECT payload,revision,origin FROM synced_policies WHERE content_key=?", (key,)).fetchone()
    return (json.loads(row[0]), row[1], row[2]) if row else None


def inventory_scan(db_path, entries, path_for):
    """Hash only equal-sized physical candidates; discard results if a file changed."""
    records = []
    sizes = defaultdict(set)
    for item in entries:
        try:
            path = path_for(item["id"])
            st = os.stat(path)
            if not os.path.isfile(path):
                continue
        except (OSError, ValueError, FileNotFoundError):
            continue
        rec = (item["id"], path, st)
        records.append(rec)
        sizes[st.st_size].add((st.st_dev, st.st_ino))
    now = int(time.time())
    valid = set()
    digest_cache = {}
    with connect(db_path) as db:
        previous = {r["vid"]: r for r in db.execute("SELECT * FROM inventory")}
        for vid, path, st in records:
            digest = None
            old = previous.get(vid)
            same_version = bool(old and (old["dev"], old["ino"], old["size"], old["mtime_ns"]) == (
                st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns))
            if len(sizes[st.st_size]) > 1:
                if same_version:
                    digest = old["digest"]
                cache_key = (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns)
                if digest is None and cache_key in digest_cache:
                    digest = digest_cache[cache_key]
                if digest is None:
                    try:
                        digest = _hash(path)
                        if identity(os.stat(path)) != identity(st):
                            digest = None
                    except OSError:
                        digest = None
                if digest is not None:
                    digest_cache[cache_key] = digest
            db.execute("""INSERT OR REPLACE INTO inventory
                (vid,dev,ino,size,allocated,links,mtime_ns,digest,scanned_at,first_seen)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (vid, st.st_dev, st.st_ino, st.st_size,
                 st.st_blocks * 512 if hasattr(st, "st_blocks") else st.st_size,
                 st.st_nlink, st.st_mtime_ns, digest, now,
                 (old["first_seen"] or now) if same_version else now))
            valid.add(vid)
        for vid in previous.keys() - valid:
            db.execute("DELETE FROM inventory WHERE vid=?", (vid,))
    return len(records)


def duplicate_groups(rows):
    """Only verified equal SHA-256 files with distinct inodes count as copies."""
    by_hash = defaultdict(list)
    by_inode = defaultdict(list)
    for row in rows:
        by_inode[(row["dev"], row["ino"])].append(row)
        if row["digest"]:
            by_hash[(row["size"], row["digest"])].append(row)
    copies = []
    for group in by_hash.values():
        physical = {(r["dev"], r["ino"]) for r in group}
        if len(physical) > 1:
            # Advisory only: reflinks, snapshots and sparse files may reclaim less.
            copies.append({"items": [r["vid"] for r in group],
                           "estimated_bytes": sum(max(r["allocated"] for r in group
                                                       if (r["dev"], r["ino"]) == inode)
                                                  for inode in physical)
                           - min(max(r["allocated"] for r in group
                                     if (r["dev"], r["ino"]) == inode) for inode in physical)})
    links = [[r["vid"] for r in group] for group in by_inode.values() if len(group) > 1]
    return copies, links


def seed_ready(torrents, rule):
    """Every associated torrent must qualify; missing seed time never qualifies."""
    if not torrents:
        return False
    for torrent in torrents:
        ratio = float(torrent.get("ratio") or 0) >= rule["ratio"]
        duration = torrent.get("seeding_time")
        duration_ok = duration is not None and int(duration) >= rule["seed_seconds"]
        if not ((ratio and duration_ok) if rule["seed_operator"] == "and" else (ratio or duration_ok)):
            return False
    return True
