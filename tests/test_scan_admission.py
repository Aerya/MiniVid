"""Admission to the library is stricter than filename/allocated-size discovery."""
import os
import shutil
import subprocess
import unittest
from unittest import mock

import test_media_management_app as fixtures
minivid = fixtures.minivid
from media_managers import TorrentClientError


class ScanAdmissionTest(unittest.TestCase):
    tearDown = fixtures.MediaManagementApiTest.tearDown
    save_config = fixtures.MediaManagementApiTest.save_config

    def setUp(self):
        fixtures.MediaManagementApiTest.setUp(self)
        self.scan_readable_patch.stop()
        self.scan_completion_patch.stop()
        with minivid.storage.connect(minivid.STORAGE_DB) as db:
            db.execute('DELETE FROM readable_media')

    def test_preallocated_playable_but_incomplete_file_is_not_indexed(self):
        self.save_config(deletion_enabled=False, linked=True)
        client = mock.Mock()
        size = os.path.getsize(self.video_path)
        client.file_completion.return_value = {self.video_name: {'complete':False, 'size':size}}
        with mock.patch.object(minivid, '_configured_client', return_value=client), mock.patch.object(minivid, '_scan_readable_media', return_value=True) as readable:
            minivid.scan_media()
            self.assertEqual(minivid.MEDIA, [])
            readable.assert_not_called()
            client.file_completion.return_value[self.video_name]['complete'] = True
            minivid.scan_media()
            self.assertEqual([item['id'] for item in minivid.MEDIA], [self.vid])
            readable.assert_called_once()
            readable.return_value = False
            minivid.scan_media()
            self.assertEqual(minivid.MEDIA, [])
        self.assertTrue(os.path.exists(self.video_path))
        self.assertEqual(client.file_completion.call_count, 3)

    def test_missing_mismatched_or_unavailable_completion_is_excluded(self):
        self.save_config(deletion_enabled=False, linked=True)
        client = mock.Mock()
        with mock.patch.object(minivid, '_configured_client', return_value=client), mock.patch.object(minivid, '_scan_readable_media', return_value=True):
            for data in ({}, {self.video_name:{'complete':True,'size':99999}}):
                client.file_completion.return_value = data
                minivid.scan_media()
                self.assertEqual(minivid.MEDIA, [])
            client.file_completion.side_effect = TorrentClientError('offline')
            minivid.scan_media()
            self.assertEqual(minivid.MEDIA, [])
        self.assertTrue(os.path.exists(self.video_path))

    def test_local_source_requires_readability_even_without_torrent_integration(self):
        self.save_config(deletion_enabled=False)
        with mock.patch.object(minivid, '_is_decodable_media', return_value=False):
            minivid.scan_media()
            self.assertEqual(minivid.MEDIA, [])

    def test_only_successful_unchanged_validation_is_cached(self):
        cache = {}
        result = mock.Mock(returncode=0, stdout=b'# framehash\n0, 0, 0, 1, 123, abc\n')
        with mock.patch.object(minivid, '_is_decodable_media', return_value=True) as first, mock.patch.object(minivid.subprocess, 'run', return_value=result) as tail:
            stat = os.stat(self.video_path)
            self.assertTrue(minivid._scan_readable_media(self.video_path, stat, cache))
            self.assertTrue(minivid._scan_readable_media(self.video_path, stat, cache))
            first.assert_called_once()
            tail.assert_called_once()
            with open(self.video_path, 'ab') as handle:
                handle.write(b'changed')
            result.stdout = b'# headers without any decoded frame\n'
            self.assertFalse(minivid._scan_readable_media(self.video_path, os.stat(self.video_path), cache))
            result.stdout = b'0, 0, 0, 1, 123, abc\n'
            self.assertTrue(minivid._scan_readable_media(self.video_path, os.stat(self.video_path), cache))
            self.assertEqual(tail.call_count, 3)

    def test_changing_file_during_validation_is_rejected(self):
        def decode(*args, **kwargs):
            with open(self.video_path, 'ab') as handle:
                handle.write(b'downloading')
            return mock.Mock(returncode=0, stdout=b'0, 0, 0, 1, 123, abc\n')
        cache = {}
        with mock.patch.object(minivid, '_is_decodable_media', return_value=True), mock.patch.object(minivid.subprocess, 'run', side_effect=decode):
            self.assertFalse(minivid._scan_readable_media(self.video_path, os.stat(self.video_path), cache))
        self.assertNotIn(self.video_path, cache)

    def test_timeout_does_not_poison_the_validation_cache(self):
        cache = {}
        with mock.patch.object(minivid, '_is_decodable_media', return_value=True), mock.patch.object(minivid.subprocess, 'run', side_effect=subprocess.TimeoutExpired('ffmpeg',8)):
            self.assertFalse(minivid._scan_readable_media(self.video_path, os.stat(self.video_path), cache))
        self.assertEqual(cache, {})

    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg required for real container regression')
    def test_real_valid_mp4_is_admitted_and_truncated_mp4_is_excluded(self):
        self.save_config(deletion_enabled=False)
        os.remove(self.video_path)
        self.video_path = os.path.splitext(self.video_path)[0]+'.mp4'
        subprocess.run(['ffmpeg','-v','error','-nostdin','-f','lavfi','-i','color=c=black:s=32x32:r=10','-t','2','-c:v','mpeg4','-movflags','+faststart','-y',self.video_path],check=True,capture_output=True,timeout=15)
        minivid.scan_media()
        self.assertEqual(len(minivid.MEDIA), 1)
        with mock.patch.object(minivid, '_is_decodable_media', side_effect=AssertionError('persisted validation should be reused')):
            minivid.scan_media()
            self.assertEqual(len(minivid.MEDIA), 1)
        with open(self.video_path, 'r+b') as handle:
            handle.truncate(400)
        minivid.scan_media()
        self.assertEqual(minivid.MEDIA, [])
