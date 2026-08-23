#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any


def run_command(cmd: list[str], timeout: int = 10) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)


def read_meminfo(path: str = "/proc/meminfo") -> dict[str, int]:
    result: dict[str, int] = {}
    try:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            key, raw = line.split(":", 1)
            parts = raw.strip().split()
            if not parts:
                continue
            value = int(parts[0])
            if len(parts) > 1 and parts[1].lower() == "kb":
                value *= 1024
            result[key] = value
    except (OSError, ValueError):
        pass
    return result


def parse_nvidia_smi_csv(text: str) -> list[dict[str, Any]]:
    gpus: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 6:
            continue
        index, name, uuid, memory_total, driver_version, compute_cap = parts
        try:
            memory_total_mib = int(memory_total)
        except ValueError:
            memory_total_mib = None
        gpus.append(
            {
                "index": int(index) if index.isdigit() else index,
                "name": name,
                "uuid": uuid,
                "memory_total_mib": memory_total_mib,
                "driver_version": driver_version,
                "compute_capability": compute_cap or None,
            }
        )
    return gpus


def collect_nvidia() -> dict[str, Any]:
    exe = shutil.which("nvidia-smi")
    if not exe:
        return {"available": False, "gpus": [], "error": "nvidia-smi not found"}

    query = [
        exe,
        "--query-gpu=index,name,uuid,memory.total,driver_version,compute_cap",
        "--format=csv,noheader,nounits",
    ]
    rc, out, err = run_command(query)
    if rc != 0:
        return {"available": False, "gpus": [], "error": err or f"nvidia-smi exited {rc}"}

    rc2, cuda_out, _ = run_command([exe])
    cuda_version = None
    if rc2 == 0:
        marker = "CUDA Version:"
        if marker in cuda_out:
            tail = cuda_out.split(marker, 1)[1].strip()
            cuda_version = tail.split()[0]

    return {"available": True, "gpus": parse_nvidia_smi_csv(out), "cuda_version": cuda_version}


def collect_host_facts() -> dict[str, Any]:
    mem = read_meminfo()
    uname = platform.uname()

    disk = shutil.disk_usage("/")
    container_runtimes = {}
    for name in ("docker", "podman"):
        exe = shutil.which(name)
        if not exe:
            container_runtimes[name] = None
            continue
        rc, out, err = run_command([exe, "--version"])
        container_runtimes[name] = out if rc == 0 else f"error: {err or rc}"

    return {
        "schema_version": 1,
        "hostname": socket.gethostname(),
        "os": {
            "system": uname.system,
            "release": uname.release,
            "version": uname.version,
            "machine": uname.machine,
            "python": platform.python_version(),
        },
        "cpu": {
            "model": platform.processor() or None,
            "logical_cpus": os.cpu_count(),
        },
        "memory": {
            "total_bytes": mem.get("MemTotal"),
            "available_bytes": mem.get("MemAvailable"),
        },
        "storage_root": {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
        },
        "nvidia": collect_nvidia(),
        "container_runtimes": container_runtimes,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect CyberHIVE reference-node host facts as JSON")
    parser.add_argument("--output", "-o", help="Write JSON to file instead of stdout")
    args = parser.parse_args()

    payload = json.dumps(collect_host_facts(), indent=2, sort_keys=True)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
