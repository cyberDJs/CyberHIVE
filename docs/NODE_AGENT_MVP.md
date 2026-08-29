# CyberHIVE Node Agent & Action Dispatch MVP

Patch 013 introduces the first node-side execution boundary.

## Why

Earlier patches can produce plans, evaluate policy, collect approvals and create
execution runs. Patch 013 adds the missing dispatch surface: a safe typed channel
for telling a node what should happen next.

## Architecture

```text
OrchestrationPlan
    ↓
Policy + Approval
    ↓
Execution Engine
    ↓
NodeActionDispatcher
    ↓
NodeAgentRegistry
    ↓
LocalNodeAgent
```

## MVP behavior

Supported typed actions:

- `health_check`
- `prewarm_model`
- `data_move`
- `cache_prime`
- `noop`

Dry-run is the default. Live node actions require local node policy to allow
live mode and the relevant approval token.

## Explicit non-goals

The MVP does not execute shell commands, open remote sessions, call container
runtimes, move files or start real model servers. It deliberately records intent
and safe local state only.

## Approval tokens

- `runtime.prewarm.execute` for live model prewarm recording
- `data.move.execute` for live data-move intent acceptance
- `cache.prime.execute` for live cache-prime intent acceptance

## Design note

The node agent repeats critical safety checks even though policy already ran
above it. Side-effect boundaries should be redundant and boring. Clever side-
effect boundaries are how infrastructure gets haunted.
