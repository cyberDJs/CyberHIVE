# CyberHIVE Model Swarm observability and synthetic performance baseline

Status: experimental / non-production baseline

## Decision

Model Swarm v0.1 exposes an in-process observer contract and a bounded in-memory recorder before adding any monitoring backend. The first benchmark uses the real fetcher, CAS, concurrency and scheduler source with a deterministic synthetic network client. No Prometheus server, telemetry database, external SaaS or background collector is required.

## Privacy and cardinality

The structured metrics intentionally contain no prompt text, user content, model name, hostname, credential, chunk hash or endpoint URL.

Per-peer metrics use the stable peer ID only. The recorder keeps at most 64 explicit peer IDs by default; additional IDs are aggregated into `__other__`. This bounds label cardinality even when discovery returns a large or hostile peer set.

## Metrics contract

One fetch can report:

- artifact bytes and completion time;
- peer bytes and origin bytes;
- verified local cache-hit bytes, cache-miss bytes and hit ratio;
- per-peer attempts, failures, bytes, average request latency and effective throughput;
- chunk verification failures;
- retry count and fallback count;
- final artifact success.

Chunk hashes and artifact/model identifiers are deliberately not part of the metrics schema.

## Benchmark command

Single synthetic run:

```sh
go run ./cmd/swarmbench \
  --artifact-mib=8 \
  --chunk-mib=1 \
  --concurrency=4 \
  --strategy=scheduler \
  --scenario=heterogeneous \
  --runs=5
```

Issue #6 matrix:

```sh
go run ./cmd/swarmbench \
  --matrix \
  --artifact-mib=8 \
  --runs=1 \
  --output=benchmarks/results/swarm-matrix.json
```

The matrix covers chunk sizes 1/4/16 MiB, concurrency 1/4/8/16, first-peer vs scheduler source selection, and single/multi/heterogeneous peer scenarios. The 8 MiB default bounds execution cost; 16 MiB chunk behavior is additionally checked with a targeted 32 MiB artifact run.

## Synthetic network profiles

The benchmark does not contact the Internet. A synthetic client delays real fetch calls according to controlled peer profiles and returns the actual manifest chunk bytes.

- single: one LAN-like peer at nominal 1 GiB/s and 0.5 ms RTT;
- multi: two equivalent LAN-like peers at nominal 1 GiB/s and 0.5 ms RTT;
- heterogeneous: `peer-a` at nominal 128 MiB/s + 8 ms RTT, `peer-b` at nominal 1 GiB/s + 0.5 ms RTT;
- origin-fallback: failing peer plus explicit origin at nominal 512 MiB/s + 2 ms RTT.

Before scheduler runs, the benchmark probes the synthetic peers and feeds measured effective throughput and RTT into the actual scheduler `TelemetryProvider`. Upload utilization is neutral and locality is fixed to LAN for this initial comparison.

## Baseline recorded 2026-08-24

Environment: isolated Linux/amd64 runner, Go 1.23.2. Real RTX-class hardware and physical LAN/Wi-Fi validation are **UNVERIFIED**.

The committed full matrix contains 72 synthetic cases. In the current matrix, the scheduler is faster than first-peer selection in all 12 heterogeneous chunk/concurrency combinations; the median improvement across those 12 one-run comparisons is about 30%. Equal/single-peer cases show expected runner and filesystem noise and are not evidence of universal scheduler benefit.

A separate five-run heterogeneous point (8 MiB artifact, 1 MiB chunks, concurrency 4) records:

- first-peer median: about 100.9 ms;
- scheduler median: about 75.1 ms;
- median improvement: about 25.6%.

A targeted 32 MiB / 16 MiB-chunk heterogeneous probe also exercises the large-chunk path. The attempted full 32 MiB matrix exceeded the isolated runner time budget, so large-artifact matrix validation is intentionally not part of normal CI.

Metric sanity probes additionally verify:

- 50% pre-seeded CAS produces a 0.5 cache-hit ratio and transfers only the remaining bytes from peers;
- origin fallback records failed peer attempts/fallbacks separately and attributes successful fallback bytes to `origin_bytes`.

The compact evidence summary is committed as `benchmarks/results/swarm-synthetic-baseline-2026-08-24.json`. Raw matrix output is retained in the CASER SandCloud session and is reproducible with the documented `swarmbench --matrix` command rather than permanently bloating Git history.

## Interpretation boundary

This baseline proves that the scheduler can have measurable value when candidate peers are materially heterogeneous and that the telemetry schema can measure the effect. It does **not** prove production LAN throughput, RTX-specific performance or a stable regression threshold.

No performance regression threshold is defined yet. Thresholds should be proposed only after repeated runs on the reference CyberHIVE hardware and real network paths.
