# Runbook: M0 inference benchmark on the RTX 3070 reference node

## Purpose

Collect reproducible evidence for CyberHIVE issue #9 on the physical CH-M0-RTX3070 node. This runbook measures an already-installed runtime; it does not install drivers, change services, modify model artifacts, or alter ADR status.

## Scope and owner

- Target: Ryzen 7 5800X / 32 GB RAM / NVIDIA GeForce RTX 3070 8 GB.
- Reference OS candidate: Ubuntu Server 24.04 LTS amd64.
- Runtime candidates: llama.cpp, vLLM, Ollama smoke-only, TensorRT-LLM experimental-only.
- Evidence owner: CyberHIVE maintainers.

## Prerequisites

Before starting, verify:

1. you are on the physical reference node, not a VM or another GPU host;
2. the runtime and model under test are already installed and their exact versions are known;
3. the model revision, artifact SHA-256, quantization and context length are known;
4. the inference API is bound to loopback for benchmark execution;
5. there is enough free disk space under `benchmarks/results/`;
6. no unrelated GPU workload is running.

Stop if the node identity, GPU, model hash, runtime version, or benchmark branch is ambiguous.

## Safety

The commands below are read-only with respect to the host except for writing benchmark JSON under the repository. They do not install packages, restart services automatically, reboot the node, or delete evidence.

Runtime restart and host reboot are explicit operator actions. Perform them only when you are ready to interrupt inference on this reference node.

## 1. Verify repository and benchmark harness

Run from the CyberHIVE repository root on the reference node:

```bash
git status --short
git rev-parse --show-toplevel
python3 -m py_compile scripts/collect_host_facts.py scripts/benchmark_resources.py scripts/benchmark_openai.py
python3 -m unittest discover -s tests -v
```

Expected result:

- working tree state is understood;
- repository root is the intended CyberHIVE checkout;
- Python compile and tests pass.

Do not benchmark from an unreviewed local patch.

## 2. Collect host facts

```bash
python3 scripts/collect_host_facts.py \
  --output benchmarks/results/host-facts.json
```

Verify:

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = json.loads(Path('benchmarks/results/host-facts.json').read_text())
print(json.dumps(p.get('nvidia', {}), indent=2))
PY
```

Required before continuing:

- GPU reports `NVIDIA GeForce RTX 3070`;
- VRAM is approximately 8 GiB;
- driver is present;
- CUDA compatibility reported by `nvidia-smi` is captured.

Stop if `nvidia-smi` is missing, the wrong GPU is selected, or GPU facts are incomplete.

## 3. Record runtime and model identity

For every runtime/model combination record, outside secrets:

- runtime name and exact version;
- exact launch command;
- model ID and pinned revision;
- SHA-256 of the local model artifact;
- quantization;
- configured context length;
- runtime process PID when available.

Example model hash command:

```bash
sha256sum /path/to/model.gguf
```

The SHA-256 must be copied into the benchmark command exactly. Do not compare different model representations as if they were the same workload.

## 4. Start one runtime manually

Start the runtime using its documented pinned version and bind its OpenAI-compatible API to loopback.

Default benchmark endpoint:

```text
http://127.0.0.1:8000/v1/chat/completions
```

Confirm health/readiness using the runtime's documented local health endpoint or a smoke request before collecting measured evidence.

## 5. Run the measured three-run benchmark

Replace every placeholder before running:

```bash
python3 scripts/benchmark_openai.py \
  --runtime '<runtime-name>' \
  --runtime-version '<exact-version>' \
  --model '<exact-runtime-model-id>' \
  --model-revision '<pinned-model-revision>' \
  --artifact-sha256 '<64-hex-sha256>' \
  --quantization '<exact-quantization>' \
  --context-length 4096 \
  --host-facts benchmarks/results/host-facts.json \
  --runtime-pid '<runtime-pid>' \
  --warmup 1 \
  --runs 3 \
  --raw-dir benchmarks/results/raw/<runtime-name>/<model-id> \
  --output benchmarks/results/<runtime-name>-<model-id>-summary.json
```

If a stable runtime PID is not available, omit `--runtime-pid`. Host RAM, CPU, GPU utilization and VRAM sampling still run; only runtime RSS stays unavailable.

The harness fails closed when required TTFT or token-usage metrics are unavailable. Do not replace missing metrics with guesses.

## 6. Run the 10-minute sustained test

Use the same runtime, model, prompt, context and artifact identity:

```bash
python3 scripts/benchmark_openai.py \
  --runtime '<runtime-name>' \
  --runtime-version '<exact-version>' \
  --model '<exact-runtime-model-id>' \
  --model-revision '<pinned-model-revision>' \
  --artifact-sha256 '<64-hex-sha256>' \
  --quantization '<exact-quantization>' \
  --context-length 4096 \
  --host-facts benchmarks/results/host-facts.json \
  --runtime-pid '<runtime-pid>' \
  --warmup 1 \
  --runs 3 \
  --duration 600 \
  --raw-dir benchmarks/results/raw/<runtime-name>/<model-id>-sustained \
  --output benchmarks/results/<runtime-name>-<model-id>-sustained-summary.json
```

Acceptance evidence must include no critical runtime error, no OOM, and no unexplained degradation that invalidates the run.

## 7. Validate restart behavior

First restart only the runtime process using the runtime's documented operator procedure. Do not reboot yet.

After restart:

1. confirm the same runtime version;
2. confirm the same model artifact hash;
3. repeat one complete measured benchmark command from step 5;
4. preserve the resulting JSON with a `restart` suffix.

A runtime that does not recover cleanly fails the M0 recovery gate even if its peak throughput is high.

## 8. Validate host reboot recovery

Reboot is intentionally not automated by this runbook.

After the operator reboots the reference node:

1. verify headless boot completed;
2. recollect `host-facts.json` under a new filename;
3. verify GPU/driver availability;
4. verify the runtime becomes healthy using the documented service procedure;
5. repeat the measured benchmark from step 5;
6. preserve the post-reboot raw JSON and summary.

Stop if the driver, GPU, runtime, model identity, or service state differs unexpectedly from the pre-reboot evidence.

## 9. Evidence to preserve

For every valid combination retain:

- host facts JSON;
- one raw JSON file per measured request;
- batch summary JSON;
- runtime launch command and version;
- model revision and artifact SHA-256;
- measured three-run result;
- sustained 10-minute result;
- process-restart result;
- post-reboot result;
- exact failure reason for unsupported or failed combinations.

Raw run JSON intentionally matches the issue #9 schema and adds resource-sampler fields. TTFT is measured from request start to the first non-empty streamed token. Effective prompt throughput is prompt tokens divided by TTFT; generation throughput uses completion tokens divided by post-TTFT generation time. Both are local loopback measurements and must be interpreted consistently across runtimes.

## Stop conditions

Stop the current runtime/model test when any of these occur:

- OOM or repeated GPU driver error;
- model hash/revision mismatch;
- runtime version mismatch;
- endpoint is not local to the reference node;
- streaming usage does not provide the required token counts;
- resource sampler cannot observe the GPU for a GPU benchmark;
- sustained run shows critical errors;
- evidence files would overwrite a previous authoritative run.

Record the failure instead of silently tuning until the result looks good.

## Validation

A runtime/model combination is evidence-complete only when:

- warm-up plus at least three measured runs exist;
- TTFT, effective prompt throughput and generation throughput are present;
- peak VRAM, host RAM, GPU utilization and CPU utilization are captured;
- 10-minute sustained evidence exists;
- process restart is validated;
- post-reboot health and benchmark are validated;
- all model/runtime identities are pinned.

## Rollback

The harness changes no system configuration. To abandon a test, stop the runtime using its normal operator procedure and leave generated evidence in place until it has been classified as valid or rejected. Do not delete failed evidence while investigating a failure.

## Decision gate

Do not change ADR-0002 or ADR-0003 from `Proposed` based on preflight or synthetic data. ADR status changes require reviewed measurements from the physical CH-M0-RTX3070 node.
