# ADR-0018: Canonical Communication EventStore over RuntimeBus

## Status

Proposed for MVP.

## Date

2026-09-27

## Context

CyberHIVE already owns the runtime transport primitive (`RuntimeBus`) and its append-only
`HiveFrame` JSONL trail. Multi-agent rooms need durable room/session/actor communication history,
idempotency, resume and integrity evidence without creating a second message bus or moving
orchestration policy into CyberHIVE.

## Decision

Add an immutable `CommunicationEvent` v1 contract and a narrow `EventStore` interface.
`RuntimeBusEventStore` persists communication events as high-priority OBSERVE operations through
the existing RuntimeBus and existing AppendOnlyLog.

Communication-event `sequence` is independent from `HiveFrame.sequence`. On startup the adapter
replays persisted communication events, verifies their hash chain, restores the next communication
sequence, and advances the in-memory RuntimeBus frame sequence to the highest persisted frame
sequence it observed.

EventStore requires a trusted `EventAccessContext` for append/read. Actor spoofing and unauthorized
room/session access fail closed. Secret-bearing payload/metadata keys are redacted before hashing
and persistence.

## Consequences

Positive:

- no second event bus;
- single-node restart/resume works with existing persistence;
- duplicate event IDs are idempotent only for identical canonical content;
- simple SHA-256 chaining gives lightweight tamper evidence;
- orchestration remains outside CyberHIVE.

Costs:

- startup currently scans the local JSONL log;
- one global communication sequence is optimized for single-node MVP, not distributed ordering;
- hash chaining is integrity evidence, not authentication or authorization.

## Rejected alternatives

- A new Redis/NATS/Kafka bus: unjustified for the single-node MVP and duplicates RuntimeBus.
- Reusing HiveFrame sequence as conversation sequence: it is transport-local and was not restart-durable.
- Putting agent selection/floor control here: violates the CyberCore control-plane boundary.

## Verification

- append/read ordering;
- same-ID idempotency and conflicting-ID rejection;
- restart/resume from persisted sequence;
- actor and room/session authorization;
- secret redaction;
- hash-chain verification;
- presence join/leave projection.

## Migration / rollback

The change is additive. Before merge, discard the feature branch. After merge but before deployment,
revert the merge commit. No existing RuntimeBus or log format is rewritten.
