"""A blocked video probe must not prevent the HTTP socket from opening."""
import os
import http.cookiejar
import json
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import urllib.parse


class StartupTest(unittest.TestCase):
    def test_login_available_while_initial_video_validation_is_blocked(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'videos').mkdir()
            (root/'videos'/'ready.mp4').write_bytes(b'validated probe fixture')
            (root/'videos'/'sub').mkdir()
            (root/'videos'/'sub'/'pending.mp4').write_bytes(b'blocked probe fixture')
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            env = {**os.environ, 'DATA_DIR':str(root/'data'), 'THUMB_DIR':str(root/'cache'),
                   'MEDIA_DIRS':str(root/'videos'), 'MEDIA_NAMES':'Startup test',
                   'MINI_HWACCEL':'off', 'MINI_AUTOSCAN':'0', 'MINI_TRANSCODE':'0',
                   'MINI_USER':'admin', 'MINI_PASS':'test', 'SECRET_KEY':'startup-test',
                   'MINI_EXTENSION_URL':'', 'MINI_SHARED_STATE':'0', 'MINI_SYNC_PEERS':''}
            code = '''import pathlib, subprocess, threading
from unittest.mock import patch
import sys
original = subprocess.run
def probe(args, *a, **kw):
    if args[0] == "ffmpeg":
        if any(str(arg).endswith("pending.mp4") for arg in args):
            pathlib.Path(sys.argv[2]).write_text("blocked")
            threading.Event().wait(30)
            return subprocess.CompletedProcess(args, 1, b"", b"")
        return subprocess.CompletedProcess(args, 0, b"0, 0, 0, 1, 123, abc\\n", b"")
    return original(args, *a, **kw)
with patch("subprocess.run", side_effect=probe):
    import app
    from waitress import serve
    serve(app.app, host="127.0.0.1", port=int(sys.argv[1]))
'''
            with open(root/'server.log', 'w+') as log:
                child = subprocess.Popen([sys.executable, '-c', code, str(port), str(root/'probing')],
                                         cwd=Path(__file__).resolve().parents[1], env=env,
                                         stdout=log, stderr=log)
                try:
                    deadline = time.monotonic()+8
                    success = False
                    while time.monotonic() < deadline and child.poll() is None:
                        try:
                            with urllib.request.urlopen(f'http://127.0.0.1:{port}/login', timeout=0.3) as response:
                                success = response.status == 200
                            if success and (root/'probing').exists():
                                break
                        except OSError:
                            pass
                        time.sleep(0.05)
                    log.seek(0)
                    self.assertTrue(success, log.read())
                    self.assertTrue((root/'probing').exists(), 'HTTP opens while validation is in progress')
                    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
                    base = f'http://127.0.0.1:{port}'
                    opener.open(base+'/login', data=urllib.parse.urlencode({'username':'admin','password':'test'}).encode(), timeout=2).close()
                    with opener.open(base+'/browse', timeout=2) as response:
                        page = response.read().decode()
                        self.assertIn('id="library-initial-scan"', page)
                        self.assertIn('ready.mp4', page)
                        self.assertNotIn('pending.mp4', page)
                    with opener.open(base+'/api/maintenance/progress', timeout=2) as response:
                        progress = json.load(response)
                        self.assertTrue(progress['running'])
                        self.assertEqual(progress['kind'], 'initial')
                        self.assertEqual(progress['indexed'], 1)
                    with sqlite3.connect(root/'data'/'storage.db') as db:
                        self.assertEqual(db.execute('SELECT count(*) FROM readable_media').fetchone()[0], 1)
                finally:
                    child.terminate()
                    child.wait(timeout=5)
