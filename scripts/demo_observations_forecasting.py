#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cyberhive_core.observations_forecasting import (
    ForecastEngine,
    ObservationCollector,
    SchedulerHintEngine,
    TelemetryStore,
)


def main() -> None:
    store = TelemetryStore(retention_seconds=3600)
    collector = ObservationCollector(store, max_batch_size=8)
    base = datetime.now(timezone.utc) - timedelta(minutes=8)

    for i, queue_depth in enumerate([1, 1, 2, 3, 5, 7, 9, 11]):
        timestamp = base + timedelta(seconds=i * 60)
        collector.record_metric(
            source="runtime.node-alpha",
            resource_id="node.alpha",
            name="inference.queue_depth",
            value=queue_depth,
            timestamp=timestamp,
        )
        collector.record_metric(
            source="runtime.node-alpha",
            resource_id="node.alpha",
            name="gpu.utilization_percent",
            value=42 + i * 6,
            unit="percent",
            timestamp=timestamp,
        )
        collector.record_metric(
            source="runtime.node-alpha",
            resource_id="node.alpha",
            name="gpu.vram_free_gb",
            value=3.6 - i * 0.28,
            unit="GB",
            timestamp=timestamp,
        )
    collector.flush()

    forecast_engine = ForecastEngine(store)
    hint_engine = SchedulerHintEngine(forecast_engine)

    queue = forecast_engine.forecast_metric(
        name="inference.queue_depth",
        resource_id="node.alpha",
        horizon_seconds=300,
        lookback_seconds=1200,
    )
    print(f"queue forecast: {queue.direction.value} current={queue.current_value:.2f} predicted={queue.predicted_value:.2f} confidence={queue.confidence:.2f}")

    for hint in hint_engine.hints_for_node(node_id="node.alpha", horizon_seconds=300):
        print(f"hint: {hint.action.value} priority={hint.priority} target={hint.target}")
        print(f"  {hint.reason}")


if __name__ == "__main__":
    main()
