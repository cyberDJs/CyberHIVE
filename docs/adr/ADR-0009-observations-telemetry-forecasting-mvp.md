# ADR-0009: Observations, Telemetry and Forecasting MVP

## Status

Accepted for MVP seed.

## Context

CyberHIVE needs to adapt runtime routing and data placement before overload
happens. Runtime Bus, Data Fabric, Data Mover and Cache Reuse already provide
execution and optimization primitives, but the system also needs a feedback loop.

## Decision

Add a local dependency-free observations and forecasting layer:

- observations are appendable signals, not final truth,
- telemetry aggregation is local and bounded by retention,
- forecasts use simple explainable linear trend logic,
- scheduler guidance is emitted as hints, not automatic destructive action.

## Consequences

Positive:

- Predictive scheduling becomes possible.
- Runtime pressure can be detected before it becomes an incident.
- Future Wisdom rules can use measured outcomes.

Trade-offs:

- Forecasting is intentionally primitive.
- No distributed metrics backend yet.
- Hints need later integration with the actual scheduler/router.
