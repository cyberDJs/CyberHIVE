#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cyberhive_core.observations_forecasting import (
    ForecastDirection,
    ForecastEngine,
    ObservationCollector,
    SchedulerHintAction,
    SchedulerHintEngine,
    TelemetryStore,
)


def main() -> None:
    store = TelemetryStore(retention_seconds=3600)
    collector = ObservationCollector(store, max_batch_size=16)
    base = datetime.now(timezone.utc) - timedelta(minutes=10)
    for i in range(12):
        collector.record_metric(
            source="node.alpha",
            resource_id="node.alpha",
            name="inference.queue_depth",
            value=i,
            timestamp=base + timedelta(seconds=i * 30),
        )
        collector.record_metric(
            source="node.alpha",
            resource_id="node.alpha",
            name="gpu.utilization_percent",
            value=40 + i * 4,
            timestamp=base + timedelta(seconds=i * 30),
        )
    collector.flush()

    aggregate = store.aggregate(name="inference.queue_depth", resource_id="node.alpha", window_seconds=1800)
    assert aggregate.count == 12
    assert aggregate.latest == 11.0

    forecast = ForecastEngine(store).forecast_metric(
        name="inference.queue_depth",
        resource_id="node.alpha",
        horizon_seconds=300,
        lookback_seconds=1800,
    )
    assert forecast.direction == ForecastDirection.UP
    assert forecast.predicted_value is not None and forecast.predicted_value > forecast.current_value

    hints = SchedulerHintEngine(ForecastEngine(store)).hints_for_node(node_id="node.alpha", horizon_seconds=300)
    assert any(hint.action == SchedulerHintAction.PREWARM for hint in hints)

    print("OK: Observations + Telemetry + Forecasting MVP validation passed")
    print(f"observations={store.count} aggregate_count={aggregate.count}")
    print(f"forecast={forecast.direction.value} current={forecast.current_value:.2f} predicted={forecast.predicted_value:.2f}")
    print("hints=" + ", ".join(f"{hint.action.value}:{hint.priority}" for hint in hints))


if __name__ == "__main__":
    main()
