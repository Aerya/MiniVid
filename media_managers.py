"""Clients BitTorrent et association sécurisée entre torrents et fichiers MiniVid."""

from __future__ import annotations

import base64
import http.cookiejar
import json
import posixpath
import urllib.error
import urllib.parse
import urllib.request


class TorrentClientError(RuntimeError):
    pass


def _clean_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise TorrentClientError("URL du client invalide")
    return url


def _client_path(root: str, rel: str) -> str:
    root = "/" + (root or "").strip().strip("/")
    rel = (rel or "").replace("\\", "/").lstrip("/")
    path = posixpath.normpath(posixpath.join(root, rel))
    if path != root and not path.startswith(root.rstrip("/") + "/"):
        raise TorrentClientError("Chemin vidéo hors de la source configurée")
    return path


class _HttpClient:
    def __init__(self, url: str, username: str = "", password: str = "", timeout: int = 10):
        self.url = _clean_url(url)
        self.username = username or ""
        self.password = password or ""
        self.timeout = max(2, min(30, int(timeout)))
        self.cookies = http.cookiejar.CookieJar()
        handlers = [urllib.request.HTTPCookieProcessor(self.cookies)]
        if self.username:
            password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None, self.url, self.username, self.password)
            handlers.append(urllib.request.HTTPBasicAuthHandler(password_mgr))
        self.opener = urllib.request.build_opener(*handlers)

    def request(self, path: str, data: dict | None = None):
        body = None
        headers = {"Accept": "application/json", "User-Agent": "MiniVid/2.1"}
        if data is not None:
            body = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = urllib.request.Request(self.url + path, data=body, headers=headers)
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                payload = response.read()
                return response.status, payload, response.headers
        except urllib.error.HTTPError as exc:
            detail = exc.read(300).decode("utf-8", "replace").strip()
            raise TorrentClientError(f"Client HTTP {exc.code}: {detail or exc.reason}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise TorrentClientError(f"Client inaccessible: {exc}") from exc


class QBittorrentClient(_HttpClient):
    kind = "qbittorrent"

    def login(self):
        status, payload, _ = self.request(
            "/api/v2/auth/login",
            {"username": self.username, "password": self.password},
        )
        if status != 200 or payload.decode("utf-8", "replace").strip() != "Ok.":
            raise TorrentClientError("Authentification qBittorrent refusée")

    def _json(self, path: str):
        _, payload, _ = self.request(path)
        try:
            return json.loads(payload.decode("utf-8"))
        except Exception as exc:
            raise TorrentClientError("Réponse JSON qBittorrent invalide") from exc

    def test(self):
        self.login()
        _, payload, _ = self.request("/api/v2/app/version")
        return {"ok": True, "version": payload.decode("utf-8", "replace").strip()}

    def _find_torrent(self, rel: str, client_root: str):
        self.login()
        target = _client_path(client_root, rel)
        torrents = self._json("/api/v2/torrents/info")
        exact = []
        possible = []
        for torrent in torrents if isinstance(torrents, list) else []:
            content_path = posixpath.normpath(str(torrent.get("content_path") or ""))
            if content_path == target:
                exact.append(torrent)
                continue
            if content_path and target.startswith(content_path.rstrip("/") + "/"):
                possible.append(torrent)
            elif posixpath.basename(target) == str(torrent.get("name") or ""):
                possible.append(torrent)
        if len(exact) == 1:
            return exact[0], target
        if len(exact) > 1:
            raise TorrentClientError("Plusieurs torrents correspondent exactement au fichier")

        verified = []
        for torrent in possible:
            info_hash = str(torrent.get("hash") or "")
            if not info_hash:
                continue
            files = self._json("/api/v2/torrents/files?" + urllib.parse.urlencode({"hash": info_hash}))
            save_path = posixpath.normpath(str(torrent.get("save_path") or ""))
            for item in files if isinstance(files, list) else []:
                candidate = posixpath.normpath(posixpath.join(save_path, str(item.get("name") or "")))
                if candidate == target:
                    verified.append(torrent)
                    break
        if len(verified) == 1:
            return verified[0], target
        if len(verified) > 1:
            raise TorrentClientError("Plusieurs torrents contiennent ce fichier")
        raise TorrentClientError("Aucun torrent ne correspond exactement à cette vidéo")

    def metadata(self, rel: str, client_root: str):
        torrent, target = self._find_torrent(rel, client_root)
        return {
            "client_type": self.kind,
            "torrent_hash": str(torrent.get("hash") or ""),
            "torrent_name": str(torrent.get("name") or ""),
            "target_path": target,
            "added_on": int(torrent.get("added_on") or 0),
            "seeding_time": int(torrent.get("seeding_time") or 0),
            "ratio": float(torrent.get("ratio") or 0),
            "peers_connected": int(torrent.get("num_leechs") or 0),
            "seeds_connected": int(torrent.get("num_seeds") or 0),
            "peers_total": int(torrent.get("num_incomplete") or 0),
            "seeds_total": int(torrent.get("num_complete") or 0),
            "state": str(torrent.get("state") or ""),
        }

    def delete_with_data(self, rel: str, client_root: str):
        torrent, _ = self._find_torrent(rel, client_root)
        info_hash = str(torrent.get("hash") or "")
        if not info_hash:
            raise TorrentClientError("Hash qBittorrent manquant")
        status, _, _ = self.request(
            "/api/v2/torrents/delete",
            {"hashes": info_hash, "deleteFiles": "true"},
        )
        if status != 200:
            raise TorrentClientError("Suppression qBittorrent refusée")
        return {"torrent_hash": info_hash, "torrent_name": str(torrent.get("name") or "")}


class RutorrentClient(_HttpClient):
    kind = "rutorrent"

    @property
    def action_path(self):
        parsed = urllib.parse.urlsplit(self.url)
        if parsed.path.endswith("/plugins/httprpc/action.php"):
            return ""
        return "/plugins/httprpc/action.php"

    def _action(self, fields: list[tuple[str, str]]):
        encoded = urllib.parse.urlencode(fields).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "MiniVid/2.1",
        }
        if self.username:
            token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
            headers["Authorization"] = "Basic " + token
        req = urllib.request.Request(self.url + self.action_path, data=encoded, headers=headers)
        try:
            with self.opener.open(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise TorrentClientError(f"ruTorrent HTTP {exc.code}") from exc
        except Exception as exc:
            raise TorrentClientError(f"Réponse ruTorrent invalide: {exc}") from exc

    def _list(self):
        result = self._action([("mode", "list"), ("cid", "0")])
        torrents = result.get("t", {}) if isinstance(result, dict) else {}
        parsed = []
        for info_hash, values in torrents.items():
            if not isinstance(values, list) or len(values) < 35:
                continue
            parsed.append({
                "hash": info_hash,
                "name": values[4],
                "size": values[5],
                "uploaded": values[9],
                "ratio_raw": values[10],
                "peers_connected": values[17],
                "seeds_connected": values[18],
                "state_changed": values[21],
                "base_path": values[25],
                "creation_date": values[26],
                "active": values[28],
            })
        return parsed

    def test(self):
        torrents = self._list()
        return {"ok": True, "version": "ruTorrent", "torrent_count": len(torrents)}

    def _find_torrent(self, rel: str, client_root: str):
        target = _client_path(client_root, rel)
        matches = [t for t in self._list() if posixpath.normpath(str(t.get("base_path") or "")) == target]
        if len(matches) != 1:
            if not matches:
                raise TorrentClientError("Aucun torrent ruTorrent ne correspond exactement à cette vidéo")
            raise TorrentClientError("Plusieurs torrents ruTorrent correspondent à cette vidéo")
        return matches[0], target

    def metadata(self, rel: str, client_root: str):
        torrent, target = self._find_torrent(rel, client_root)
        ratio_raw = float(torrent.get("ratio_raw") or 0)
        state_changed = int(torrent.get("state_changed") or 0)
        return {
            "client_type": self.kind,
            "torrent_hash": str(torrent.get("hash") or ""),
            "torrent_name": str(torrent.get("name") or ""),
            "target_path": target,
            # La liste standard ruTorrent n'expose pas la date d'ajout au client.
            # Ne pas présenter la date de création du .torrent comme un ajout.
            "added_on": 0,
            "torrent_created_on": int(torrent.get("creation_date") or 0),
            "seeding_time": 0,
            "ratio": ratio_raw / 1000.0,
            "peers_connected": int(torrent.get("peers_connected") or 0),
            "seeds_connected": int(torrent.get("seeds_connected") or 0),
            "peers_total": 0,
            "seeds_total": 0,
            "state": "active" if int(torrent.get("active") or 0) else "stopped",
            "state_changed": state_changed,
        }

    def delete_with_data(self, rel: str, client_root: str):
        torrent, _ = self._find_torrent(rel, client_root)
        info_hash = str(torrent.get("hash") or "")
        result = self._action([
            ("mode", "removewithdata"),
            ("hash", info_hash),
            ("v", "1"),
        ])
        if result is False or result is None:
            raise TorrentClientError("Suppression ruTorrent refusée")
        return {"torrent_hash": info_hash, "torrent_name": str(torrent.get("name") or "")}


def make_torrent_client(config: dict, password: str):
    cls = QBittorrentClient if config.get("type") == "qbittorrent" else RutorrentClient
    return cls(
        config.get("url", ""),
        config.get("username", ""),
        password,
        config.get("timeout", 10),
    )
