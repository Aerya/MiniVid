#!/usr/bin/env python3
"""Prepare MiniVid's single CDI device and prove it works through Docker."""

from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import re
import socket
import stat
import subprocess
import time
import uuid


HOST = Path(os.environ.get("MINIVID_HOST_ROOT", "/host"))
CDI_FILE = Path(os.environ.get("MINIVID_CDI_FILE", "/var/run/cdi/minivid.json"))
DOCKER_SOCKET = os.environ.get("DOCKER_HOST_SOCKET", "/var/run/docker.sock")
MODE = os.environ.get("MINIVID_GPU", "auto").strip().lower()
FALLBACK = os.environ.get("MINIVID_GPU_FALLBACK", "1").strip().lower() not in {
    "0", "false", "no", "off"
}
VALID_MODES = {"auto", "cpu", "nvidia", "vaapi", "intel", "amd"}


def log(message: str) -> None:
    print(f"[MiniVid GPU] {message}", flush=True)


def atomic_spec(spec: dict) -> None:
    CDI_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = CDI_FILE.with_suffix(f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o644)
    os.replace(temporary, CDI_FILE)
    # Docker watches the standard CDI directories, but its filesystem watcher is
    # asynchronous. A short delay avoids racing container creation.
    time.sleep(0.3)


def cpu_spec(reason: str) -> None:
    atomic_spec({
        "cdiVersion": "0.7.0",
        "kind": "minivid.dev/gpu",
        "devices": [{
            "name": "all",
            "containerEdits": {"env": ["MINIVID_GPU_SELECTED=cpu"]},
        }],
    })
    log(f"Mode CPU sélectionné ({reason}).")


def host_path(path: str) -> Path:
    return HOST / path.lstrip("/")


def run_on_host(command: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
    def enter_host() -> None:
        os.chroot(HOST)
        os.chdir("/")

    return subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
        preexec_fn=enter_host,
    )


def nvidia_present() -> bool:
    return host_path("/dev/nvidiactl").exists() and (
        host_path("/proc/driver/nvidia/version").exists()
        or host_path("/usr/bin/nvidia-smi").exists()
    )


def stale_nvidia_cdi() -> list[str]:
    missing: set[str] = set()
    for location in ("/etc/cdi/nvidia.yaml", "/var/run/cdi/nvidia.yaml"):
        path = host_path(location)
        try:
            content = path.read_text(encoding="utf-8")
        except (FileNotFoundError, PermissionError, UnicodeDecodeError):
            continue
        # NVIDIA YAML specs identify injected host files with hostPath. JSON
        # specs use the same field name. Only absolute host paths are checked.
        candidates = re.findall(r'(?:hostPath\s*:\s*|"hostPath"\s*:\s*")([^"\s,}]+)', content)
        for candidate in candidates:
            if candidate.startswith("/") and not host_path(candidate).exists():
                missing.add(candidate)
    return sorted(missing)


def generate_nvidia_spec() -> tuple[bool, str]:
    executable = "/usr/bin/nvidia-ctk"
    if not host_path(executable).exists():
        return False, "nvidia-ctk absent de l'hôte"
    result = run_on_host([
        executable, "cdi", "generate",
        "--output=/var/run/cdi/minivid.json",
        "--format=json", "--vendor=minivid.dev", "--class=gpu",
    ])
    if result.returncode != 0:
        return False, result.stdout.strip() or "échec de nvidia-ctk"
    time.sleep(0.3)
    return True, ""


def regenerate_standard_nvidia_cdi() -> bool:
    """Run NVIDIA's documented manual refresh into its standard runtime path."""
    executable = "/usr/bin/nvidia-ctk"
    if not host_path(executable).exists():
        return False
    targets = ["/var/run/cdi/nvidia.yaml"]
    if host_path("/etc/cdi/nvidia.yaml").exists():
        targets.append("/etc/cdi/nvidia.yaml")
    results = [run_on_host([
        executable, "cdi", "generate", f"--output={target}",
    ]) for target in targets]
    if all(result.returncode == 0 for result in results):
        log("CDI NVIDIA standard régénéré avec nvidia-ctk.")
        return True
    return False


def render_devices(wanted: str) -> list[Path]:
    devices = sorted(host_path("/dev/dri").glob("renderD*"))
    if wanted in {"intel", "amd"}:
        expected = {"intel": {"0x8086"}, "amd": {"0x1002", "0x1022"}}[wanted]
        devices = [device for device in devices if drm_vendor(device) in expected]
    return devices


def drm_vendor(device: Path) -> str:
    vendor = host_path(f"/sys/class/drm/{device.name}/device/vendor")
    try:
        return vendor.read_text(encoding="ascii").strip().lower()
    except OSError:
        return ""


def generate_vaapi_spec(wanted: str) -> tuple[bool, str]:
    devices = render_devices(wanted)
    if not devices:
        return False, f"aucun périphérique VA-API {wanted if wanted != 'vaapi' else ''}".strip()
    nodes = []
    for device in devices:
        info = device.stat()
        container_path = "/" + str(device.relative_to(HOST))
        nodes.append({
            "path": container_path,
            "hostPath": container_path,
            "type": "c",
            "major": os.major(info.st_rdev),
            "minor": os.minor(info.st_rdev),
            "fileMode": stat.S_IMODE(info.st_mode),
            "permissions": "rwm",
            "uid": info.st_uid,
            "gid": info.st_gid,
        })
    atomic_spec({
        "cdiVersion": "0.7.0",
        "kind": "minivid.dev/gpu",
        "devices": [{
            "name": "all",
            "containerEdits": {
                "deviceNodes": nodes,
                "additionalGids": sorted({node["gid"] for node in nodes}),
                "env": ["MINIVID_GPU_SELECTED=vaapi"],
            },
        }],
    })
    return True, ""


class UnixHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str):
        super().__init__("localhost", timeout=60)
        self.socket_path = socket_path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)


def docker_request(method: str, path: str, body: dict | None = None) -> tuple[int, bytes]:
    connection = UnixHTTPConnection(DOCKER_SOCKET)
    payload = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if payload else {}
    connection.request(method, path, body=payload, headers=headers)
    response = connection.getresponse()
    data = response.read()
    connection.close()
    return response.status, data


def decode_docker_logs(data: bytes) -> str:
    """Decode Docker's multiplexed stdout/stderr stream."""
    output = bytearray()
    offset = 0
    while offset + 8 <= len(data) and data[offset] in {0, 1, 2}:
        size = int.from_bytes(data[offset + 4:offset + 8], "big")
        start = offset + 8
        end = start + size
        if end > len(data):
            break
        output.extend(data[start:end])
        offset = end
    if not output:
        output.extend(data)
    return output.decode(errors="replace").strip()


def docker_gpu_test(kind: str) -> tuple[bool, str]:
    name = f"minivid-gpu-test-{uuid.uuid4().hex[:10]}"
    image = os.environ.get("MINIVID_TEST_IMAGE", "ghcr.io/aerya/minivid:latest")
    if kind == "nvidia":
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
            "-i", "color=size=256x256:rate=1", "-frames:v", "1",
            "-c:v", "h264_nvenc", "-f", "null", "-",
        ]
    else:
        command = [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-vaapi_device", "/dev/dri/renderD128", "-f", "lavfi",
            "-i", "color=size=256x256:rate=1", "-vf", "format=nv12,hwupload",
            "-frames:v", "1", "-c:v", "h264_vaapi", "-f", "null", "-",
        ]
    request = {
        "Image": image,
        "Cmd": command,
        "HostConfig": {"DeviceRequests": [{
            "Driver": "cdi", "Count": 0,
            "DeviceIDs": ["minivid.dev/gpu=all"],
        }]},
    }
    try:
        status, data = docker_request("POST", f"/containers/create?name={name}", request)
        if status != 201:
            return False, data.decode(errors="replace")
        status, data = docker_request("POST", f"/containers/{name}/start")
        if status != 204:
            return False, data.decode(errors="replace")
        status, data = docker_request("POST", f"/containers/{name}/wait?condition=not-running")
        if status != 200:
            return False, data.decode(errors="replace")
        exit_code = json.loads(data)["StatusCode"]
        _, logs = docker_request("GET", f"/containers/{name}/logs?stdout=1&stderr=1")
        message = decode_docker_logs(logs)
        return exit_code == 0, message
    except (OSError, TimeoutError, ValueError, http.client.HTTPException) as error:
        return False, str(error)
    finally:
        try:
            docker_request("DELETE", f"/containers/{name}?force=1")
        except Exception:
            pass


def fail_or_cpu(reason: str) -> None:
    if FALLBACK:
        cpu_spec(reason)
        return
    log(f"Échec sans fallback CPU : {reason}")
    raise SystemExit(1)


def prepare_nvidia() -> None:
    stale = stale_nvidia_cdi()
    refreshed = False
    if stale:
        log(f"CDI NVIDIA obsolète détecté ({stale[0]} absent).")
        refreshed = regenerate_standard_nvidia_cdi()
    generated, detail = generate_nvidia_spec()
    if generated:
        passed, detail = docker_gpu_test("nvidia")
        if passed:
            log("NVIDIA NVENC utilisable par Docker.")
            return
    if not refreshed:
        refreshed = regenerate_standard_nvidia_cdi()
        generated, generation_detail = generate_nvidia_spec()
        if generated:
            passed, detail = docker_gpu_test("nvidia")
            if passed:
                log("NVIDIA NVENC utilisable par Docker après refresh CDI.")
                return
        else:
            detail = generation_detail
    fail_or_cpu(f"NVIDIA inutilisable: {detail[:500]}")


def prepare_vaapi(wanted: str) -> None:
    generated, detail = generate_vaapi_spec(wanted)
    if generated:
        passed, detail = docker_gpu_test("vaapi")
        if passed:
            log("VA-API utilisable par Docker.")
            return
    fail_or_cpu(f"VA-API inutilisable: {detail[:500]}")


def main() -> None:
    if MODE not in VALID_MODES:
        log("MINIVID_GPU doit valoir auto, cpu, nvidia, vaapi, intel ou amd.")
        raise SystemExit(2)
    if MODE == "cpu":
        cpu_spec("mode demandé")
    elif MODE == "nvidia":
        prepare_nvidia()
    elif MODE in {"vaapi", "intel", "amd"}:
        prepare_vaapi(MODE)
    elif nvidia_present():
        prepare_nvidia()
    elif render_devices("vaapi"):
        prepare_vaapi("vaapi")
    else:
        cpu_spec("aucun GPU compatible détecté")


if __name__ == "__main__":
    main()
