import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import gpu_bootstrap as gpu


class GpuBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.spec = self.root / "run/cdi/minivid.json"
        self.patches = [
            mock.patch.object(gpu, "HOST", self.root),
            mock.patch.object(gpu, "CDI_FILE", self.spec),
            mock.patch.object(gpu.time, "sleep"),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.temporary.cleanup()

    def test_cpu_spec_is_a_resolvable_empty_cdi_device(self):
        gpu.cpu_spec("test")
        spec = json.loads(self.spec.read_text())
        self.assertEqual(spec["cdiVersion"], "0.7.0")
        self.assertEqual(spec["kind"], "minivid.dev/gpu")
        self.assertEqual(
            spec["devices"][0]["containerEdits"]["env"],
            ["MINIVID_GPU_SELECTED=cpu"],
        )

    def test_stale_nvidia_cdi_reports_a_missing_host_library(self):
        cdi = self.root / "etc/cdi/nvidia.yaml"
        cdi.parent.mkdir(parents=True)
        cdi.write_text("hostPath: /usr/lib/libnvidia-egl-wayland.so.1.1.21\n")
        self.assertEqual(
            gpu.stale_nvidia_cdi(),
            ["/usr/lib/libnvidia-egl-wayland.so.1.1.21"],
        )

    def test_vaapi_spec_uses_render_node_and_group(self):
        render = self.root / "dev/dri/renderD128"
        render.parent.mkdir(parents=True)
        render.touch()
        with mock.patch.object(gpu, "render_devices", return_value=[render]), mock.patch.object(
            Path, "stat", return_value=mock.Mock(
                st_rdev=os.makedev(226, 128), st_mode=0o20660, st_uid=0, st_gid=109
            )
        ):
            success, _ = gpu.generate_vaapi_spec("vaapi")
        self.assertTrue(success)
        edits = json.loads(self.spec.read_text())["devices"][0]["containerEdits"]
        self.assertEqual(edits["deviceNodes"][0]["path"], "/dev/dri/renderD128")
        self.assertEqual(edits["additionalGids"], [109])

    def test_failed_gpu_falls_back_to_cpu_by_default(self):
        with mock.patch.object(gpu, "FALLBACK", True):
            gpu.fail_or_cpu("indisponible")
        selected = json.loads(self.spec.read_text())["devices"][0]["containerEdits"]["env"]
        self.assertEqual(selected, ["MINIVID_GPU_SELECTED=cpu"])

    def test_failed_forced_gpu_can_block_when_fallback_is_disabled(self):
        with mock.patch.object(gpu, "FALLBACK", False):
            with self.assertRaises(SystemExit):
                gpu.fail_or_cpu("indisponible")

    def test_docker_logs_are_demultiplexed(self):
        payload = b"erreur\n"
        stream = bytes([2, 0, 0, 0]) + len(payload).to_bytes(4, "big") + payload
        self.assertEqual(gpu.decode_docker_logs(stream), "erreur")


if __name__ == "__main__":
    unittest.main()
