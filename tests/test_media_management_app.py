import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
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
        with minivid.storage.connect(minivid.STORAGE_DB) as db:db.execute("DELETE FROM playback_stats WHERE vid=?",(self.vid,))
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
        with mock.patch.object(minivid, "_is_decodable_media", return_value=True):
            response = self.client.get(f"/watch/{self.vid}")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('<details id="media-management"', html)
        details_tag = html.split('<details id="media-management"', 1)[1].split('>', 1)[0]
        self.assertNotIn(" open", details_tag)
        self.assertIn("url.searchParams.set('_mv_refresh'", html)
        self.assertIn("window.location.href = refreshedBrowseUrl();", html)

    def test_maintenance_includes_project_links(self):
        response = self.client.get("/maintenance")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('href="https://github.com/Aerya/MiniVid"', html)
        self.assertIn('href="https://github.com/Aerya/PornScout"', html)

    def test_never_watched_filter_excludes_a_video_marked_unwatched_after_playback(self):
        unseen_name = "never-watched.mkv"
        unseen_path = os.path.join(VIDEO_ROOT, unseen_name)
        with open(unseen_path, "wb") as handle:
            handle.write(b"not-a-real-video")
        try:
            minivid.scan_media()
            self.client.post("/api/played", json={"vid": self.vid, "played": True})
            self.client.post("/api/played", json={"vid": self.vid, "played": False})
            response = self.client.get("/browse?read=never")
            html = response.get_data(as_text=True)
            self.assertNotIn(self.video_name, html)
            self.assertIn(unseen_name, html)
        finally:
            try:
                os.remove(unseen_path)
            except OSError:
                pass
            state = minivid.read_state()
            for key in ("played", "ever_played", "progress"):
                state.get(key, {}).pop(self.vid, None)
            minivid.write_state(state)
            minivid.scan_media()

    def test_favorite_is_exposed_for_the_delete_warning(self):
        self.save_config(deletion_enabled=True)
        self.client.post("/api/fav", json={"vid": self.vid, "fav": True})
        try:
            management = self.client.get(f"/api/media/{self.vid}/management").get_json()
            self.assertTrue(management["favorite"])
            with mock.patch.object(minivid, "_is_decodable_media", return_value=True):
                html = self.client.get(f"/watch/{self.vid}").get_data(as_text=True)
            self.assertIn("mediaManagement.favorite", html)
            self.assertIn("Attention : cette vidéo est dans vos favoris.", html)
        finally:
            self.client.post("/api/fav", json={"vid": self.vid, "fav": False})

    def test_storage_overview_does_not_contact_torrent_clients(self):
        copy_path = os.path.join(VIDEO_ROOT, "overview-copy.mkv")
        with open(copy_path, "wb") as handle:
            handle.write(b"not-a-real-video")
        try:
            self.save_config(deletion_enabled=True, delete_mode="torrent", linked=True)
            minivid.scan_media()
            minivid.storage.inventory_scan(minivid.STORAGE_DB, list(minivid.MEDIA), minivid._storage_path)
            with mock.patch.object(minivid, "_configured_client", side_effect=AssertionError("Unexpected network request")):
                response = self.client.get("/api/storage?sort=oldest")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.get_json()["copies"]), 1)
            self.assertEqual(response.get_json()["copies"][0]["files"][0]["management"], "unknown")
        finally:
            os.remove(copy_path)
            minivid.scan_media()

    def test_read_only_test_instance_rejects_destructive_requests(self):
        self.save_config(deletion_enabled=True, delete_mode="file")
        with mock.patch.dict(os.environ, {"MINI_READ_ONLY_TEST": "1"}):
            for endpoint in ("/api/media/" + self.vid + "/delete", "/api/storage/duplicates/delete",
                             "/api/storage/selection/delete", "/api/storage/automation"):
                response = self.client.post(endpoint, json={"confirmation": self.video_name})
                self.assertEqual(response.status_code, 403, endpoint)
        self.assertTrue(os.path.isfile(self.video_path))

    def test_custom_theme_is_shared_across_application_pages(self):
        response = self.client.post("/api/preferences", json={"theme": "custom", "accent": "#123abc", "background": "#112233"})
        self.assertEqual(response.get_json()["prefs"]["accent"], "#123abc")
        for endpoint in ("/browse", "/storage", "/maintenance"):
            html = self.client.get(endpoint).get_data(as_text=True)
            self.assertIn('data-theme="custom"', html)
            self.assertIn('id="theme-form"', html)
            self.assertIn('href="/logout"', html)
        invalid = self.client.post("/api/preferences", json={"accent": "url(https://example.invalid)"})
        self.assertEqual(invalid.get_json()["prefs"]["accent"], "#d42f67")

    def test_storage_scan_lists_actual_copies_and_bulk_deletes_only_unprotected_copy(self):
        copy_name = "another.mkv"
        copy_path = os.path.join(VIDEO_ROOT, copy_name)
        with open(copy_path, "wb") as handle:
            handle.write(b"not-a-real-video")
        try:
            self.save_config(deletion_enabled=True, delete_mode="file")
            minivid.scan_media()
            response = self.client.get("/storage")
            self.assertEqual(response.status_code, 200)
            minivid.storage.inventory_scan(minivid.STORAGE_DB, list(minivid.MEDIA), minivid._storage_path)
            data = self.client.get("/api/storage").get_json()
            self.assertEqual(len(data["copies"]), 1)
            self.assertEqual(data["copies"][0]["estimated_bytes"], os.stat(copy_path).st_blocks * 512)
            digest = data["copies"][0]["digest"]
            wrong = self.client.post("/api/storage/duplicates/delete", json={
                "digest": digest, "keep": self.vid, "confirmation": "no"})
            self.assertEqual(wrong.status_code, 400)
            self.client.post("/api/fav", json={"vid": minivid.id_for(0, copy_name), "fav": True})
            blocked = self.client.post("/api/storage/duplicates/delete", json={
                "digest": digest, "keep": self.vid, "confirmation": "SUPPRIMER"})
            self.assertEqual(blocked.status_code, 409)
            self.assertTrue(os.path.exists(copy_path))
            self.client.post("/api/fav", json={"vid": minivid.id_for(0, copy_name), "fav": False})
            deleted = self.client.post("/api/storage/duplicates/delete", json={
                "digest": digest, "keep": self.vid, "confirmation": "SUPPRIMER"})
            self.assertEqual(deleted.status_code, 200, deleted.get_json())
            self.assertTrue(os.path.exists(self.video_path))
            self.assertFalse(os.path.exists(copy_path))
        finally:
            if os.path.exists(copy_path):
                os.remove(copy_path)
            minivid.scan_media()

    def test_storage_policy_respects_favorites_and_playback_events(self):
        self.save_config(deletion_enabled=True, delete_mode="torrent", linked=True)
        fake = FakeTorrentClient()
        with mock.patch.object(minivid, "_configured_client", return_value=fake):
            response = self.client.post(f"/api/storage/rule/{self.vid}", json={
                "mode": "candidate", "ratio": 1.5, "seed_seconds": 3600,
                "seed_operator": "and", "trigger_mode": "immediate", "free_below": 15, "free_until": 20})
            self.assertEqual(response.status_code, 200, response.get_json())
            self.assertEqual(response.get_json()["status"], "ready")
        self.client.post(f"/api/playback/{self.vid}", json={"event": "start"})
        self.client.post(f"/api/progress/{self.vid}", json={"progress": 25, "percent": 25, "watched": 10})
        items = self.client.get("/api/storage?filter=abandoned").get_json()["items"]
        self.assertTrue(any(it["id"] == self.vid and it["starts"] >= 1 for it in items))
        self.client.post("/api/fav", json={"vid": self.vid, "fav": True})
        refused = self.client.post(f"/api/storage/rule/{self.vid}", json={"mode": "candidate"})
        self.assertEqual(refused.status_code, 409)
        self.client.post("/api/fav", json={"vid": self.vid, "fav": False})
        self.client.post(f"/api/storage/rule/{self.vid}", json={"mode": "none"})

    def test_owner_cycle_rechecks_seed_before_deletion(self):
        self.save_config(deletion_enabled=True, delete_mode="torrent", linked=True)
        minivid.storage.set_settings(minivid.STORAGE_DB, True, minivid.INSTANCE_ID, 1, minivid.INSTANCE_ID)
        with minivid.storage.connect(minivid.STORAGE_DB) as db:
            db.execute("DELETE FROM playback_stats WHERE vid=?", (self.vid,))
        rule = {"mode": "candidate", "trigger_mode": "immediate", "ratio": 1.5,
                "seed_seconds": 86400, "seed_operator": "or", "free_below": 15, "free_until": 20}
        minivid.storage.set_rule(minivid.STORAGE_DB, self.vid, os.stat(self.video_path), rule)
        fake = FakeTorrentClient(self.video_path)
        with mock.patch.object(minivid, "_configured_client", return_value=fake), \
             mock.patch.object(fake, "metadata_all", return_value=[{"ratio": 0.5, "seeding_time": 100}]) as metadata:
            minivid._cleanup_run_once()
        self.assertTrue(os.path.exists(self.video_path))
        self.assertEqual(FakeTorrentClient.deleted, [])
        with mock.patch.object(minivid, "_configured_client", return_value=fake), \
             mock.patch.object(fake, "metadata_all", return_value=[{"ratio": 1.5, "seeding_time": 100}]):
            with mock.patch.dict(os.environ, {"MINI_READ_ONLY_TEST": "1"}):
                minivid._cleanup_run_once()
            self.assertTrue(os.path.exists(self.video_path))
            self.assertEqual(FakeTorrentClient.deleted, [])
            minivid._cleanup_run_once()
        self.assertFalse(os.path.exists(self.video_path))
        self.assertEqual(len(FakeTorrentClient.deleted), 1)

    def test_signed_policy_sync_matches_content_across_local_paths(self):
        content_key = minivid.storage.content_key(self.video_path)
        event = {"kind": "policy", "content_key": content_key,
                 "value": {"mode": "protect"}, "revision": 100, "origin": "remote-instance"}
        raw = json.dumps(event, separators=(",", ":"), sort_keys=True).encode()
        with mock.patch.object(minivid, "SYNC_SECRET", "s" * 32), \
             mock.patch.object(minivid, "INSTANCE_ID", "local-instance"):
            response = self.client.post("/api/storage/sync", data=raw,
                                        headers={"Content-Type": "application/json",
                                                 "X-MiniVid-Sync": minivid._sync_signature(raw)})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(minivid.storage.get_rule(minivid.STORAGE_DB, self.vid, os.stat(self.video_path))["mode"], "protect")

    def test_automation_cannot_be_enabled_without_federation(self):
        response = self.client.post("/api/storage/automation", json={"enabled": True, "owner_id": minivid.INSTANCE_ID})
        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.get_json()["ok"])

    def test_default_rule_is_saved_and_signed_sync_applies_without_enabling_automation(self):
        with tempfile.TemporaryDirectory() as root, mock.patch.object(minivid, "STORAGE_DB", os.path.join(root, "storage.db")):
            desired = {"ratio": 2, "seed_seconds": 3600, "seed_operator": "or",
                       "trigger_mode": "pressure", "free_below": 12, "free_until": 22}
            with mock.patch.object(minivid, "_emit_storage_event") as emit:
                response = self.client.post("/api/storage/default-rule", json=desired)
            self.assertEqual(response.status_code, 200, response.get_json())
            emit.assert_called_once_with("defaults", "", desired)
            self.assertEqual(self.client.get("/api/storage/default-rule").get_json()["rule"], desired)
            self.assertFalse(minivid.storage.settings(minivid.STORAGE_DB)["enabled"])
            self.save_config(deletion_enabled=True, delete_mode="torrent", linked=True)
            with mock.patch.object(minivid, "_configured_client", return_value=FakeTorrentClient()):
                candidate = self.client.post(f"/api/storage/rule/{self.vid}", json={"mode": "candidate"})
            self.assertEqual(candidate.status_code, 200, candidate.get_json())
            self.assertEqual(candidate.get_json()["rule"]["ratio"], 2)
            self.assertEqual(candidate.get_json()["rule"]["free_until"], 22)
            remote = dict(desired, ratio=3)
            event = {"kind": "defaults", "content_key": "", "value": remote,
                     "revision": 5 * 10**18, "origin": "remote-instance"}
            raw = json.dumps(event, separators=(",", ":"), sort_keys=True).encode()
            with mock.patch.object(minivid, "SYNC_SECRET", "s" * 32):
                result = self.client.post("/api/storage/sync", data=raw,
                                          headers={"X-MiniVid-Sync": minivid._sync_signature(raw)})
            self.assertEqual(result.status_code, 200, result.get_json())
            self.assertEqual(minivid.storage.default_rule(minivid.STORAGE_DB)["ratio"], 3)
            self.assertEqual(minivid.storage.get_rule(minivid.STORAGE_DB, self.vid, os.stat(self.video_path))["ratio"], 2)
            self.assertFalse(minivid.storage.settings(minivid.STORAGE_DB)["enabled"])

    def test_storage_selection_previews_blocked_items_and_checks_file_identity(self):
        second_name = "second.mkv"
        second_path = os.path.join(VIDEO_ROOT, second_name)
        with open(second_path, "wb") as handle:
            handle.write(b"another video")
        try:
            minivid.scan_media()
            second_id = minivid.id_for(0, second_name)
            self.save_config(deletion_enabled=True, delete_mode="file")
            html = self.client.get("/storage").get_data(as_text=True)
            self.assertIn('id="storage-gallery"', html)
            self.assertIn('id="storage-width"', html)
            self.assertIn('id="storage-select-page"', html)
            self.client.post("/api/fav", json={"vid": second_id, "fav": True})
            preview = self.client.post("/api/storage/selection/preview", json={"items": [self.vid, second_id]})
            self.assertEqual(preview.status_code, 200, preview.get_json())
            self.assertEqual(len(preview.get_json()["ready"]), 1)
            self.assertEqual(len(preview.get_json()["blocked"]), 1)
            self.assertEqual(self.client.post("/api/storage/selection/delete", json={
                "items": preview.get_json()["ready"] + [{"id": second_id, "identity": "blocked"}],
                "confirmation": "SUPPRIMER 2"}).status_code, 409)
            self.assertTrue(os.path.exists(self.video_path))
            self.client.post("/api/fav", json={"vid": second_id, "fav": False})
            ready = self.client.post("/api/storage/selection/preview", json={"items": [self.vid]}).get_json()["ready"]
            with open(self.video_path, "ab") as handle:
                handle.write(b"changed")
            changed = self.client.post("/api/storage/selection/delete", json={
                "items": ready, "confirmation": "SUPPRIMER 1"})
            self.assertEqual(changed.status_code, 409)
            self.assertTrue(os.path.exists(self.video_path))
            ready = self.client.post("/api/storage/selection/preview", json={"items": [self.vid]}).get_json()["ready"]
            deleted = self.client.post("/api/storage/selection/delete", json={
                "items": ready, "confirmation": "SUPPRIMER 1"})
            self.assertEqual(deleted.status_code, 200, deleted.get_json())
            self.assertFalse(os.path.exists(self.video_path))
            self.assertTrue(os.path.exists(second_path))
        finally:
            self.client.post("/api/fav", json={"vid": minivid.id_for(0, second_name), "fav": False})
            os.remove(second_path)
            minivid.scan_media()

    def test_corrupted_media_shows_a_clear_error_instead_of_a_player(self):
        with mock.patch.object(minivid, "_is_decodable_media", return_value=False):
            response = self.client.get(f"/watch/{self.vid}")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Ce fichier vidéo est incomplet ou endommagé.", html)
        self.assertNotIn('id="v"', html)

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

    def test_language_preference_persists_and_loads_the_flag_switcher(self):
        response = self.client.post("/api/preferences", json={"lang": "en"})
        self.assertEqual(response.status_code, 200, response.get_json())
        self.assertEqual(response.get_json()["prefs"]["lang"], "en")
        response = self.client.get("/browse")
        html = response.get_data(as_text=True)
        self.assertIn('<html lang="en"', html)
        self.assertIn('src="/static/i18n.js"', html)
        self.client.post("/api/preferences", json={"lang": "fr"})

    def test_avi_flv_and_m2ts_use_hls_without_browser_sniffing(self):
        with minivid.app.test_request_context(), \
             mock.patch.object(minivid, "ALLOW_TRANSCODE", True), \
             mock.patch.object(minivid, "_probe_all", return_value={"vcodec": "h264"}):
            for ext in ("avi", "flv", "m2ts"):
                url, method = minivid._get_best_playback_url("video-id", "/videos1/file." + ext, ext, "")
                self.assertEqual(method, "hls")
                self.assertEqual(url, "/hls/video-id/playlist.m3u8")

    def test_hevc_mp4_uses_hls_when_transcoding_is_enabled(self):
        with minivid.app.test_request_context(), \
             mock.patch.object(minivid, "ALLOW_TRANSCODE", True), \
             mock.patch.object(minivid, "_probe_all", return_value={"vcodec": "hevc"}):
            url, method = minivid._get_best_playback_url("video-id", "/videos1/file.mp4", "mp4", "")
        self.assertEqual(method, "hls")
        self.assertEqual(url, "/hls/video-id/playlist.m3u8")

    def test_hevc_mp4_is_explicit_when_transcoding_is_disabled(self):
        with minivid.app.test_request_context(), \
             mock.patch.object(minivid, "ALLOW_TRANSCODE", False), \
             mock.patch.object(minivid, "_probe_all", return_value={"vcodec": "hevc"}):
            _, method = minivid._get_best_playback_url("video-id", "/videos1/file.mp4", "mp4", "")
        self.assertEqual(method, "unsupported")

    def test_scan_excludes_cross_seed_links_by_default(self):
        cross_seed = os.path.join(VIDEO_ROOT, "cross-seed-links")
        os.makedirs(cross_seed, exist_ok=True)
        linked_video = os.path.join(cross_seed, "duplicate.mp4")
        with open(linked_video, "wb") as handle:
            handle.write(b"not-a-real-video")
        try:
            minivid.scan_media()
            self.assertNotIn(minivid.id_for(0, "cross-seed-links/duplicate.mp4"),
                             {item["id"] for item in minivid.MEDIA})
        finally:
            os.remove(linked_video)
            os.rmdir(cross_seed)

    def test_folder_recent_date_comes_from_its_videos_not_directory_mtime(self):
        folder = os.path.join(VIDEO_ROOT, "old-collection")
        os.makedirs(folder, exist_ok=True)
        video = os.path.join(folder, "old.mp4")
        with open(video, "wb") as handle:
            handle.write(b"not-a-real-video")
        old = 1
        os.utime(self.video_path, (old, old))
        os.utime(video, (old, old))
        try:
            minivid.scan_media()
            with mock.patch.object(minivid, "render_template", return_value="ok") as render:
                response = self.client.get("/browse?smart=1&sort=date")
            self.assertEqual(response.status_code, 200)
            smart_groups = render.call_args.kwargs["smart_groups"]
            today = next((group for group in smart_groups if group["key"] == "today"), None)
            self.assertIsNone(today)
        finally:
            os.remove(video)
            os.rmdir(folder)

    def test_today_group_uses_calendar_day_not_last_twenty_four_hours(self):
        yesterday = (datetime.now().astimezone() - timedelta(days=1)).replace(hour=23, minute=59, second=0, microsecond=0)
        groups = minivid.smart_group_items([{"kind": "video", "mtime": yesterday.timestamp()}])
        self.assertNotIn("today", {group["key"] for group in groups})

    def test_incompatible_containers_are_explicit_when_transcoding_is_disabled(self):
        with minivid.app.test_request_context(), \
             mock.patch.object(minivid, "ALLOW_TRANSCODE", False):
            url, method = minivid._get_best_playback_url("video-id", "/videos1/file.avi", "avi", "")
        self.assertEqual(method, "unsupported")
        self.assertEqual(url, "/stream/video-id")

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


class HardwareTranscodingTest(unittest.TestCase):
    def codec_args(self, *, nvenc=False, vaapi=False):
        with mock.patch.object(minivid, "HAS_NVENC", nvenc), \
             mock.patch.object(minivid, "HAS_VAAPI", vaapi), \
             mock.patch.object(minivid, "_probe_all", return_value={"vcodec": "hevc"}):
            return minivid._vcodec_args("video.mkv")

    def test_cpu_is_the_default_fallback(self):
        self.assertIn("libx264", self.codec_args())

    def test_nvenc_is_preferred_when_available(self):
        self.assertIn("h264_nvenc", self.codec_args(nvenc=True, vaapi=True))

    def test_vaapi_is_used_for_intel_or_amd(self):
        args = self.codec_args(vaapi=True)
        self.assertIn("h264_vaapi", args)
        self.assertIn("/dev/dri/renderD128", args)

    def test_software_fallback_ignores_available_hardware(self):
        with mock.patch.object(minivid, "HAS_NVENC", True), \
             mock.patch.object(minivid, "HAS_VAAPI", True), \
             mock.patch.object(minivid, "_probe_all", return_value={"vcodec": "hevc"}):
            args = minivid._vcodec_args("video.mp4", software=True)
        self.assertIn("libx264", args)


if __name__ == "__main__":
    unittest.main()

class ExternalMetadataTest(unittest.TestCase):
    setUp=MediaManagementApiTest.setUp
    tearDown=MediaManagementApiTest.tearDown
    def test_card_more_count_uses_all_tags_and_watch_tags_are_collapsed(self):
        context=minivid._extension_context(self.vid)
        tags=['semantic'+str(i) for i in range(12)]
        state=minivid._default_state()
        state['utags']={self.vid:tags}
        state['fav']={self.vid:True}
        state['progress']={self.vid:35};state['watch_history']={self.vid:{'watched_seconds':35,'duration':100,'watched_percent':35}}
        minivid.write_state(state)
        minivid.MEDIA[0]['tags']=[]
        page=self.client.get('/browse').get_data(as_text=True)
        self.assertIn('>+8</span>',page)
        watch=self.client.get('/watch/'+self.vid).get_data(as_text=True)
        self.assertIn('<details id="watch-tags"',watch)
        self.assertNotIn('<details id="watch-tags" open',watch)
        self.assertIn('Tags (12)',watch)
        self.assertNotIn('class="playback-badge"',watch)
        entry=minivid._extension_library()[0]
        self.assertEqual(len(entry['tags']),12)
        self.assertTrue(entry['favorite']);self.assertTrue(entry['watched'])

    def test_batch_tag_import_writes_once_and_skips_unchanged_data(self):
        context=minivid._extension_context(self.vid)
        result={'tags':['external'],'_file':{k:context[k] for k in ('size','mtime')}}
        minivid.write_state(minivid._default_state())
        records=[{'id':self.vid,'result':result},{'id':self.vid,'result':result}]
        with mock.patch.object(minivid,'write_state',wraps=minivid.write_state) as save:
            minivid._import_extension_batch(records)
            self.assertEqual(save.call_count,1)
            minivid._import_extension_batch(records)
            self.assertEqual(save.call_count,1)

    def test_library_enrichment_includes_scanned_videos(self):
        contexts=minivid._extension_contexts()
        self.assertIn(self.vid,[item["id"] for item in contexts])

    def test_external_tags_preserve_manual_tags_and_ignore_replaced_files(self):
        state=minivid._default_state();state['utags']={self.vid:['manual']};minivid.write_state(state)
        context=minivid._extension_context(self.vid)
        result={'tags':['external'],'provider':'example','_file':{k:context[k] for k in ('size','mtime')}}
        minivid._import_extension_metadata(self.vid,context,result)
        state=minivid.read_state()
        self.assertEqual(state['utags'][self.vid],['manual'])
        self.assertEqual(minivid._effective_user_tags(state)[self.vid],['manual','external'])
        state['external_tags'][self.vid]['mtime']+=1
        self.assertEqual(minivid._effective_user_tags(state)[self.vid],['manual'])

class ReadingProgressTest(unittest.TestCase):
    tearDown = MediaManagementApiTest.tearDown

    def setUp(self):
        MediaManagementApiTest.setUp(self)
        minivid.write_state(minivid._default_state())

    def test_effective_thresholds_ignore_seeks_and_keep_manual_marks(self):
        for watched,status in ((0,'unread'),(29,'unread'),(1,'in_progress'),(30,'in_progress'),(9,'in_progress'),(1,'read')):
            response=self.client.post('/api/progress/'+self.vid,json={'progress':99,'duration':100,'watched':watched})
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json['reading_status'],status)
        self.assertEqual(self.client.post('/api/progress/'+self.vid,json={'progress':1,'duration':100}).json['reading_status'],'read')
        self.client.post('/api/played',json={'vid':self.vid,'played':False})
        self.assertEqual(self.client.post('/api/progress/'+self.vid,json={'progress':99,'duration':100,'watched':10}).json['reading_status'],'unread')

    def test_ended_or_percent_field_cannot_fake_effective_playback(self):
        self.client.post('/api/playback/'+self.vid,json={'event':'complete'})
        result=self.client.post('/api/progress/'+self.vid,json={'progress':100,'duration':100,'percent':100,'watched':0}).json
        self.assertEqual(result['reading_status'],'unread')
        self.assertEqual(result['watched_percent'],0)
        self.assertEqual(self.client.post('/api/progress/'+self.vid,json={'progress':100,'duration':100,'watched':10000}).json['watched_percent'],30)

    def test_migration_uses_measured_time_not_saved_position(self):
        state=minivid.read_state();state['watch_history']={self.vid:{'duration':100,'percent':99,'completed':True}}
        minivid.write_state(state)
        with minivid.storage.connect(minivid.STORAGE_DB) as db:db.execute('INSERT INTO playback_stats(vid,watched_seconds) VALUES(?,?)',(self.vid,35))
        minivid._migrate_effective_reading()
        migrated=minivid.read_state()
        self.assertEqual(minivid._reading_status(migrated,self.vid),'in_progress')
        self.assertEqual(migrated['watch_history'][self.vid]['watched_percent'],35)
        self.assertEqual(migrated['watch_history'][self.vid]['percent'],99)
        minivid._migrate_effective_reading()
        self.assertEqual(minivid.read_state(),migrated)

    def test_panel_is_optional_and_history_is_sorted_by_real_activity(self):
        self.client.post('/api/progress/'+self.vid,json={'progress':35,'duration':100,'watched':30})
        page=self.client.get('/browse').get_data(as_text=True)
        self.assertNotIn('class="reading-card"',page)
        self.client.post('/api/preferences',json={'history_panel':'in_progress'})
        page=self.client.get('/browse').get_data(as_text=True)
        self.assertIn('class="reading-card"',page);self.assertIn('En cours',page)
        page=self.client.get('/browse?read=in_progress').get_data(as_text=True)
        self.assertIn('data-vid="'+self.vid+'"',page)
        self.assertNotIn('data-vid="'+self.vid+'"',self.client.get('/browse?read=read').get_data(as_text=True))

    def test_dismiss_resume_preserves_history_and_can_be_undone(self):
        self.client.post('/api/progress/'+self.vid,json={'progress':35,'duration':100,'watched':30})
        before=minivid.read_state()
        self.assertTrue(minivid._recent_reading(before,'in_progress'))
        response=self.client.post('/api/resume/'+self.vid,json={'dismissed':True})
        self.assertEqual(response.status_code,200)
        after=minivid.read_state()
        self.assertEqual(after['progress'],before['progress'])
        self.assertEqual(after['watch_history'],before['watch_history'])
        self.assertEqual(minivid._reading_status(after,self.vid),'in_progress')
        self.assertEqual(minivid._recent_reading(after,'in_progress'),[])
        self.assertEqual(minivid._recent_reading(after,'both'),[])
        self.assertTrue(minivid._recent_reading(after,'recent'))
        self.assertTrue(os.path.exists(self.video_path))
        self.client.post('/api/resume/'+self.vid,json={'dismissed':False})
        self.assertTrue(minivid._recent_reading(minivid.read_state(),'in_progress'))
        self.client.post('/api/resume/'+self.vid,json={'dismissed':True})
        self.client.post('/api/playback/'+self.vid,json={'event':'start'})
        self.assertTrue(minivid._recent_reading(minivid.read_state(),'in_progress'))

    def test_resume_requires_auth_valid_video_and_boolean(self):
        self.assertEqual(self.client.post('/api/resume/missing',json={'dismissed':True}).status_code,404)
        self.assertEqual(self.client.post('/api/resume/'+self.vid,json={'dismissed':'false'}).status_code,400)
        self.client.post('/logout')
        with self.client.session_transaction() as session:session.clear()
        self.assertEqual(self.client.post('/api/resume/'+self.vid,json={'dismissed':True}).status_code,401)

    def test_progress_rejects_unknown_video_and_invalid_numbers(self):
        self.assertEqual(self.client.post('/api/progress/missing',json={'progress':20}).status_code,404)
        self.assertEqual(self.client.post('/api/progress/'+self.vid,json={'progress':'invalid'}).status_code,400)

class LibraryIdentityAndHomeTest(unittest.TestCase):
    def tearDown(self):
        minivid.write_state(minivid._default_state())
        MediaManagementApiTest.tearDown(self)
    def setUp(self):
        MediaManagementApiTest.setUp(self)
        minivid.write_state(minivid._default_state())
    def test_hardlink_aliases_are_verified_and_copies_are_excluded(self):
        import shutil
        directory=os.path.join(VIDEO_ROOT,'cross-seed-links');os.makedirs(directory,exist_ok=True)
        true_alias=os.path.join(directory,'different-name.mkv');copy=os.path.join(directory,'copy.mkv');symlink=os.path.join(directory,'symlink.mkv')
        try:
            os.link(self.video_path,true_alias);shutil.copy2(self.video_path,copy);os.symlink(self.video_path,symlink)
            minivid._EXTENSION_ALIASES['at']=0
            with mock.patch.object(minivid.time,'monotonic',return_value=10):
                ctx=minivid._extension_context(self.vid)
            self.assertEqual(ctx['aliases'],['cross-seed-links/different-name.mkv'])
            self.assertEqual(len(ctx['physical_key']),64)
        finally:
            for name in (true_alias,copy,symlink):os.unlink(name)
            os.rmdir(directory);minivid._EXTENSION_ALIASES['at']=0
    def test_navigation_is_shared_on_all_application_pages(self):
        with mock.patch.object(minivid, '_is_decodable_media', return_value=True):
            for path in ('/home','/browse','/watch/'+self.vid,'/storage','/maintenance'):
                response=self.client.get(path)
                self.assertEqual(response.status_code,200,path)
                page=response.get_data(as_text=True)
                self.assertEqual(page.count('id="library-controls"'),1,path)
                self.assertIn('id="filtersDropdownBtn"',page,path)
                self.assertIn('href="/home">Accueil</a>',page,path)
                self.assertIn('>Favoris</a>',page,path)
                self.assertIn('>Collections</a>',page,path)
                self.assertIn('/static/topbar.js',page,path)

    def test_home_preserves_library_and_resume_access(self):
        state=minivid.read_state();state['fav']={self.vid:True};minivid.write_state(state)
        self.client.post('/api/progress/'+self.vid,json={'progress':25,'duration':100})
        response=self.client.get('/home');self.assertEqual(response.status_code,200)
        page=response.get_data(as_text=True)
        self.assertIn('Reprendre',page);self.assertIn('Mes favoris',page);self.assertIn(self.vid,page)
        self.assertEqual(self.client.get('/').location,'/home')

class IgnoredTagReviewTest(unittest.TestCase):
    def setUp(self):
        MediaManagementApiTest.setUp(self)
        minivid.write_state(minivid._default_state())
        minivid._invalidate_banned_cache()

    def tearDown(self):
        minivid.write_state(minivid._default_state())
        minivid._invalidate_banned_cache()
        MediaManagementApiTest.tearDown(self)

    def test_suggestions_count_videos_once_and_preserve_semantic_tags(self):
        state=minivid.read_state()
        state['utags']={self.vid:['1080p','HEVC','hevc','portrait','popular subject']}
        minivid.write_state(state)
        minivid.MEDIA[0]['tags']=['hevc']
        before=minivid.read_state()
        result=self.client.get('/api/banned_tags/review').json
        rows={row['tag']:row for row in result['items']}
        self.assertEqual(rows['hevc']['count'],1)
        self.assertIn('1080p',rows)
        self.assertNotIn('portrait',rows)
        self.assertNotIn('popular subject',rows)
        self.assertEqual(minivid.read_state(),before)
        all_tags=self.client.get('/api/banned_tags/review?view=all&q=popular').json
        self.assertEqual([row['tag'] for row in all_tags['items']],['popular subject'])

    def test_first_save_preserves_compose_and_restore_can_override_empty_list(self):
        with mock.patch.dict(os.environ,{'MINI_BANNED_TAGS':'existing,mp4'}):
            minivid._invalidate_banned_cache()
            self.assertEqual(set(minivid.get_banned_tags()),{'existing','mp4'})
            response=self.client.post('/api/banned_tags/review',json={'action':'ignore','tags':[' HEVC ']})
            self.assertEqual(set(response.json['tags']),{'existing','mp4','hevc'})
            self.assertEqual(minivid._display_tags(['mp4','hevc','portrait']),['portrait'])
            response=self.client.post('/api/banned_tags/review',json={'action':'restore','tags':['existing','mp4','hevc']})
            self.assertEqual(response.json['tags'],[])
            self.assertEqual(minivid.get_banned_tags(),frozenset())
            self.assertEqual(self.client.get('/api/banned_tags').json['source'],'ui')
            self.assertEqual(self.client.delete('/api/banned_tags').json['source'],'env')
            self.assertEqual(set(minivid.get_banned_tags()),{'existing','mp4'})

    def test_ignoring_tags_is_reversible_for_cards_and_companion(self):
        state=minivid.read_state();state['utags']={self.vid:['hevc','portrait']};minivid.write_state(state)
        self.client.post('/api/banned_tags/review',json={'action':'ignore','tags':['hevc']})
        entry=next(row for row in minivid._extension_library() if row['id']==self.vid)
        self.assertEqual(entry['tags'],['portrait'])
        self.assertEqual(minivid.read_state()['utags'][self.vid],['hevc','portrait'])
        self.client.post('/api/banned_tags/review',json={'action':'restore','tags':['hevc']})
        entry=next(row for row in minivid._extension_library() if row['id']==self.vid)
        self.assertEqual(entry['tags'],['hevc','portrait'])

    def test_rescan_preserves_original_filename_tags_for_restore(self):
        self.client.post('/api/banned_tags/review',json={'action':'ignore','tags':['test']})
        minivid.scan_media()
        self.assertIn('test',[t.lower() for t in minivid.MEDIA[0]['tags']])
        self.assertNotIn('test',[t.lower() for t in minivid._display_tags(minivid.MEDIA[0]['tags'])])
        self.client.post('/api/banned_tags/review',json={'action':'restore','tags':['test']})
        self.assertIn('test',[t.lower() for t in minivid._display_tags(minivid.MEDIA[0]['tags'])])

    def test_validation_auth_and_pagination(self):
        self.assertEqual(self.client.post('/api/banned_tags/review',json={'action':'ignore','tags':[23]}).status_code,400)
        state=minivid.read_state();state['utags']={self.vid:['subject '+str(i) for i in range(65)]};minivid.write_state(state)
        result=self.client.get('/api/banned_tags/review?view=all&q=subject&page=2').json
        self.assertEqual(result['page'],2);self.assertEqual(len(result['items']),15)
        self.assertIn('/home',self.client.get('/browse').get_data(as_text=True))
        with self.client.session_transaction() as session:session.clear()
        self.assertEqual(self.client.get('/api/banned_tags/review').status_code,403)
        self.assertEqual(self.client.post('/api/banned_tags/review',json={'action':'ignore','tags':['hevc']}).status_code,403)
