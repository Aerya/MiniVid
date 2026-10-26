"""Concurrent HLS clients must share the encoder without duplicate work."""
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock
import test_media_management_app as fixtures

app = fixtures.minivid


class HlsResourcesTest(unittest.TestCase):
    def test_concurrent_requests_encode_once_and_serialize_distinct_segments(self):
        ready = set()
        active = peak = 0
        calls = []
        barrier = threading.Barrier(6)
        lock = threading.Lock()

        def encode(full, path, index):
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
                calls.append(path)
            time.sleep(0.02)
            ready.add(path)
            with lock:
                active -= 1
            return True

        def request(index):
            barrier.wait(timeout=3)
            return app._build_segment_file('video', f'seg-{index % 3}', index % 3)

        with mock.patch.object(app.os.path, 'exists', side_effect=lambda p: p in ready), \
             mock.patch.object(app, '_encode_segment_file', side_effect=encode):
            with ThreadPoolExecutor(max_workers=6) as pool:
                self.assertTrue(all(pool.map(request, range(6))))
        self.assertEqual(peak, 1)
        self.assertCountEqual(calls, ['seg-0', 'seg-1', 'seg-2'])

    def test_failed_job_releases_encoder_for_retry(self):
        with mock.patch.object(app.os.path, 'exists', return_value=False), \
             mock.patch.object(app, '_encode_segment_file', side_effect=[RuntimeError('failed'), True]):
            with self.assertRaises(RuntimeError):
                app._build_segment_file('video', 'seg', 0)
            self.assertTrue(app._build_segment_file('video', 'seg', 0))

    def test_hardware_and_software_fallback_bound_decoder_threads(self):
        commands = []
        def run(args, **kwargs):
            commands.append(args)
            if len(commands) == 1:
                raise app.subprocess.CalledProcessError(1, args)
        with mock.patch.object(app, 'HAS_NVENC', True), \
             mock.patch.object(app, 'HAS_VAAPI', False), \
             mock.patch.object(app, '_probe_all', return_value={'vcodec': 'hevc'}), \
             mock.patch.object(app.subprocess, 'run', side_effect=run), \
             mock.patch.object(app.os, 'replace'):
            self.assertTrue(app._encode_segment_file('video', 'seg', 0))
        self.assertEqual(len(commands), 2)
        for cmd in commands:
            self.assertLess(cmd.index('-threads'), cmd.index('-i'))
            self.assertEqual(cmd[cmd.index('-threads') + 1], '2')
        self.assertIn('h264_nvenc', commands[0])
        self.assertIn('cuda', commands[0])
        self.assertIn('libx264', commands[1])
        self.assertNotIn('-hwaccel', commands[1])

    def test_transcoding_caps_bitrate_for_each_encoder_without_scaling(self):
        for nvenc, vaapi, software in [(True, False, False), (False, True, False), (False, False, True)]:
            with self.subTest(nvenc=nvenc, vaapi=vaapi), \
                 mock.patch.object(app, 'HAS_NVENC', nvenc), \
                 mock.patch.object(app, 'HAS_VAAPI', vaapi), \
                 mock.patch.object(app, '_probe_all', return_value={'vcodec': 'hevc'}):
                args = app._vcodec_args('4k-video', software=software)
                self.assertEqual(args[args.index('-maxrate') + 1], '24M')
                self.assertEqual(args[args.index('-bufsize') + 1], '48M')
                self.assertFalse(any('scale' in arg for arg in args))
        with mock.patch.object(app, '_probe_all', return_value={'vcodec': 'h264'}):
            self.assertEqual(app._vcodec_args('direct-video'), ['-c:v', 'copy'])

    def test_legacy_high_bitrate_segment_is_not_reused(self):
        import os
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            video = os.path.join(root, 'video.mp4')
            with open(video, 'wb') as handle:
                handle.write(b'video fixture')
            vid = app.id_for(0, 'video.mp4')
            cache = os.path.join(root, 'cache', vid)
            os.makedirs(cache)
            with open(os.path.join(cache, 'seg_0.ts'), 'wb') as handle:
                handle.write(b'legacy high bitrate')
            with mock.patch.object(app, 'MEDIA_DIRS', [root]), \
                 mock.patch.object(app, 'HLS_SEGMENT_DIR', os.path.join(root, 'cache')), \
                 mock.patch.object(app, 'auth_required', return_value=True), \
                 mock.patch.object(app, '_build_segment_file', return_value=False) as build:
                response = app.app.test_client().get('/hls/' + vid + '/segment_0.ts')
                self.assertEqual(response.status_code, 500)
                self.assertEqual(build.call_args.args[1], os.path.join(cache, app.HLS_CACHE_VERSION + '_seg_0.ts'))
