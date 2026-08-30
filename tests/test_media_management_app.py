import json
import os
import tempfile
import unittest
from unittest import mock


TEST_ROOT = tempfile.TemporaryDirectory()
VIDEO_ROOT = os.path.join(TEST_ROOT.name, "videos")
DATA_ROOT = os.path.join(TEST_ROOT.name, "data")
CACHE_ROOT = os.path.join(TEST_ROOT.name, "cache")
os.makedirs(VIDEO_ROOT)
os.makedirs(DATA_ROOT)
os.makedirs(CACHE_ROOT)
os.environ.update({
    "MEDIA_DIRS": VIDEO_ROOT,
    "MEDIA_NAMES": "Tests",
    "DATA_DIR": DATA_ROOT,
    "THUMB_DIR": CACHE_ROOT,
    "MINI_USER": "admin",
    "MINI_PASS": "test-password",
    "SECRET_KEY": "stable-test-key",
    "MINI_AUTOSCAN": "0",
    "MINI_TRANSCODE": "0",
})

import app as minivid  # noqa: E402


class FakeTorrentClient:
    deleted = []

    def __init__(self, file_path=None):
        self.file_path = file_path

    def metadata(self, rel, client_root):
        return {
            "client_type": "qbittorrent",
            "torrent_hash": "abc",
            "torrent_name": rel,
            "added_on": 1700000000,
            "seeding_time": 3600,
            "ratio": 1.5,
            "peers_connected": 2,
            "seeds_connected": 3,
            "peers_total": 4,
            "seeds_total": 5,
            "state": "stalledUP",
        }

    def metadata_all(self, rel, client_root, expected_size=None):
        return [self.metadata(rel, client_root)]

    def delete_with_data(self, rel, client_root, expected_size=None):
        self.deleted.append((rel, client_root, expected_size))
        if self.file_path:
            os.remove(self.file_path)
        return {"torrent_hashes": ["abc"], "torrent_names": [rel], "torrent_count": 1}


class MediaManagementApiTest(unittest.TestCase):
    def setUp(self):
        self.video_name = "video-test.mkv"
        self.video_path = os.path.join(VIDEO_ROOT, self.video_name)
        with open(self.video_path, "wb") as handle:
            handle.write(b"not-a-real-video")
        minivid.scan_media()
        self.vid = minivid.id_for(0, self.video_name)
        self.client = minivid.app.test_client()
        self.client.post("/login", data={"username": "admin", "password": "test-password"})
        FakeTorrentClient.deleted.clear()
        try:
            os.remove(minivid.MEDIA_MANAGERS_FILE)
        except OSError:
            pass

    def tearDown(self):
        try:
            os.remove(self.video_path)
        except OSError:
            pass

    def save_config(self, *, deletion_enabled, delete_mode="file", linked=False):
        clients = []
        client_id = "client_12345678"
        if linked:
            clients = [{
                "id": client_id,
                "name": "qBittorrent test",
                "type": "qbittorrent",
                "url": "http://qbit.test:8080",
                "username": "user",
                "password": "secret-value",
            }]
        response = self.client.post("/api/settings/media-managers", json={
            "torrent_integration_enabled": linked,
            "deletion_enabled": deletion_enabled,
            "clients": clients,
            "sources": {
                "0": {
                    "client_id": client_id if linked else "",
                    "client_root": "/downloads",
                    "delete_mode": delete_mode,
                }
            },
        })
        self.assertEqual(response.status_code, 200, response.get_json())

    def test_password_is_encrypted_and_never_returned(self):
        self.save_config(deletion_enabled=False, delete_mode="torrent", linked=True)
        with open(minivid.MEDIA_MANAGERS_FILE, encoding="utf-8") as handle:
            persisted = handle.read()
        self.assertNotIn("secret-value", persisted)
        public = self.client.get("/api/settings/media-managers").get_json()
        self.assertTrue(public["clients"][0]["has_password"])
        self.assertNotIn("password", public["clients"][0])

    def test_global_delete_switch_blocks_file_removal(self):
        self.save_config(deletion_enabled=False)
        management = self.client.get(f"/api/media/{self.vid}/management").get_json()
        self.assertEqual(management["name"], self.video_name)
        self.assertIsNone(management["torrent_client"])
        response = self.client.post(
            f"/api/media/{self.vid}/delete",
            json={"confirmation": self.video_name},
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(os.path.exists(self.video_path))

    def test_wrong_confirmation_blocks_file_removal(self):
        self.save_config(deletion_enabled=True)
        response = self.client.post(
            f"/api/media/{self.vid}/delete",
            json={"confirmation": "wrong.mkv"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(os.path.exists(self.video_path))

    def test_file_delete_removes_file_and_index_entry(self):
        self.save_config(deletion_enabled=True)
        response = self.client.post(
            f"/api/media/{self.vid}/delete",
            json={"confirmation": self.video_name},
        )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertFalse(os.path.exists(self.video_path))
        self.assertFalse(any(item["id"] == self.vid for item in minivid.MEDIA))

    def test_torrent_metadata_and_delete_use_associated_client(self):
        self.save_config(deletion_enabled=True, delete_mode="torrent", linked=True)
        fake = FakeTorrentClient(self.video_path)
        with mock.patch.object(minivid, "_configured_client", return_value=fake):
            metadata = self.client.get(f"/api/media/{self.vid}/management")
            self.assertEqual(metadata.status_code, 200)
            management = metadata.get_json()
            self.assertEqual(management["name"], self.video_name)
            self.assertEqual(management["torrent"]["ratio"], 1.5)
            self.assertEqual(len(management["torrents"]), 1)
            self.assertEqual(management["torrent_client"], {
                "name": "qBittorrent test",
                "type": "qbittorrent",
                "url": "http://qbit.test:8080",
            })
            self.assertNotIn("username", management["torrent_client"])
            response = self.client.post(
                f"/api/media/{self.vid}/delete",
                json={"confirmation": self.video_name},
            )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(FakeTorrentClient.deleted, [(self.video_name, "/downloads", len(b"not-a-real-video"))])

    def test_torrent_delete_keeps_index_when_file_still_exists(self):
        self.save_config(deletion_enabled=True, delete_mode="torrent", linked=True)
        fake = FakeTorrentClient()
        with mock.patch.object(minivid, "_configured_client", return_value=fake), \
             mock.patch.object(minivid.time, "sleep", return_value=None):
            response = self.client.post(
                f"/api/media/{self.vid}/delete",
                json={"confirmation": self.video_name},
            )
        self.assertEqual(response.status_code, 502, response.get_json())
        self.assertTrue(os.path.exists(self.video_path))
        self.assertTrue(any(item["id"] == self.vid for item in minivid.MEDIA))

    def test_configuration_requires_authenticated_session(self):
        anonymous = minivid.app.test_client()
        response = anonymous.get("/api/settings/media-managers")
        self.assertEqual(response.status_code, 403)

    def test_media_management_panel_is_collapsed_by_default(self):
        response = self.client.get(f"/watch/{self.vid}")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('<details id="media-management"', html)
        details_tag = html.split('<details id="media-management"', 1)[1].split('>', 1)[0]
        self.assertNotIn(" open", details_tag)
        self.assertIn("url.searchParams.set('_mv_refresh'", html)
        self.assertIn("window.location.href = refreshedBrowseUrl();", html)

    def test_browse_page_persists_and_restores_scroll_position(self):
        response = self.client.get("/browse?root=0&sort=date")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Cache-Control"), "no-store, max-age=0")
        html = response.get_data(as_text=True)
        self.assertIn("history.scrollRestoration = 'manual'", html)
        self.assertIn("browseUrl.searchParams.delete('_mv_refresh')", html)
        self.assertIn("history.replaceState(history.state, '', stableBrowseUrl)", html)
        self.assertIn("window.addEventListener('pagehide', saveScroll)", html)
        self.assertIn("window.setTimeout(() => window.scrollTo(0, target), 150)", html)

    def test_forced_browse_refresh_rescans_media(self):
        with mock.patch.object(minivid, "scan_media") as scan:
            response = self.client.get("/browse?root=0&_mv_refresh=123")
        self.assertEqual(response.status_code, 200)
        scan.assert_called_once_with()

    def test_new_unsaved_client_can_be_tested(self):
        candidate = {
            "id": "client_87654321",
            "name": "qBittorrent direct",
            "type": "qbittorrent",
            "url": "http://qbit.test:8080",
            "username": "user",
            "password": "secret-value",
        }
        tested_client = mock.Mock()
        tested_client.test.return_value = {"ok": True, "version": "v5.1.0"}
        with mock.patch.object(minivid, "make_torrent_client", return_value=tested_client) as factory:
            response = self.client.post(
                "/api/settings/media-managers/test/client_87654321",
                json={"client": candidate},
            )
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["version"], "v5.1.0")
        self.assertEqual(factory.call_args.args[1], "secret-value")
        self.assertFalse(os.path.exists(minivid.MEDIA_MANAGERS_FILE))


if __name__ == "__main__":
    unittest.main()
