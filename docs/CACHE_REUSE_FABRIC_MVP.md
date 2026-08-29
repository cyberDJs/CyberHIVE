# Cache & Reuse Fabric MVP

## Purpose

The Cache & Reuse Fabric prevents CyberHIVE from repeatedly doing the same work.

It caches not only final outputs, but also reusable runtime state, semantic query
results, artifact metadata and successful workflow plans.

## Design rule

Every high-frequency interface should support reuse.

CyberHIVE should ask:

> Is it cheaper, safer and fresh enough to reuse something we already know?

## Cache layers

| Layer | Purpose |
|---|---|
| Exact result cache | Identical canonical operation, identical relevant state, same result. |
| Semantic cache | Different wording, same canonical intent. |
| State cache | Latest computed runtime or inventory state. |
| Artifact cache | Metadata for derived artifacts such as embeddings or transcoded outputs. |
| Plan cache | Reusable workflow sequence for a known task type. |
| Execution Pattern Memory | Observed plan, cost and success rate from previous executions. |

## Cache key principle

A cache key is not just `hash(request)`.

It must include:

- operation,
- normalized input,
- relevant state,
- model version,
- configuration,
- permissions,
- dependency versions,
- revision.

This prevents fast but wrong answers.

## Security principle

Cacheability is determined by:

- determinism,
- reuse probability,
- computation cost,
- freshness tolerance,
- sensitivity,
- ACL and scope.

Secret data is not cacheable by default in the MVP. Sensitive data requires a
safe scope and explicit ACL.

## Resource cost, not cloud billing

The reuse cost model is based on:

- CPU time,
- GPU time,
- wall time,
- I/O bytes,
- network bytes,
- token count,
- tool calls.

It does not optimize directly for provider pricing.

## MVP limitations

- in-memory only,
- no distributed invalidation,
- no vector semantic similarity,
- no persistent cache backend,
- no automatic learning from all runtime executions yet.

## Next steps

- connect to Runtime Bus observations,
- store cache statistics as Observations,
- add persistent local cache backend,
- add semantic vector lookup,
- expose cache decisions to Wisdom and Optimizer,
- support materialized views for Knowledge and Inventory queries.
