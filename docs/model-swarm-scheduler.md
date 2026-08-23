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
