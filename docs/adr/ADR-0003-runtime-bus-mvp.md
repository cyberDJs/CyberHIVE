# ADR-0003: Runtime Bus MVP uses append-only log and micro-batching

## Status

Accepted for MVP.

## Context

CyberHIVE needs a fast local data plane for observations, state deltas, command
results and telemetry. Sending every tiny update through independent request and
write paths would waste CPU, I/O and network resources.

## Decision

Implement a pure-stdlib MVP Runtime Bus with:

- `Operation` as the smallest work unit,
- `HiveFrame` as a batch of operations,
- `MicroBatcher` for count, size, latency and priority flushes,
- append-only JSONL frame log for durable local trail,
- revisioned `StateEngine` for current runtime state.

## Consequences

Positive:

- runnable immediately on any Python 3 installation,
- simple audit trail,
- clear migration path toward protobuf frames,
- avoids premature dependency on Kafka, NATS, Redis or PostgreSQL.

Negative:

- JSONL is not the final high-throughput wire format,
- no distributed ordering yet,
- no encryption or authentication in this layer yet.

## Follow-up

Benchmark JSON fallback vs protobuf/MessagePack/CBOR before choosing final data
plane serialization.
