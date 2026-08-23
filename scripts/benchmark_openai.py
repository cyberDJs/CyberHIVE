#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any


@dataclass
class RunResult:
    elapsed_ms: float
    completion_tokens: int | None
    prompt_tokens: int | None
    total_tokens: int | None
    tokens_per_second: float | None
    status: str
    error: str | None = None


def percentile_nearest(values: list[float], p: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    ordered = sorted(values)
    idx = round((len(ordered) - 1) * p)
    return ordered[idx]


def summarize(runs: list[RunResult]) -> dict[str, Any]:
    passed = [r for r in runs if r.status == "pass"]
    elapsed = [r.elapsed_ms for r in passed]
    tps = [r.tokens_per_second for r in passed if r.tokens_per_second is not None]
    return {
        "runs": len(runs),
        "passed": len(passed),
        "failed": len(runs) - len(passed),
        "elapsed_ms_median": statistics.median(elapsed) if elapsed else None,
        "elapsed_ms_p95_nearest": percentile_nearest(elapsed, 0.95) if elapsed else None,
        "tokens_per_second_median": statistics.median(tps) if tps else None,
        "tokens_per_second_min": min(tps) if tps else None,
    }


def post_json(url: str, payload: dict[str, Any], timeout: int) -> tuple[dict[str, Any], float]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
    elapsed_ms = (time.perf_counter() - started) * 1000
    return json.loads(body), elapsed_ms


def execute_run(url: str, model: str, prompt: str, max_tokens: int, timeout: int) -> RunResult:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": False,
    }
    try:
        body, elapsed_ms = post_json(url, payload, timeout)
        usage = body.get("usage") or {}
        completion_tokens = usage.get("completion_tokens")
        prompt_tokens = usage.get("prompt_tokens")
        total_tokens = usage.get("total_tokens")
        tps = None
        if isinstance(completion_tokens, int) and elapsed_ms > 0:
            tps = completion_tokens / (elapsed_ms / 1000)
        return RunResult(elapsed_ms, completion_tokens, prompt_tokens, total_tokens, tps, "pass")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return RunResult(0.0, None, None, None, None, "fail", str(exc))


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark an OpenAI-compatible chat completions endpoint")
    parser.add_argument("--url", default="http://127.0.0.1:8000/v1/chat/completions")
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", default="Explain why reproducible benchmarks matter in one short paragraph.")
    parser.add_argument("--max-tokens", type=int, default=128)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output", "-o")
    args = parser.parse_args()

    for _ in range(max(args.warmup, 0)):
        execute_run(args.url, args.model, args.prompt, args.max_tokens, args.timeout)

    runs = [execute_run(args.url, args.model, args.prompt, args.max_tokens, args.timeout) for _ in range(max(args.runs, 1))]
    result = {
        "schema_version": 1,
        "endpoint": args.url,
        "model": args.model,
        "prompt": args.prompt,
        "max_tokens": args.max_tokens,
        "runs": [asdict(r) for r in runs],
        "summary": summarize(runs),
    }

    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    return 0 if all(r.status == "pass" for r in runs) else 2


if __name__ == "__main__":
    raise SystemExit(main())
