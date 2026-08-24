# Model Swarm scheduler v0.1

## Decision

Peer selection remains an in-process wrapper around the existing `peer.Source` interface. It does not add a broker, database, scheduler daemon or network hop.

The scheduler ranks only peers that already advertise the requested chunk. It may use fresh telemetry when available and degrades to deterministic hash affinity when telemetry is missing or stale.

## Inputs

The v0.1 telemetry contract contains:

- measured effective throughput in bytes/second;
- round-trip latency;
- current upload utilization in the range 0..1;
- locality: same host, LAN, VPN, Internet or unknown;
- observation timestamp.

Telemetry is supplied through a `TelemetryProvider` interface. Collection is deliberately outside the ranking algorithm so the source can later be backed by local measurements, coordinator state or another approved observer without changing the fetcher.

## Ranking

For fresh telemetry, the base score is:

```text
0.40 * normalized_throughput
+ 0.20 * latency_score
+ 0.20 * free_upload_capacity
+ 0.20 * locality_score
```

A small deterministic chunk/peer affinity is mixed into the result:

```text
final = 0.88 * base + 0.12 * hash_affinity(chunk, peer)
```

The affinity prevents equivalent peers from always losing to the first stable tie-breaker and spreads chunks without mutable scheduler state.

Stale or missing telemetry does not make a peer unavailable. Such peers receive a conservative fallback score plus the same deterministic affinity. Exact ties resolve by peer ID so repeated ranking is reproducible.

Invalid negative/NaN/infinite measurements are sanitized before scoring.

## Why this design

- preserves offline and single-node behavior;
- adds zero services and zero runtime dependencies;
- remains explainable: `Rank` returns component scores;
- avoids making telemetry availability a hard dependency for downloads;
- allows later benchmark-driven tuning of weights without changing the peer-discovery or transport contracts.

## Verification status

Unit tests prove that:

- a much faster, lower-latency LAN peer outranks a slower loaded VPN peer;
- equivalent peers are distributed across many chunks through deterministic affinity;
- stale telemetry falls back deterministically rather than blocking downloads.

The tests prove algorithmic behavior, **not real-world performance improvement**. Issue #6 must establish a reproducible benchmark and compare this scheduler against the simple first-peer baseline before issue #4 can be considered complete.

## Non-goals

- predictive model prefetch;
- distributed consensus;
- persistent telemetry database;
- global scheduling across unrelated Hives;
- learned/ML ranking;
- changing artifact identity or the Model Swarm data path.

## Acceptance follow-up — 2026-08-24

Issue #4's remaining acceptance checks are covered by a focused child change without modifying the production scheduler algorithm:

- ranking tests now exercise at least three peers and assert that normalized throughput, latency, load, locality, affinity and final score remain inspectable;
- a mutable upstream-source test proves a disappeared peer is removed from the next ranking instead of being retained in scheduler state;
- equivalent-peer ordering is re-evaluated deterministically for the same chunk;
- the synthetic benchmark's timed telemetry probe uses the median of five samples to reduce short-run scheduler jitter;
- a dedicated `contended-multi` scenario models two equally suitable peers with 64 MiB/s aggregate capacity, 2 ms RTT and one concurrent upload slot each.

For `contended-multi`, stable controlled telemetry inputs are intentionally used instead of wall-clock probes. This isolates the scheduler's source-spreading behavior from runner timing noise. The existing heterogeneous benchmark continues to exercise timed measured inputs.

A five-run 8 MiB / 1 MiB-chunk / concurrency-4 acceptance probe recorded a first-peer median of about 211.2 ms and scheduler median of about 129.1 ms, approximately 38.9% improvement. The scheduler transferred 4 MiB from each of the two peers in every recorded run.

These are synthetic acceptance results, **not** production LAN or RTX-class throughput claims. Real-network validation remains `UNVERIFIED`, and this follow-up does not define a production regression threshold.

Compact evidence is stored in `benchmarks/results/swarm-scheduler-acceptance-2026-08-24.json`.
