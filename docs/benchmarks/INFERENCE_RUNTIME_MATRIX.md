# M0 Inference Runtime Benchmark Matrix

Status: Draft
Reference node: Ryzen 7 5800X / 32 GB RAM / NVIDIA GeForce RTX 3070 8 GB
Reference OS candidate: Ubuntu Server 24.04 LTS amd64

## Goal

Select the first production runtime path using measured behavior on the actual reference node, not benchmark folklore.

## Candidates

| Runtime | M0 role | Required result |
| --- | --- | --- |
| llama.cpp | Primary candidate | Must pass |
| vLLM | Secondary serving candidate | Benchmark and document limits |
| Ollama | Convenience integration | Smoke test only in M0 |
| TensorRT-LLM | Experimental | Test only if setup is reasonable on RTX 3070 |

## Model classes

Benchmark at least three practical classes. Use models whose licenses permit the intended CyberHIVE use.

1. **Small** — roughly 1B-4B parameters, quantized where appropriate.
2. **Reference** — roughly 7B-8B parameters, sized to exercise the 8 GB VRAM limit.
3. **Stress** — a model/configuration that requires partial CPU offload or otherwise exposes the memory boundary.

Record the exact model revision, artifact hash, quantization and prompt fixture. Do not compare different model representations as though they were identical workloads.

## Measurements

For every runtime/model combination capture:

- cold start time,
- model load time,
- time to first token,
- prompt processing throughput,
- generation tokens/second,
- peak VRAM,
- peak host RAM,
- GPU utilization,
- CPU utilization,
- idle memory footprint,
- sustained 10-minute behavior,
- restart/recovery behavior,
- API compatibility notes,
- setup complexity,
- failure reason when a test cannot run.

## Standard workload

Run each valid combination with:

- identical deterministic prompt fixtures,
- identical requested context length where supported,
- single-user latency test,
- short concurrency test where supported,
- 10-minute sustained generation test,
- daemon/runtime restart followed by the same smoke request.

Perform at least three measured runs after one warm-up run. Store raw results; report median and worst observed value.

## Scoring

M0 selection is weighted for an appliance rather than a datacenter:

| Dimension | Weight |
| --- | ---: |
| Works reliably within 8 GB VRAM | 30% |
| Latency / generation performance | 20% |
| Operational simplicity | 15% |
| Memory efficiency | 15% |
| API / integration quality | 10% |
| Recovery and observability | 10% |

A runtime that cannot reliably operate on the reference node cannot win M0 solely on peak throughput.

## Pass gates

The primary M0 runtime must:

1. run headless after reboot,
2. expose a health check,
3. complete the reference-model workload without OOM,
4. recover cleanly after process restart,
5. provide measurable resource usage,
6. operate without a mandatory cloud dependency,
7. support a documented model artifact format,
8. survive the sustained test without accumulating critical errors.

## Raw result schema

Store machine-readable runs under `benchmarks/results/` using one JSON file per run:

```json
{
  "schema_version": 1,
  "timestamp_utc": "",
  "host_id": "",
  "os": "",
  "kernel": "",
  "gpu": "NVIDIA GeForce RTX 3070",
  "driver": "",
  "cuda": "",
  "runtime": "",
  "runtime_version": "",
  "model_id": "",
  "model_revision": "",
  "artifact_sha256": "",
  "quantization": "",
  "context_length": 0,
  "ttft_ms": 0,
  "prompt_tokens_per_second": 0,
  "generation_tokens_per_second": 0,
  "peak_vram_mib": 0,
  "peak_ram_mib": 0,
  "result": "pass|fail",
  "notes": ""
}
```

## Decision output

At the end of the sprint, update ADR-0002 and ADR-0003 from `Proposed` to `Accepted`, `Rejected` or `Superseded` based on the measured results.
