"""CyberHIVE Observations, Telemetry and Forecasting MVP.

This module closes the first optimization loop:

* observations capture what happened,
* telemetry stores and aggregates the recent signal,
* forecasting predicts near-future pressure,
* scheduler hints translate forecasts into safe operational guidance.

The MVP is intentionally local and dependency-free. It does not attempt to be a
Prometheus replacement, a TSDB, or a distributed scheduler. It defines stable
semantics that later storage and routing layers can implement efficiently.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
import math
import statistics
import uuid
from typing import Any, Iterable, Mapping, Sequence


class ObservationKind(str, Enum):
    METRIC = "metric"
    EVENT = "event"
    STATE = "state"
    LOG = "log"
    TRACE = "trace"


class ObservationSeverity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ForecastDirection(str, Enum):
    DOWN = "down"
    FLAT = "flat"
    UP = "up"


class SchedulerHintAction(str, Enum):
    NONE = "none"
    PREWARM = "prewarm"
    SHIFT_LOAD = "shift_load"
    THROTTLE_BACKGROUND = "throttle_background"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    HOLD_CAPACITY = "hold_capacity"


@dataclass(frozen=True)
class Observation:
    """A recorded signal from runtime, node, service, skill or device.

    Observations are not truth. They are timestamped statements with provenance.
    Knowledge and Wisdom can later derive facts, policies or recommendations
    from them.
    """

    source: str
    name: str
    value: float | int | str | bool | None = None
    kind: ObservationKind = ObservationKind.METRIC
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: f"obs_{uuid.uuid4().hex[:20]}")
    resource_id: str | None = None
    unit: str | None = None
    severity: ObservationSeverity = ObservationSeverity.INFO
    confidence: float = 1.0
    tags: tuple[str, ...] = ()
    dimensions: Mapping[str, str] = field(default_factory=dict)
    payload: Mapping[str, Any] = field(default_factory=dict)
    ttl_seconds: int | None = None

    def numeric_value(self) -> float | None:
        if isinstance(self.value, bool):
            return 1.0 if self.value else 0.0
        if isinstance(self.value, (int, float)) and not isinstance(self.value, bool):
            if math.isfinite(float(self.value)):
                return float(self.value)
        return None

    def expired(self, now: datetime | None = None) -> bool:
        if self.ttl_seconds is None:
            return False
        current = now or datetime.now(timezone.utc)
        return current >= self.timestamp + timedelta(seconds=self.ttl_seconds)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "name": self.name,
            "value": self.value,
            "kind": self.kind.value,
            "timestamp": self.timestamp.isoformat(),
            "resource_id": self.resource_id,
            "unit": self.unit,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "tags": list(self.tags),
            "dimensions": dict(self.dimensions),
            "payload": dict(self.payload),
            "ttl_seconds": self.ttl_seconds,
        }


@dataclass(frozen=True)
class TelemetryAggregate:
    name: str
    resource_id: str | None
    window_seconds: int
    count: int
    minimum: float | None
    maximum: float | None
    average: float | None
    p95: float | None
    latest: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "resource_id": self.resource_id,
            "window_seconds": self.window_seconds,
            "count": self.count,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "average": self.average,
            "p95": self.p95,
            "latest": self.latest,
        }


@dataclass(frozen=True)
class Forecast:
    name: str
    resource_id: str | None
    horizon_seconds: int
    current_value: float | None
    predicted_value: float | None
    direction: ForecastDirection
    confidence: float
    reason: str
    samples: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "resource_id": self.resource_id,
            "horizon_seconds": self.horizon_seconds,
            "current_value": self.current_value,
            "predicted_value": self.predicted_value,
            "direction": self.direction.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "samples": self.samples,
        }


@dataclass(frozen=True)
class SchedulerHint:
    action: SchedulerHintAction
    target: str
    reason: str
    priority: int = 0
    forecast: Forecast | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "target": self.target,
            "reason": self.reason,
            "priority": self.priority,
            "forecast": self.forecast.as_dict() if self.forecast else None,
            "metadata": dict(self.metadata),
        }


class ObservationCollector:
    """Validates and forwards observations in batches."""

    def __init__(self, store: "TelemetryStore", max_batch_size: int = 128) -> None:
        if max_batch_size <= 0:
            raise ValueError("max_batch_size must be positive")
        self.store = store
        self.max_batch_size = max_batch_size
        self._buffer: list[Observation] = []

    def record(self, observation: Observation) -> None:
        _validate_observation(observation)
        self._buffer.append(observation)
        if len(self._buffer) >= self.max_batch_size:
            self.flush()

    def record_metric(
        self,
        *,
        source: str,
        name: str,
        value: float | int | bool,
        resource_id: str | None = None,
        unit: str | None = None,
        confidence: float = 1.0,
        timestamp: datetime | None = None,
        tags: Iterable[str] = (),
    ) -> Observation:
        observation = Observation(
            source=source,
            name=name,
            value=value,
            kind=ObservationKind.METRIC,
            timestamp=timestamp or datetime.now(timezone.utc),
            resource_id=resource_id,
            unit=unit,
            confidence=confidence,
            tags=tuple(tags),
        )
        self.record(observation)
        return observation

    def record_event(
        self,
        *,
        source: str,
        name: str,
        resource_id: str | None = None,
        severity: ObservationSeverity = ObservationSeverity.INFO,
        payload: Mapping[str, Any] | None = None,
    ) -> Observation:
        observation = Observation(
            source=source,
            name=name,
            kind=ObservationKind.EVENT,
            resource_id=resource_id,
            severity=severity,
            payload=dict(payload or {}),
        )
        self.record(observation)
        return observation

    def flush(self) -> int:
        if not self._buffer:
            return 0
        batch = self._buffer
        self._buffer = []
        self.store.append_many(batch)
        return len(batch)

    @property
    def pending_count(self) -> int:
        return len(self._buffer)


class TelemetryStore:
    """Small in-memory telemetry store for the MVP."""

    def __init__(self, retention_seconds: int = 3600) -> None:
        if retention_seconds <= 0:
            raise ValueError("retention_seconds must be positive")
        self.retention_seconds = retention_seconds
        self._observations: list[Observation] = []

    def append(self, observation: Observation) -> None:
        _validate_observation(observation)
        self._observations.append(observation)
        self.compact()

    def append_many(self, observations: Iterable[Observation]) -> None:
        for observation in observations:
            _validate_observation(observation)
            self._observations.append(observation)
        self.compact()

    def compact(self, now: datetime | None = None) -> int:
        current = now or datetime.now(timezone.utc)
        cutoff = current - timedelta(seconds=self.retention_seconds)
        before = len(self._observations)
        self._observations = [obs for obs in self._observations if obs.timestamp >= cutoff and not obs.expired(current)]
        return before - len(self._observations)

    def query(
        self,
        *,
        name: str | None = None,
        resource_id: str | None = None,
        kind: ObservationKind | None = None,
        since: datetime | None = None,
    ) -> list[Observation]:
        result: list[Observation] = []
        for obs in self._observations:
            if name is not None and obs.name != name:
                continue
            if resource_id is not None and obs.resource_id != resource_id:
                continue
            if kind is not None and obs.kind != kind:
                continue
            if since is not None and obs.timestamp < since:
                continue
            result.append(obs)
        return sorted(result, key=lambda obs: obs.timestamp)

    def numeric_series(
        self,
        *,
        name: str,
        resource_id: str | None = None,
        since: datetime | None = None,
    ) -> list[tuple[datetime, float]]:
        series: list[tuple[datetime, float]] = []
        for obs in self.query(name=name, resource_id=resource_id, kind=ObservationKind.METRIC, since=since):
            value = obs.numeric_value()
            if value is not None:
                series.append((obs.timestamp, value))
        return series

    def aggregate(self, *, name: str, resource_id: str | None = None, window_seconds: int = 300) -> TelemetryAggregate:
        now = datetime.now(timezone.utc)
        since = now - timedelta(seconds=window_seconds)
        values = [value for _, value in self.numeric_series(name=name, resource_id=resource_id, since=since)]
        if not values:
            return TelemetryAggregate(name, resource_id, window_seconds, 0, None, None, None, None, None)
        return TelemetryAggregate(
            name=name,
            resource_id=resource_id,
            window_seconds=window_seconds,
            count=len(values),
            minimum=min(values),
            maximum=max(values),
            average=sum(values) / len(values),
            p95=_percentile(values, 95),
            latest=values[-1],
        )

    @property
    def count(self) -> int:
        return len(self._observations)


class ForecastEngine:
    """Forecasts near-future metric pressure from recent telemetry."""

    def __init__(self, store: TelemetryStore) -> None:
        self.store = store

    def forecast_metric(
        self,
        *,
        name: str,
        resource_id: str | None = None,
        horizon_seconds: int = 300,
        lookback_seconds: int = 900,
    ) -> Forecast:
        if horizon_seconds <= 0:
            raise ValueError("horizon_seconds must be positive")
        if lookback_seconds <= 0:
            raise ValueError("lookback_seconds must be positive")
        since = datetime.now(timezone.utc) - timedelta(seconds=lookback_seconds)
        series = self.store.numeric_series(name=name, resource_id=resource_id, since=since)
        if not series:
            return Forecast(
                name=name,
                resource_id=resource_id,
                horizon_seconds=horizon_seconds,
                current_value=None,
                predicted_value=None,
                direction=ForecastDirection.FLAT,
                confidence=0.0,
                reason="no numeric samples",
                samples=0,
            )
        if len(series) == 1:
            current = series[-1][1]
            return Forecast(name, resource_id, horizon_seconds, current, current, ForecastDirection.FLAT, 0.2, "single sample", 1)

        xs = [(ts - series[0][0]).total_seconds() for ts, _ in series]
        ys = [value for _, value in series]
        slope = _linear_slope(xs, ys)
        current = ys[-1]
        predicted = current + slope * horizon_seconds
        delta = predicted - current
        noise = statistics.pstdev(ys) if len(ys) > 1 else 0.0
        scale = max(abs(current), abs(predicted), noise, 1.0)
        if abs(delta) / scale < 0.03:
            direction = ForecastDirection.FLAT
        elif delta > 0:
            direction = ForecastDirection.UP
        else:
            direction = ForecastDirection.DOWN
        trend_strength = min(1.0, abs(delta) / scale)
        sample_strength = min(1.0, len(series) / 12.0)
        confidence = max(0.05, min(0.95, 0.25 + 0.45 * sample_strength + 0.30 * trend_strength))
        return Forecast(
            name=name,
            resource_id=resource_id,
            horizon_seconds=horizon_seconds,
            current_value=current,
            predicted_value=predicted,
            direction=direction,
            confidence=confidence,
            reason=f"linear trend slope={slope:.6f}/s over {len(series)} samples",
            samples=len(series),
        )


class SchedulerHintEngine:
    """Converts forecasts into lightweight routing and capacity hints."""

    def __init__(self, forecast_engine: ForecastEngine) -> None:
        self.forecast_engine = forecast_engine

    def hints_for_node(
        self,
        *,
        node_id: str,
        horizon_seconds: int = 300,
        queue_high: float = 8.0,
        gpu_hot_percent: float = 82.0,
        vram_low_gb: float = 1.0,
    ) -> list[SchedulerHint]:
        hints: list[SchedulerHint] = []
        queue = self.forecast_engine.forecast_metric(
            name="inference.queue_depth",
            resource_id=node_id,
            horizon_seconds=horizon_seconds,
        )
        gpu = self.forecast_engine.forecast_metric(
            name="gpu.utilization_percent",
            resource_id=node_id,
            horizon_seconds=horizon_seconds,
        )
        vram = self.forecast_engine.forecast_metric(
            name="gpu.vram_free_gb",
            resource_id=node_id,
            horizon_seconds=horizon_seconds,
        )

        if queue.predicted_value is not None and queue.predicted_value >= queue_high and queue.direction == ForecastDirection.UP:
            hints.append(
                SchedulerHint(
                    action=SchedulerHintAction.PREWARM,
                    target=node_id,
                    reason="queue depth is predicted to rise above threshold",
                    priority=80,
                    forecast=queue,
                    metadata={"metric": "inference.queue_depth", "threshold": queue_high},
                )
            )
            hints.append(
                SchedulerHint(
                    action=SchedulerHintAction.SHIFT_LOAD,
                    target=node_id,
                    reason="route non-interactive work away before queue pressure peaks",
                    priority=70,
                    forecast=queue,
                )
            )

        if gpu.predicted_value is not None and gpu.predicted_value >= gpu_hot_percent:
            hints.append(
                SchedulerHint(
                    action=SchedulerHintAction.THROTTLE_BACKGROUND,
                    target=node_id,
                    reason="GPU utilization forecast is above safe interactive headroom",
                    priority=75,
                    forecast=gpu,
                    metadata={"metric": "gpu.utilization_percent", "threshold": gpu_hot_percent},
                )
            )

        if vram.predicted_value is not None and vram.predicted_value <= vram_low_gb:
            hints.append(
                SchedulerHint(
                    action=SchedulerHintAction.HOLD_CAPACITY,
                    target=node_id,
                    reason="predicted free VRAM is low; avoid aggressive model swaps",
                    priority=85,
                    forecast=vram,
                    metadata={"metric": "gpu.vram_free_gb", "threshold": vram_low_gb},
                )
            )

        return sorted(hints, key=lambda hint: hint.priority, reverse=True)


def _validate_observation(observation: Observation) -> None:
    if not observation.source:
        raise ValueError("observation.source is required")
    if not observation.name:
        raise ValueError("observation.name is required")
    if not 0.0 <= observation.confidence <= 1.0:
        raise ValueError("observation.confidence must be between 0 and 1")
    if observation.timestamp.tzinfo is None:
        raise ValueError("observation.timestamp must be timezone-aware")


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        raise ValueError("values must not be empty")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (len(ordered) - 1) * (percentile / 100.0)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return ordered[int(rank)]
    weight = rank - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _linear_slope(xs: Sequence[float], ys: Sequence[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
