# CyberHIVE Patch 007 — Observations + Telemetry + Forecasting MVP

## Purpose

Patch 007 adds the first closed-loop signal layer:

```text
Observations -> TelemetryStore -> ForecastEngine -> SchedulerHintEngine
```

This makes CyberHIVE able to collect runtime signals, aggregate them and produce
near-future scheduler hints before the system is already overloaded.

## Components

- `Observation` — timestamped signal with provenance.
- `ObservationCollector` — validates and micro-batches observations.
- `TelemetryStore` — local in-memory MVP telemetry store with retention.
- `TelemetryAggregate` — count/min/max/average/p95/latest over a window.
- `ForecastEngine` — simple near-future linear trend forecast.
- `SchedulerHintEngine` — translates forecasts into routing/capacity hints.

## Non-goals

- Replacing Prometheus, OpenTelemetry or a TSDB.
- Distributed consensus.
- Production scheduling.
- Automatic scaling against paid cloud APIs.

## Scheduler hints

The MVP can emit:

- `prewarm`
- `shift_load`
- `throttle_background`
- `hold_capacity`
- `scale_up`
- `scale_down`
- `none`

These are hints, not mandatory actions. Policy, Wisdom and operator approval can
still override them.

## Safety

Observations are not treated as truth. They are signals. Derived Knowledge or
Wisdom must keep provenance and confidence.
