#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from benchmark_resources import ResourceSampler, ResourceSummary

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


@dataclass
class RunResult:
    run_index: int
    timestamp_utc: str
    elapsed_ms: float
    ttft_ms: float | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    prompt_tokens_per_second: float | None
    generation_tokens_per_second: float | None
    generated_characters: int
    result: str
    notes: str
    error: str | None
    resources: ResourceSummary


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def percentile_nearest(values: list[float], p: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * p)]


def _max_optional(values: Iterable[float | None]) -> float | None:
    found = [value for value in values if value is not None]
    return max(found) if found else None


def summarize(runs: list[RunResult]) -> dict[str, Any]:
    passed = [run for run in runs if run.result == "pass"]
    elapsed = [run.elapsed_ms for run in passed]
    ttft = [run.ttft_ms for run in passed if run.ttft_ms is not None]
    prompt_tps = [run.prompt_tokens_per_second for run in passed if run.prompt_tokens_per_second is not None]
    generation_tps = [run.generation_tokens_per_second for run in passed if run.generation_tokens_per_second is not None]
    return {
        "runs": len(runs),
        "passed": len(passed),
        "failed": len(runs) - len(passed),
        "elapsed_ms_median": statistics.median(elapsed) if elapsed else None,
        "elapsed_ms_p95_nearest": percentile_nearest(elapsed, 0.95) if elapsed else None,
        "ttft_ms_median": statistics.median(ttft) if ttft else None,
        "ttft_ms_p95_nearest": percentile_nearest(ttft, 0.95) if ttft else None,
        "prompt_tokens_per_second_median": statistics.median(prompt_tps) if prompt_tps else None,
        "generation_tokens_per_second_median": statistics.median(generation_tps) if generation_tps else None,
        "generation_tokens_per_second_min": min(generation_tps) if generation_tps else None,
        "peak_vram_mib": _max_optional(run.resources.peak_vram_mib for run in runs),
        "peak_ram_mib": _max_optional(run.resources.peak_ram_mib for run in runs),
        "peak_gpu_utilization_pct": _max_optional(run.resources.peak_gpu_utilization_pct for run in runs),
        "peak_cpu_utilization_pct": _max_optional(run.resources.peak_cpu_utilization_pct for run in runs),
        "peak_runtime_rss_mib": _max_optional(run.resources.peak_runtime_rss_mib for run in runs),
    }


def iter_sse_json(lines: Iterable[bytes]) -> Iterator[dict[str, Any]]:
    data_lines: list[str] = []
    for raw in lines:
        line = raw.decode("utf-8", errors="strict").rstrip("\r\n")
        if not line:
            if data_lines:
                payload = "\n".join(data_lines)
                data_lines.clear()
                if payload == "[DONE]":
                    return
                yield json.loads(payload)
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
    if data_lines:
        payload = "\n".join(data_lines)
        if payload != "[DONE]":
            yield json.loads(payload)


def extract_delta_text(event: dict[str, Any]) -> str:
    choices = event.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        return ""
    delta = choices[0].get("delta")
    if not isinstance(delta, dict):
        return ""
    content = delta.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(item["text"] for item in content if isinstance(item, dict) and isinstance(item.get("text"), str))
    return ""


def extract_usage(event: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
    usage = event.get("usage")
    if not isinstance(usage, dict):
        return None, None, None
    values = [usage.get(key) for key in ("prompt_tokens", "completion_tokens", "total_tokens")]
    return tuple(value if isinstance(value, int) else None for value in values)  # type: ignore[return-value]


def calculate_throughput(
    prompt_tokens: int | None,
    completion_tokens: int | None,
    ttft_ms: float | None,
    elapsed_ms: float,
) -> tuple[float | None, float | None]:
    prompt_tps = prompt_tokens / (ttft_ms / 1000.0) if prompt_tokens is not None and ttft_ms is not None and ttft_ms > 0 else None
    generation_ms = elapsed_ms - ttft_ms if ttft_ms is not None else 0.0
    generation_tps = completion_tokens / (generation_ms / 1000.0) if completion_tokens is not None and generation_ms > 0 else None
    return prompt_tps, generation_tps


def load_host_facts(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("host facts must be a JSON object")
    return data


def _host_metadata(host_facts: dict[str, Any]) -> dict[str, Any]:
    os_data = host_facts.get("os") if isinstance(host_facts.get("os"), dict) else {}
    nvidia = host_facts.get("nvidia") if isinstance(host_facts.get("nvidia"), dict) else {}
    gpus = nvidia.get("gpus") if isinstance(nvidia.get("gpus"), list) else []
    gpu = gpus[0] if gpus and isinstance(gpus[0], dict) else {}
    fallback_os = f"{os_data.get('system', platform.system())} {os_data.get('release', platform.release())}".strip()
    return {
        "host_id": host_facts.get("hostname") or platform.node(),
        "os": os_data.get("pretty_name") or fallback_os,
        "kernel": os_data.get("release") or platform.release(),
        "gpu": gpu.get("name"),
        "driver": gpu.get("driver_version"),
        "cuda": nvidia.get("cuda_version"),
    }


def build_raw_record(run: RunResult, host_facts: dict[str, Any], args: argparse.Namespace) -> dict[str, Any]:
    host = _host_metadata(host_facts)
    record = {
        "schema_version": 1,
        "timestamp_utc": run.timestamp_utc,
        **host,
        "runtime": args.runtime,
        "runtime_version": args.runtime_version,
        "model_id": args.model,
        "model_revision": args.model_revision,
        "artifact_sha256": args.artifact_sha256.lower(),
        "quantization": args.quantization,
        "context_length": args.context_length,
        "ttft_ms": run.ttft_ms,
        "prompt_tokens_per_second": run.prompt_tokens_per_second,
        "generation_tokens_per_second": run.generation_tokens_per_second,
        "peak_vram_mib": run.resources.peak_vram_mib,
        "peak_ram_mib": run.resources.peak_ram_mib,
        "gpu_utilization_peak_pct": run.resources.peak_gpu_utilization_pct,
        "cpu_utilization_peak_pct": run.resources.peak_cpu_utilization_pct,
        "runtime_rss_peak_mib": run.resources.peak_runtime_rss_mib,
        "elapsed_ms": run.elapsed_ms,
        "prompt_tokens": run.prompt_tokens,
        "completion_tokens": run.completion_tokens,
        "total_tokens": run.total_tokens,
        "generated_characters": run.generated_characters,
        "resource_samples": run.resources.samples,
        "sampler_errors": run.resources.sampler_errors,
        "result": run.result,
        "notes": run.notes,
        "error": run.error,
    }
    return record


def execute_stream_run(
    *, run_index: int, url: str, model: str, prompt: str, max_tokens: int, timeout: int,
    context_length: int, sample_interval: float, runtime_pid: int | None,
) -> RunResult:
    del context_length  # metadata only; do not send non-standard context fields to runtime APIs
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": True,
        "stream_options": {"include_usage": True},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        method="POST",
    )
    sampler = ResourceSampler(interval_seconds=sample_interval, runtime_pid=runtime_pid)
    sampler.start()
    started = time.perf_counter()
    timestamp = utc_now()
    first_token_at: float | None = None
    prompt_tokens = completion_tokens = total_tokens = None
    generated: list[str] = []
    error: str | None = None
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/event-stream" not in content_type:
                raise ValueError(f"endpoint did not return text/event-stream: {content_type or 'missing content type'}")
            for event in iter_sse_json(response):
                text = extract_delta_text(event)
                if text:
                    generated.append(text)
                    if first_token_at is None:
                        first_token_at = time.perf_counter()
                p, c, t = extract_usage(event)
                prompt_tokens = p if p is not None else prompt_tokens
                completion_tokens = c if c is not None else completion_tokens
                total_tokens = t if t is not None else total_tokens
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, OSError, ValueError) as exc:
        error = str(exc)
    finished = time.perf_counter()
    resources = sampler.stop()
    elapsed_ms = (finished - started) * 1000.0
    ttft_ms = (first_token_at - started) * 1000.0 if first_token_at is not None else None
    prompt_tps, generation_tps = calculate_throughput(prompt_tokens, completion_tokens, ttft_ms, elapsed_ms)

    missing = []
    if error is None:
        for name, value in (("ttft", ttft_ms), ("prompt_tokens", prompt_tokens), ("completion_tokens", completion_tokens), ("generation_tokens_per_second", generation_tps)):
            if value is None:
                missing.append(name)
    notes = "required metrics unavailable: " + ", ".join(missing) if missing else ""
    if resources.sampler_errors:
        warning = "resource sampler warnings: " + "; ".join(resources.sampler_errors)
        notes = f"{notes}; {warning}" if notes else warning
    return RunResult(
        run_index=run_index,
        timestamp_utc=timestamp,
        elapsed_ms=elapsed_ms,
        ttft_ms=ttft_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        prompt_tokens_per_second=prompt_tps,
        generation_tokens_per_second=generation_tps,
        generated_characters=sum(len(part) for part in generated),
        result="pass" if error is None and not missing else "fail",
        notes=notes,
        error=error,
        resources=resources,
    )


def should_continue(started: float, now: float, completed_runs: int, minimum_runs: int, duration_seconds: int) -> bool:
    return completed_runs < minimum_runs or (duration_seconds > 0 and (now - started) < duration_seconds)


def sanitize_component(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-") or "unknown"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def validate_args(args: argparse.Namespace) -> None:
    if args.runs < 3:
        raise ValueError("--runs must be at least 3 for M0 evidence")
    if args.warmup < 1:
        raise ValueError("--warmup must be at least 1 for M0 evidence")
    if args.duration < 0:
        raise ValueError("--duration cannot be negative")
    if args.max_tokens <= 0 or args.context_length <= 0 or args.sample_interval <= 0:
        raise ValueError("token, context and sample values must be positive")
    if not _SHA256_RE.match(args.artifact_sha256):
        raise ValueError("--artifact-sha256 must be exactly 64 hexadecimal characters")
    if args.runtime_pid is not None and args.runtime_pid <= 0:
        raise ValueError("--runtime-pid must be positive")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark a local OpenAI-compatible streaming chat endpoint")
    parser.add_argument("--url", default="http://127.0.0.1:8000/v1/chat/completions")
    for flag in ("runtime", "runtime-version", "model", "model-revision", "artifact-sha256", "quantization"):
        parser.add_argument(f"--{flag}", required=True)
    parser.add_argument("--context-length", type=int, required=True)
    parser.add_argument("--host-facts", type=Path, required=True)
    parser.add_argument("--runtime-pid", type=int)
    parser.add_argument("--prompt", default="Explain why reproducible benchmarks matter in one short paragraph.")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--duration", type=int, default=0, help="Continue measured requests for at least this many seconds; use 600 for sustained M0 test")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--sample-interval", type=float, default=0.5)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", "-o", type=Path, required=True, help="Write batch summary JSON")
    args = parser.parse_args()
    try:
        validate_args(args)
        host_facts = load_host_facts(args.host_facts)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    for index in range(args.warmup):
        warmup = execute_stream_run(
            run_index=-(index + 1), url=args.url, model=args.model, prompt=args.prompt,
            max_tokens=args.max_tokens, timeout=args.timeout, context_length=args.context_length,
            sample_interval=args.sample_interval, runtime_pid=args.runtime_pid,
        )
        if warmup.error is not None:
            print(f"warmup failed: {warmup.error}", file=os.sys.stderr)
            return 2

    batch_started = time.monotonic()
    runs: list[RunResult] = []
    while should_continue(batch_started, time.monotonic(), len(runs), args.runs, args.duration):
        run = execute_stream_run(
            run_index=len(runs) + 1, url=args.url, model=args.model, prompt=args.prompt,
            max_tokens=args.max_tokens, timeout=args.timeout, context_length=args.context_length,
            sample_interval=args.sample_interval, runtime_pid=args.runtime_pid,
        )
        runs.append(run)
        filename = f"{sanitize_component(args.runtime)}-{sanitize_component(args.model)}-run-{run.run_index:03d}.json"
        write_json(args.raw_dir / filename, build_raw_record(run, host_facts, args))

    write_json(args.output, {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "benchmark_mode": "sustained" if args.duration > 0 else "measured",
        "requested_duration_seconds": args.duration,
        "runtime": args.runtime,
        "runtime_version": args.runtime_version,
        "model_id": args.model,
        "model_revision": args.model_revision,
        "artifact_sha256": args.artifact_sha256.lower(),
        "quantization": args.quantization,
        "context_length": args.context_length,
        "endpoint": args.url,
        "summary": summarize(runs),
        "runs": [asdict(run) for run in runs],
    })
    return 0 if all(run.result == "pass" for run in runs) else 2


if __name__ == "__main__":
    raise SystemExit(main())
