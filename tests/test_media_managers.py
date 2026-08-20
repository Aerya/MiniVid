import json
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from media_managers import QBittorrentClient, RutorrentClient, TorrentClientError


class FakeTorrentServer(BaseHTTPRequestHandler):
    deleted = []

    def log_message(self, *_args):
        pass

    def _send(self, payload, content_type="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path)
        if path.path == "/api/v2/app/version":
            return self._send(b"5.1.2", "text/plain")
        if path.path == "/api/v2/torrents/info":
            return self._send([{
                "hash": "abc123",
                "name": "video.mkv",
                "content_path": "/downloads/video.mkv",
                "save_path": "/downloads",
                "added_on": 1700000000,
                "seeding_time": 7200,
                "ratio": 2.5,
                "num_leechs": 3,
                "num_seeds": 4,
                "num_incomplete": 30,
                "num_complete": 40,
                "state": "stalledUP",
            }])
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        data = urllib.parse.parse_qs(self.rfile.read(length).decode())
        if self.path == "/api/v2/auth/login":
            return self._send(b"Ok.", "text/plain")
        if self.path == "/api/v2/torrents/delete":
            self.deleted.append(data)
            return self._send(b"", "text/plain")
        if self.path == "/rutorrent/plugins/httprpc/action.php":
            mode = data.get("mode", [""])[0]
            if mode == "list":
                values = [0] * 35
                values[4] = "video.mkv"
                values[5] = 123
                values[9] = 1000
                values[10] = 2500
                values[17] = 3
                values[18] = 4
                values[21] = 1700000200
                values[25] = "/downloads/video.mkv"
                values[26] = 1700000000
                values[28] = 1
                return self._send({"t": {"DEF456": values}, "cid": 1})
            if mode == "removewithdata":
                self.deleted.append(data)
                return self._send([0])
        self.send_error(404)


class TorrentClientsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeTorrentServer)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        FakeTorrentServer.deleted.clear()

    def test_qbittorrent_metadata_and_delete_with_data(self):
        client = QBittorrentClient(self.base_url, "user", "password")
        metadata = client.metadata("video.mkv", "/downloads")
        self.assertEqual(metadata["torrent_hash"], "abc123")
        self.assertEqual(metadata["seeding_time"], 7200)
        self.assertEqual(metadata["ratio"], 2.5)
        client.delete_with_data("video.mkv", "/downloads")
        self.assertEqual(FakeTorrentServer.deleted[-1]["hashes"], ["abc123"])
        self.assertEqual(FakeTorrentServer.deleted[-1]["deleteFiles"], ["true"])

    def test_qbittorrent_refuses_non_matching_path(self):
        client = QBittorrentClient(self.base_url, "user", "password")
        with self.assertRaises(TorrentClientError):
            client.delete_with_data("other.mkv", "/downloads")
        self.assertEqual(FakeTorrentServer.deleted, [])

    def test_rutorrent_metadata_and_remove_with_data(self):
        client = RutorrentClient(self.base_url + "/rutorrent", "user", "password")
        metadata = client.metadata("video.mkv", "/downloads")
        self.assertEqual(metadata["torrent_hash"], "DEF456")
        self.assertEqual(metadata["ratio"], 2.5)
        client.delete_with_data("video.mkv", "/downloads")
        self.assertEqual(FakeTorrentServer.deleted[-1]["mode"], ["removewithdata"])
        self.assertEqual(FakeTorrentServer.deleted[-1]["hash"], ["DEF456"])


if __name__ == "__main__":
    unittest.main()
