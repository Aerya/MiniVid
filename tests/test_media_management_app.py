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
             mock.patch.object(minivid, "ALLOW_TRANSCODE", True):
            for ext in ("avi", "flv", "m2ts"):
                url, method = minivid._get_best_playback_url("video-id", "/videos1/file." + ext, ext, "")
                self.assertEqual(method, "hls")
                self.assertEqual(url, "/hls/video-id/playlist.m3u8")

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


if __name__ == "__main__":
    unittest.main()
