# CyberHIVE Patch 015 — Node Heartbeat & Capability Sync MVP

## Purpose

Patch 015 makes enrolled nodes observable and schedulable.

It introduces an authenticated heartbeat surface that turns node-side telemetry into controller-side capability snapshots, liveness state and scheduler `NodeState` objects.

## Flow

```text
Node Enrollment + Session
        ↓
NodeHeartbeat
        ↓
NodeHeartbeatStore
        ↓
CapabilitySnapshot
        ↓
Liveness + Scheduler NodeState + optional NodeDescriptor
        ↓
ComputeRouter
```

## Safety boundaries

The MVP does not open sockets, perform LAN discovery, accept anonymous telemetry, run shell commands or mutate node-local services. If a `NodeIdentityRegistry` is configured, heartbeat ingestion requires a valid enrolled identity and active session token.

## Liveness model

- `healthy`: fresh heartbeat and normal pressure
- `degraded`: fresh heartbeat but high queue or GPU pressure
- `stale`: heartbeat is old and should not receive aggressive routing
- `expired`: heartbeat is too old and should not be considered live
- `unknown`: no heartbeat has been seen

## Scheduler sync

`NodeHeartbeatStore.sync_router(router)` upserts scheduler `NodeState` records derived from the latest capability snapshots. This keeps routing based on observed reality rather than static config.

## Non-goals

- network transport
- mTLS
- remote attestation
- persistent metrics store
- Prometheus exporter
- automatic quarantine policy
- physical workload execution
