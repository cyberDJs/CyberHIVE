# ADR-0010: Scheduler + Router MVP

## Status

Accepted

## Context

CyberHIVE already has runtime frames, inventory, data placement, data movement, cache reuse and forecasting. Forecasting produces scheduler hints, but there is no layer that turns those hints into routing decisions.

## Decision

Add a local dependency-free Scheduler + Router MVP with explicit route scoring.

The router will:

- reject unhealthy, disabled or incapable nodes,
- enforce resource headroom,
- preserve interactive VRAM reserve,
- apply forecast-derived hints,
- return an explainable route decision with alternatives.

## Consequences

Positive:

- forecasting can influence runtime behavior,
- decisions become explainable and testable,
- later execution layers can consume a stable route decision contract.

Negative:

- scoring is heuristic in the MVP,
- the router is local-only,
- there is no distributed locking or admission control yet.

## Follow-up

Patch 009 should integrate route decisions with `RuntimeBus` and `StateEngine`.
