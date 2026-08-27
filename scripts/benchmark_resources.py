#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ResourceSummary:
    samples: int
    peak_vram_mib: float | None
    peak_ram_mib: float | None
    peak_gpu_utilization_pct: float | None
    peak_cpu_utilization_pct: float | None
    peak_runtime_rss_mib: float | None
    sampler_errors: list[str]


@dataclass(frozen=True)
class _CPUTicks:
    total: int
    idle: int


def run_command(cmd: list[str], timeout: float = 5.0) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)


def parse_meminfo(text: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        parts = raw.strip().split()
        if not parts:
            continue
        try:
            value = int(parts[0])
        except ValueError:
            continue
        if len(parts) > 1 and parts[1].lower() == "kb":
            value *= 1024
        result[key] = value
    return result


def read_meminfo(path: str = "/proc/meminfo") -> dict[str, int]:
    try:
        return parse_meminfo(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return {}


def host_ram_used_mib(meminfo: dict[str, int]) -> float | None:
    total = meminfo.get("MemTotal")
    available = meminfo.get("MemAvailable")
    if total is None or available is None or total < available:
        return None
    return (total - available) / (1024 * 1024)


def parse_proc_stat(text: str) -> _CPUTicks | None:
    first = text.splitlines()[0] if text.splitlines() else ""
    fields = first.split()
    if len(fields) < 5 or fields[0] != "cpu":
        return None
    try:
        values = [int(value) for value in fields[1:]]
    except ValueError:
        return None
    total = sum(values)
    idle = values[3]
    if len(values) > 4:
        idle += values[4]
    return _CPUTicks(total=total, idle=idle)


def read_cpu_ticks(path: str = "/proc/stat") -> _CPUTicks | None:
    try:
        return parse_proc_stat(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return None


def cpu_utilization_pct(previous: _CPUTicks | None, current: _CPUTicks | None) -> float | None:
    if previous is None or current is None:
        return None
    total_delta = current.total - previous.total
    idle_delta = current.idle - previous.idle
    if total_delta <= 0 or idle_delta < 0:
        return None
    busy = total_delta - idle_delta
    value = (busy / total_delta) * 100.0
    return max(0.0, min(100.0, value))


def parse_nvidia_smi_sample(text: str) -> tuple[float | None, float | None]:
    line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    if not line:
        return None, None
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 2:
        return None, None
    try:
        memory_used = float(parts[0])
    except ValueError:
        memory_used = None
    try:
        gpu_util = float(parts[1])
    except ValueError:
        gpu_util = None
    return memory_used, gpu_util


def read_process_rss_mib(pid: int | None) -> float | None:
    if pid is None or pid <= 0:
        return None
    try:
        text = Path(f"/proc/{pid}/status").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        if not line.startswith("VmRSS:"):
            continue
        parts = line.split()
        if len(parts) < 2:
            return None
        try:
            return int(parts[1]) / 1024.0
        except ValueError:
            return None
    return None


class ResourceSampler:
    def __init__(self, interval_seconds: float = 0.5, runtime_pid: int | None = None) -> None:
        if interval_seconds <= 0:
            raise ValueError("resource sample interval must be positive")
        self.interval_seconds = interval_seconds
        self.runtime_pid = runtime_pid
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._samples = 0
        self._peak_vram_mib: float | None = None
        self._peak_ram_mib: float | None = None
        self._peak_gpu_utilization_pct: float | None = None
        self._peak_cpu_utilization_pct: float | None = None
        self._peak_runtime_rss_mib: float | None = None
        self._errors: list[str] = []
        self._nvidia_smi = shutil.which("nvidia-smi")

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("resource sampler already started")
        self._thread = threading.Thread(target=self._run, name="cyberhive-resource-sampler", daemon=True)
        self._thread.start()

    def stop(self) -> ResourceSummary:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(2.0, self.interval_seconds * 4))
        with self._lock:
            return ResourceSummary(
                samples=self._samples,
                peak_vram_mib=self._peak_vram_mib,
                peak_ram_mib=self._peak_ram_mib,
                peak_gpu_utilization_pct=self._peak_gpu_utilization_pct,
                peak_cpu_utilization_pct=self._peak_cpu_utilization_pct,
                peak_runtime_rss_mib=self._peak_runtime_rss_mib,
                sampler_errors=list(self._errors),
            )

    def _record_peak(self, name: str, value: float | None) -> None:
        if value is None:
            return
        current = getattr(self, name)
        if current is None or value > current:
            setattr(self, name, value)

    def _run(self) -> None:
        previous_cpu = read_cpu_ticks()
        while not self._stop.is_set():
            meminfo = read_meminfo()
            ram_used = host_ram_used_mib(meminfo)
            current_cpu = read_cpu_ticks()
            cpu_pct = cpu_utilization_pct(previous_cpu, current_cpu)
            previous_cpu = current_cpu
            runtime_rss = read_process_rss_mib(self.runtime_pid)

            vram_mib: float | None = None
            gpu_util: float | None = None
            if self._nvidia_smi:
                rc, out, err = run_command(
                    [
                        self._nvidia_smi,
                        "--query-gpu=memory.used,utilization.gpu",
                        "--format=csv,noheader,nounits",
                    ],
                    timeout=max(2.0, self.interval_seconds * 2),
                )
                if rc == 0:
                    vram_mib, gpu_util = parse_nvidia_smi_sample(out)
                elif err:
                    with self._lock:
                        if len(self._errors) < 8:
                            self._errors.append(f"nvidia-smi: {err}")

            with self._lock:
                self._samples += 1
                self._record_peak("_peak_vram_mib", vram_mib)
                self._record_peak("_peak_ram_mib", ram_used)
                self._record_peak("_peak_gpu_utilization_pct", gpu_util)
                self._record_peak("_peak_cpu_utilization_pct", cpu_pct)
                self._record_peak("_peak_runtime_rss_mib", runtime_rss)

            self._stop.wait(self.interval_seconds)
