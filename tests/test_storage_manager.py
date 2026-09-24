import os
import tempfile
import unittest

import storage_manager as storage


class StorageManagerTest(unittest.TestCase):
    def test_copies_and_hardlinks_are_separate(self):
        with tempfile.TemporaryDirectory() as root:
            db = os.path.join(root, "storage.db")
            original = os.path.join(root, "original.mkv")
            alias = os.path.join(root, "alias.mkv")
            copy = os.path.join(root, "copy.mkv")
            different = os.path.join(root, "different.mkv")
            with open(original, "wb") as f:
                f.write(b"duplicate content")
            os.link(original, alias)
            with open(copy, "wb") as f:
                f.write(b"duplicate content")
            with open(different, "wb") as f:
                f.write(b"different content")
            paths = {"original": original, "alias": alias, "copy": copy, "different": different}
            storage.inventory_scan(db, [{"id": vid} for vid in paths], paths.__getitem__)
            with storage.connect(db) as con:
                copies, links = storage.duplicate_groups([dict(r) for r in con.execute("SELECT * FROM inventory")])
            self.assertEqual(len(copies), 1)
            self.assertEqual(set(copies[0]["items"]), {"original", "alias", "copy"})
            self.assertEqual([set(group) for group in links], [{"original", "alias"}])
            self.assertEqual(copies[0]["estimated_bytes"], os.stat(copy).st_blocks * 512)

    def test_replacement_file_does_not_inherit_delete_permission(self):
        with tempfile.TemporaryDirectory() as root:
            db = os.path.join(root, "storage.db")
            path = os.path.join(root, "file.mkv")
            with open(path, "wb") as f:
                f.write(b"old")
            rule = storage.set_rule(db, "video", os.stat(path), {"mode": "candidate"})
            self.assertEqual(rule["mode"], "candidate")
            replacement = os.path.join(root, "new.mkv")
            with open(replacement, "wb") as f:
                f.write(b"new")
            os.replace(replacement, path)
            self.assertIsNone(storage.get_rule(db, "video", os.stat(path)))

    def test_every_torrent_must_pass_and_missing_seed_time_fails_closed(self):
        rule = {"ratio": 1.5, "seed_seconds": 86400, "seed_operator": "and"}
        torrents = [{"ratio": 2, "seeding_time": 90000}, {"ratio": 0.3, "seeding_time": 90000}]
        self.assertFalse(storage.seed_ready(torrents, rule))
        rule["seed_operator"] = "or"
        self.assertTrue(storage.seed_ready(torrents, rule))
        torrents[1]["seeding_time"] = None
        self.assertFalse(storage.seed_ready(torrents, rule))

    def test_synced_policy_and_owner_are_disabled_until_explicitly_enabled(self):
        with tempfile.TemporaryDirectory() as root:
            db = os.path.join(root, "storage.db")
            self.assertFalse(storage.settings(db)["enabled"])
            key = "sha256:4:" + "a" * 64
            self.assertTrue(storage.set_synced_policy(db, key, {"mode": "protect"}, 2, "instance-a"))
            self.assertFalse(storage.set_synced_policy(db, key, {"mode": "candidate"}, 1, "instance-b"))
            self.assertEqual(storage.synced_policy(db, key)[0]["mode"], "protect")
            self.assertTrue(storage.set_settings(db, True, "instance-a", 3, "instance-a"))
            self.assertEqual(storage.settings(db)["owner_id"], "instance-a")


if __name__ == "__main__":
    unittest.main()
