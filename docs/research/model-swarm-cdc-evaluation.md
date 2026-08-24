# Model Swarm CDC evaluation — 2026-08-24

## Decision

**Do not adopt content-defined chunking into Model Swarm v0.1. Keep fixed 4 MiB chunks and manifest schema v1 as the production baseline.**

The measured synthetic corpus does demonstrate that CDC can recover deduplication after byte insertion shifts, but the best tested CDC configuration reduces unique bytes by only **1.47% versus fixed 4 MiB** on the combined five-version corpus. That is not enough value to justify a new chunking algorithm, manifest semantics, migration surface, and extra packing CPU.

## Context and constraints

Verified project facts:

- Model Swarm manifest schema v1 uses fixed-size chunks, SHA-256 per chunk, and whole-artifact SHA-256.
- The default production chunk size is 4 MiB.
- ADR-0004 explicitly deferred CDC until measured deduplication value exists.
- Fixed-size schema must remain readable if a future algorithm is added.
- No third-party runtime dependency should be added without measurable benefit.

Research assumptions:

- The deterministic synthetic corpus is intended to represent common checkpoint/version mutation patterns, not the byte layout of every GGUF/safetensors/model family.
- Short isolated-runner timings are appropriate for relative research evidence, not production SLOs.
- A real model corpus may justify re-evaluation later.

## Method

A dependency-free Go research harness compares:

1. `fixed-4m` — current 4 MiB fixed chunks.
2. `gear-cdc-2m` — Gear-style rolling hash, 1 MiB minimum, ~2 MiB target mask, 4 MiB maximum.
3. `gear-cdc-4m` — Gear-style rolling hash, 2 MiB minimum, ~4 MiB target mask, 8 MiB maximum.

The 8 MiB deterministic base artifact is transformed into:

- identical copy;
- 64 KiB metadata insertion after 1 MiB, shifting all subsequent bytes;
- 1 MiB region replacement;
- 1 MiB append-only growth;
- five independent 4 KiB sparse edits;
- combined five-version corpus: base + shifted + replaced + appended + sparse.

Mutation data uses independent deterministic seeds so inserted bytes cannot accidentally duplicate the base artifact.

Measurements include raw bytes, unique bytes, deduplication savings, chunk-reference count, estimated index bytes, pack time, reassembly time, and SHA-256 reassembly verification.

## Measured results

| Scenario | fixed-4m savings | gear-cdc-2m savings | gear-cdc-4m savings |
| --- | ---: | ---: | ---: |
| identical | 50.00% | 50.00% | 50.00% |
| metadata shift | 0.00% | **37.43%** | 0.00% |
| region replacement | **25.00%** | 12.42% | 0.00% |
| append-only | **47.06%** | 26.04% | **47.06%** |
| sparse edits | 0.00% | 0.00% | 0.00% |
| combined five-version | 29.22% | **30.26%** | 19.48% |

Combined corpus raw bytes: **43,057,152**.

- fixed-4m unique bytes: **30,474,240**
- gear-cdc-2m unique bytes: **30,026,520**
- gear-cdc-4m unique bytes: **34,668,544**

Relative to fixed-4m:

- gear-cdc-2m reduces unique bytes by **1.47%**;
- gear-cdc-4m increases unique bytes by **13.76%**.

Combined-corpus median timing over three runs:

| Metric | fixed-4m | gear-cdc-2m | gear-cdc-4m |
| --- | ---: | ---: | ---: |
| pack | 196.082 ms | 289.169 ms | 309.983 ms |
| pack ratio vs fixed | 1.00× | **1.47×** | **1.58×** |
| reassembly | 517.816 ms | 425.266 ms | 383.359 ms |
| chunk references | 12 | 18 | 8 |
| estimated index bytes | 768 B | 1,152 B | 512 B |

The observed faster reassembly for the CDC fixtures is not treated as a production performance claim. It may reflect allocation/chunk-layout effects in the small synthetic corpus. All reconstructed artifacts were verified by SHA-256.

## Adoption gate

A future CDC architecture change should be considered only if a legally/test-wise approved **real model version corpus** demonstrates all of the following against fixed 4 MiB:

- at least **15% fewer unique bytes** across representative multi-version artifacts;
- packing CPU time no worse than **2.5×** fixed chunking;
- manifest/index overhead below **0.1%** of raw artifact bytes;
- reassembly regression no worse than **25%**;
- no mandatory external service or database;
- fixed schema v1 remains supported for read/fetch/seed;
- migration is opt-in per artifact and rollback does not require rewriting existing v1 CAS data.

Current result: **VALUE_GATE=FAIL** because the best tested CDC configuration improves unique bytes by only 1.47%, far below the 15% threshold.

## Security impact

No security boundary changes are required for this research result. SHA-256 content verification and artifact authorization remain unchanged.

A future schema that supports CDC must bind the chunking algorithm and its parameters into authenticated/signed manifest semantics; otherwise two nodes could interpret the same artifact metadata differently.

## Performance/resource impact

Keeping fixed 4 MiB preserves:

- current low-complexity packing path;
- predictable chunk counts;
- existing CAS and manifest readers;
- lower CPU cost on weak nodes;
- zero migration cost.

CDC remains potentially valuable for artifact families dominated by insertion/shift behavior, as shown by the 37.43% metadata-shift result. That isolated win does not justify system-wide adoption.

## Alternatives rejected

- **Adopt Gear CDC now:** rejected; value gate fails.
- **Replace fixed schema v1:** rejected; unnecessary migration and compatibility risk.
- **Add a third-party CDC library now:** rejected; no measured need justifies dependency/supply-chain cost.
- **Tune CDC parameters until the synthetic benchmark wins:** rejected as benchmark overfitting.

## Migration / rollback if revisited later

If a future real-corpus evaluation passes the gate, introduce an explicit chunking algorithm identifier in a new manifest schema/version. Keep the v1 fixed reader and seeding path. New CDC artifacts may coexist with v1 artifacts in CAS because chunk identity remains content-addressed by SHA-256.

Rollback must disable creation of the new schema while retaining read support; existing v1 artifacts require no rewrite.

## Verification status

Verified in an isolated Linux workspace:

- dependency-free research harness;
- `go vet` passes;
- SHA-256 reassembly validation passes for every artifact;
- deterministic deduplication fixture tests cover exact reassembly and insertion-shift resynchronization;
- raw JSON evidence is retained in `benchmarks/results/swarm-cdc-research-2026-08-24.json`.

Physical RTX-class hosts, real LAN/Wi-Fi transfer effects, and real model-version corpora remain **UNVERIFIED** and are not required to justify the current no-adopt decision.

## ADR required

**No new ADR now.** ADR-0004 already records fixed-size v0.1 and explicitly defers CDC pending evidence. A new/superseding ADR is required only if future evidence passes the adoption gate and CyberHIVE chooses to introduce another chunking schema.
