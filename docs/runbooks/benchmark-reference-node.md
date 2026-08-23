# Runbook: benchmark the M0 reference node

## Purpose

Collect reproducible host facts and benchmark an OpenAI-compatible inference endpoint on the RTX 3070 reference node.

## Safety

These commands are read-only except for writing result JSON files under the repository. They do not install drivers, change services or modify model files.

## 1. Collect host facts

From the repository root:

```bash
python3 scripts/collect_host_facts.py \
  --output benchmarks/results/host-facts.json
```

Verify the JSON includes the expected RTX 3070, VRAM, driver and compute capability before running model benchmarks.

## 2. Start one runtime manually

Start the runtime under test using its documented, pinned version and record the exact launch command in the benchmark notes.

The benchmark harness expects an OpenAI-compatible chat-completions endpoint. The default URL is:

```text
http://127.0.0.1:8000/v1/chat/completions
```

## 3. Execute benchmark requests

```bash
python3 scripts/benchmark_openai.py \
  --model '<exact-runtime-model-id>' \
  --runs 3 \
  --warmup 1 \
  --output benchmarks/results/<runtime>-<model>-run.json
```

Use the same prompt, `max_tokens`, model revision and runtime configuration when comparing runtimes.

## 4. Capture GPU metrics

Run `nvidia-smi` in parallel or use the runtime's metrics endpoint to capture peak VRAM, GPU utilization and temperatures. The first harness intentionally does not invent peak resource values it cannot measure reliably itself.

## 5. Validate restart behavior

Restart only the runtime process, repeat the smoke request, then reboot the node and repeat host-facts + smoke validation.

## 6. Record failures

A failed or unsupported configuration is still a valid benchmark result. Record the exact runtime version, command and error instead of tuning it silently until it passes.

## Rollback

This runbook changes no system configuration. Remove generated files under `benchmarks/results/` if a test run must be discarded.
