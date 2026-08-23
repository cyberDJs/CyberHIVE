# ADR-0003: Inference runtime strategy for M0

Status: Proposed
Date: 2026-08-23

## Context

CyberHIVE must support local inference on a consumer NVIDIA RTX 3070 with 8 GB VRAM while preserving a path to higher-throughput server hardware later.

No single runtime should become an irreversible platform dependency.

## Decision

Adopt a runtime-adapter architecture with this M0 order:

1. **llama.cpp** — primary reference runtime for local quantized inference and the RTX 3070 appliance path.
2. **vLLM** — secondary reference runtime for OpenAI-compatible serving and future higher-throughput/multi-user workloads.
3. **Ollama** — optional developer/user convenience integration, not the core runtime contract.
4. **TensorRT-LLM** — experimental benchmark target only until consumer RTX 3070 support, operational complexity and measurable gain justify promotion.

The CyberHIVE control plane talks to runtimes through a stable internal adapter contract rather than embedding runtime-specific assumptions into scheduling or UI code.

## Rationale

### llama.cpp

Best M0 fit for constrained VRAM, GGUF quantization, broad local deployment and low operational overhead. It is the baseline that must work even when the node is offline.

### vLLM

Current vLLM NVIDIA requirements include compute capability 7.5 or higher. RTX 3070 is Ampere compute capability 8.6, so it is a valid benchmark candidate. vLLM is valuable for OpenAI-compatible serving, batching and future scale-out, but it may have a larger memory/operational footprint than llama.cpp on an 8 GB consumer card.

### Ollama

Useful packaging and UX layer. CyberHIVE should integrate it where useful but must not make its model store, API conventions or lifecycle the platform's canonical abstraction.

### TensorRT-LLM

Potentially excellent on NVIDIA server hardware, but current official hardware documentation emphasizes supported datacenter-class NVIDIA platforms. It is therefore not the M0 dependency for the RTX 3070 reference node.

## Runtime adapter minimum contract

Each runtime adapter must expose at least:

- availability and version,
- supported model formats,
- model load/unload,
- health/readiness,
- text generation request,
- streaming generation,
- runtime metrics,
- VRAM/RAM consumption where observable,
- graceful cancellation,
- capability discovery.

## Consequences

- Model registry metadata must distinguish model identity from runtime representation.
- Scheduler decisions use capabilities and measured resources, not runtime names.
- Benchmarking is mandatory before changing the primary runtime.
- Runtime-specific optimizations remain replaceable modules.

## Acceptance criteria

1. The same logical model can be represented by multiple runtime artifacts where licensing permits.
2. Control-plane code can switch adapters without changing API consumers.
3. Baseline benchmark results exist for llama.cpp and vLLM on the RTX 3070 node.
4. Failure of one runtime does not prevent CyberHIVE from managing the node.
