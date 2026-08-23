---
name: cyberhive-model-ops
description: Select, deploy, benchmark and troubleshoot local AI models and inference runtimes for CyberHIVE based on real hardware constraints. Use when choosing models, quantization, runtimes, GPU/CPU placement, context size, concurrency, memory limits, benchmark plans, runtime compatibility or diagnosing local inference performance. Prefer measured hardware facts over assumptions and optimize first for stable operation on consumer GPUs such as RTX 3070.
---

# CyberHIVE Model Ops

Collect actual hardware and software facts before recommending a model/runtime when possible.

## Workflow

1. Establish GPU model/VRAM, RAM, CPU, storage, OS, driver and relevant runtime versions.
2. Define workload: chat, coding, embeddings, vision, audio, batch, latency target and concurrency.
3. Produce one recommended model/runtime profile plus fallback profiles.
4. State estimated memory requirements as estimates until measured.
5. Define a benchmark with repeatable prompts/workloads and capture latency, tokens/s, VRAM/RAM, failures and quality notes.
6. Keep deployment reversible and record exact model identity/checksum when practical.
7. Diagnose OOM/slowdowns from evidence before reducing quality blindly.
