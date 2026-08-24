# CyberHIVE CDC research harness

This directory contains a standalone, dependency-free research benchmark for issue #7.
It does **not** implement a production chunking format and is not on the Model Swarm runtime path.

Run from the repository root:

```sh
go run ./tools/research/cdcbench ./benchmarks/results/swarm-cdc-research-2026-08-24.json
go test -race ./tools/research/cdcbench
```

The corpus is deterministic and synthetic. It models checkpoint-like version changes: identical copies, an inserted metadata region that shifts subsequent bytes, a replaced region, append-only growth, sparse edits, and a combined five-version corpus.

The benchmark compares the current fixed 4 MiB chunking model with two experimental Gear-style content-defined configurations. Gear CDC here is only a measurement instrument. It is not a proposed wire/storage format.
