from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from cyberhive_core.observations_forecasting import (
    ForecastDirection,
    ForecastEngine,
    Observation,
    ObservationCollector,
    ObservationKind,
    SchedulerHintAction,
    SchedulerHintEngine,
    TelemetryStore,
)


class ObservationsForecastingMvpTests(unittest.TestCase):
    def test_collector_flushes_to_store(self) -> None:
        store = TelemetryStore()
        collector = ObservationCollector(store, max_batch_size=2)
        collector.record_metric(source="node.a", name="cpu.load", value=0.4, resource_id="node.a")
        self.assertEqual(store.count, 0)
        collector.record_metric(source="node.a", name="cpu.load", value=0.5, resource_id="node.a")
        self.assertEqual(store.count, 2)
        self.assertEqual(collector.pending_count, 0)

    def test_boolean_metric_is_numeric(self) -> None:
        obs = Observation(source="camera", name="motion", value=True, kind=ObservationKind.METRIC)
        self.assertEqual(obs.numeric_value(), 1.0)

    def test_aggregate(self) -> None:
        store = TelemetryStore()
        now = datetime.now(timezone.utc)
        store.append_many(
            [
                Observation(source="node", name="gpu.temp", value=60, resource_id="node.a", timestamp=now - timedelta(seconds=3)),
                Observation(source="node", name="gpu.temp", value=70, resource_id="node.a", timestamp=now - timedelta(seconds=2)),
                Observation(source="node", name="gpu.temp", value=80, resource_id="node.a", timestamp=now - timedelta(seconds=1)),
            ]
        )
        aggregate = store.aggregate(name="gpu.temp", resource_id="node.a", window_seconds=60)
        self.assertEqual(aggregate.count, 3)
        self.assertEqual(aggregate.minimum, 60.0)
        self.assertEqual(aggregate.maximum, 80.0)
        self.assertEqual(aggregate.latest, 80.0)
        self.assertAlmostEqual(aggregate.average or 0.0, 70.0)

    def test_retention_compacts_old_observations(self) -> None:
        store = TelemetryStore(retention_seconds=10)
        now = datetime.now(timezone.utc)
        store.append(Observation(source="node", name="old", value=1, timestamp=now - timedelta(seconds=99)))
        self.assertEqual(store.count, 0)

    def test_forecast_detects_upward_trend(self) -> None:
        store = TelemetryStore(retention_seconds=3600)
        base = datetime.now(timezone.utc) - timedelta(minutes=5)
        for i in range(8):
            store.append(
                Observation(
                    source="node",
                    name="inference.queue_depth",
                    resource_id="node.a",
                    value=i,
                    timestamp=base + timedelta(seconds=i * 30),
                )
            )
        forecast = ForecastEngine(store).forecast_metric(name="inference.queue_depth", resource_id="node.a", horizon_seconds=300)
        self.assertEqual(forecast.direction, ForecastDirection.UP)
        self.assertGreater(forecast.predicted_value or 0.0, forecast.current_value or 0.0)

    def test_forecast_without_samples_is_low_confidence(self) -> None:
        forecast = ForecastEngine(TelemetryStore()).forecast_metric(name="missing", resource_id="node.a")
        self.assertEqual(forecast.samples, 0)
        self.assertEqual(forecast.confidence, 0.0)
        self.assertIsNone(forecast.predicted_value)

    def test_scheduler_hints_for_rising_pressure(self) -> None:
        store = TelemetryStore(retention_seconds=3600)
        base = datetime.now(timezone.utc) - timedelta(minutes=8)
        for i in range(12):
            store.append(
                Observation(
                    source="node",
                    name="inference.queue_depth",
                    resource_id="node.a",
                    value=2 + i,
                    timestamp=base + timedelta(seconds=i * 40),
                )
            )
        hints = SchedulerHintEngine(ForecastEngine(store)).hints_for_node(node_id="node.a", horizon_seconds=300)
        actions = {hint.action for hint in hints}
        self.assertIn(SchedulerHintAction.PREWARM, actions)
        self.assertIn(SchedulerHintAction.SHIFT_LOAD, actions)

    def test_validation_rejects_naive_timestamp(self) -> None:
        store = TelemetryStore()
        with self.assertRaises(ValueError):
            store.append(Observation(source="node", name="bad", value=1, timestamp=datetime(2026, 1, 1, 0, 0, 0)))


if __name__ == "__main__":
    unittest.main()
