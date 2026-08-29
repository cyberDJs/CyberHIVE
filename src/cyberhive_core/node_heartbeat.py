"""CyberHIVE Node Heartbeat & Capability Sync MVP.

This module turns enrolled node sessions into fresh schedulable node state.

The MVP is intentionally local and dependency-free. It does not open sockets,
perform discovery or trust unauthenticated telemetry. It gives CyberHIVE the
controller-side contracts for:

* authenticated heartbeat ingestion,
* monotonic heartbeat sequencing,
* capability and metric snapshots,
* stale/expired liveness decisions,
* conversion into Scheduler/Router NodeState,
* optional Runtime Bus observation publishing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Iterable, Mapping
import uuid

try:  # Optional runtime bus integration from Patch 002.
    from .hiveframe import Operation, OperationType
except Exception:  # pragma: no cover
    Operation = None  # type: ignore[assignment]
    OperationType = None  # type: ignore[assignment]

try:  # Optional scheduler integration from Patch 008.
    from .scheduler_router import NodeState
except Exception:  # pragma: no cover
    NodeState = None  # type: ignore[assignment]

try:  # Optional node agent descriptor integration from Patch 013.
    from .node_agent import AgentActionType, NodeDescriptor
except Exception:  # pragma: no cover
    AgentActionType = None  # type: ignore[assignment]
    NodeDescriptor = None  # type: ignore[assignment]

try:  # Optional identity registry integration from Patch 014.
    from .node_identity import NodeIdentityRegistry, TrustState
except Exception:  # pragma: no cover
    NodeIdentityRegistry = None  # type: ignore[assignment]
    TrustState = None  # type: ignore[assignment]


class HeartbeatStatus(str, Enum):
    ACCEPTED = "accepted"
    DUPLICATE = "duplicate"
    DENIED = "denied"
    INVALID = "invalid"


class LivenessStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    STALE = "stale"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class NodeHeartbeatError(RuntimeError):
    """Raised when heartbeat operations are invalid."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _age_seconds(at: datetime, now: datetime | None = None) -> float:
    return max(0.0, ((now or _now()) - at).total_seconds())


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _finite_float(value: Any, *, field_name: str, minimum: float | None = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise NodeHeartbeatError(f"{field_name} must be numeric") from exc
    if not math.isfinite(number):
        raise NodeHeartbeatError(f"{field_name} must be finite")
    if minimum is not None and number < minimum:
        raise NodeHeartbeatError(f"{field_name} must be >= {minimum}")
    return number


def _int_metric(value: Any, *, field_name: str, minimum: int = 0) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise NodeHeartbeatError(f"{field_name} must be integer") from exc
    if number < minimum:
        raise NodeHeartbeatError(f"{field_name} must be >= {minimum}")
    return number


@dataclass(frozen=True)
class NodeHeartbeat:
    """Node telemetry sample sent by an enrolled worker node."""

    node_id: str
    sequence: int
    session_id: str | None = None
    observed_at: datetime = field(default_factory=_now)
    capabilities: tuple[str, ...] = ()
    labels: Mapping[str, str] = field(default_factory=dict)
    cpu_cores: float = 0.0
    free_cpu_cores: float = 0.0
    memory_gb: float = 0.0
    free_memory_gb: float = 0.0
    gpu_vram_gb: float = 0.0
    free_vram_gb: float = 0.0
    gpu_utilization: float = 0.0
    queue_depth: int = 0
    latency_ms: float = 0.0
    data_locality: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: f"hb_{uuid.uuid4().hex[:20]}")

    @classmethod
    def from_metrics(
        cls,
        *,
        node_id: str,
        sequence: int,
        session_id: str | None = None,
        metrics: Mapping[str, Any] | None = None,
        capabilities: Iterable[str] = (),
        labels: Mapping[str, str] | None = None,
        data_locality: Iterable[str] = (),
        metadata: Mapping[str, Any] | None = None,
        observed_at: datetime | None = None,
    ) -> "NodeHeartbeat":
        values = dict(metrics or {})
        return cls(
            node_id=node_id,
            sequence=sequence,
            session_id=session_id,
            observed_at=observed_at or _now(),
            capabilities=tuple(str(item) for item in capabilities),
            labels=labels or {},
            cpu_cores=_finite_float(values.get("cpu_cores", 0.0), field_name="cpu_cores"),
            free_cpu_cores=_finite_float(values.get("free_cpu_cores", 0.0), field_name="free_cpu_cores"),
            memory_gb=_finite_float(values.get("memory_gb", 0.0), field_name="memory_gb"),
            free_memory_gb=_finite_float(values.get("free_memory_gb", 0.0), field_name="free_memory_gb"),
            gpu_vram_gb=_finite_float(values.get("gpu_vram_gb", 0.0), field_name="gpu_vram_gb"),
            free_vram_gb=_finite_float(values.get("free_vram_gb", 0.0), field_name="free_vram_gb"),
            gpu_utilization=_finite_float(values.get("gpu_utilization", 0.0), field_name="gpu_utilization", minimum=0.0),
            queue_depth=_int_metric(values.get("queue_depth", 0), field_name="queue_depth"),
            latency_ms=_finite_float(values.get("latency_ms", 0.0), field_name="latency_ms"),
            data_locality=tuple(str(item) for item in data_locality),
            metadata=metadata or {},
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "sequence": self.sequence,
            "session_id": self.session_id,
            "observed_at": self.observed_at.isoformat(),
            "capabilities": list(self.capabilities),
            "labels": dict(self.labels),
            "metrics": {
                "cpu_cores": self.cpu_cores,
                "free_cpu_cores": self.free_cpu_cores,
                "memory_gb": self.memory_gb,
                "free_memory_gb": self.free_memory_gb,
                "gpu_vram_gb": self.gpu_vram_gb,
                "free_vram_gb": self.free_vram_gb,
                "gpu_utilization": self.gpu_utilization,
                "queue_depth": self.queue_depth,
                "latency_ms": self.latency_ms,
            },
            "data_locality": list(self.data_locality),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class CapabilitySnapshot:
    """Latest controller-side view derived from a heartbeat."""

    node_id: str
    heartbeat_id: str
    sequence: int
    capabilities: tuple[str, ...]
    labels: Mapping[str, str]
    cpu_cores: float
    free_cpu_cores: float
    memory_gb: float
    free_memory_gb: float
    gpu_vram_gb: float
    free_vram_gb: float
    gpu_utilization: float
    queue_depth: int
    latency_ms: float
    data_locality: tuple[str, ...]
    observed_at: datetime
    updated_at: datetime = field(default_factory=_now)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def liveness(self, *, stale_after_seconds: int, expire_after_seconds: int, now: datetime | None = None) -> "NodeLiveness":
        current = now or _now()
        age = _age_seconds(self.observed_at, current)
        if age >= expire_after_seconds:
            status = LivenessStatus.EXPIRED
            healthy = False
            reason = "heartbeat expired"
        elif age >= stale_after_seconds:
            status = LivenessStatus.STALE
            healthy = False
            reason = "heartbeat stale"
        elif self.gpu_utilization >= 0.95 or self.queue_depth >= 20:
            status = LivenessStatus.DEGRADED
            healthy = True
            reason = "node is alive but under pressure"
        else:
            status = LivenessStatus.HEALTHY
            healthy = True
            reason = "heartbeat fresh"
        return NodeLiveness(
            node_id=self.node_id,
            status=status,
            healthy=healthy,
            reason=reason,
            age_seconds=age,
            last_sequence=self.sequence,
            last_seen_at=self.observed_at,
            evaluated_at=current,
        )

    def to_node_state(self, *, healthy: bool = True):
        if NodeState is None:  # pragma: no cover
            raise NodeHeartbeatError("scheduler_router.NodeState is not available")
        return NodeState(
            id=self.node_id,
            enabled=True,
            healthy=healthy,
            capabilities=self.capabilities,
            labels=dict(self.labels),
            cpu_cores=self.cpu_cores,
            free_cpu_cores=self.free_cpu_cores,
            memory_gb=self.memory_gb,
            free_memory_gb=self.free_memory_gb,
            gpu_vram_gb=self.gpu_vram_gb,
            free_vram_gb=self.free_vram_gb,
            gpu_utilization=self.gpu_utilization,
            queue_depth=self.queue_depth,
            latency_ms=self.latency_ms,
            data_locality=self.data_locality,
            updated_at=self.updated_at,
        )

    def to_node_descriptor(self, *, healthy: bool = True):
        if NodeDescriptor is None or AgentActionType is None:  # pragma: no cover
            raise NodeHeartbeatError("node_agent.NodeDescriptor is not available")
        allowed = [AgentActionType.HEALTH_CHECK, AgentActionType.NOOP]
        if "model.prewarm" in self.capabilities:
            allowed.append(AgentActionType.PREWARM_MODEL)
        if "data.move" in self.capabilities:
            allowed.append(AgentActionType.DATA_MOVE)
        if "cache.prime" in self.capabilities:
            allowed.append(AgentActionType.CACHE_PRIME)
        return NodeDescriptor(
            id=self.node_id,
            enabled=True,
            healthy=healthy,
            capabilities=self.capabilities,
            allowed_actions=tuple(allowed),
            labels=dict(self.labels),
            metadata={**dict(self.metadata), "heartbeat_id": self.heartbeat_id, "sequence": self.sequence},
            updated_at=self.updated_at,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "heartbeat_id": self.heartbeat_id,
            "sequence": self.sequence,
            "capabilities": list(self.capabilities),
            "labels": dict(self.labels),
            "metrics": {
                "cpu_cores": self.cpu_cores,
                "free_cpu_cores": self.free_cpu_cores,
                "memory_gb": self.memory_gb,
                "free_memory_gb": self.free_memory_gb,
                "gpu_vram_gb": self.gpu_vram_gb,
                "free_vram_gb": self.free_vram_gb,
                "gpu_utilization": self.gpu_utilization,
                "queue_depth": self.queue_depth,
                "latency_ms": self.latency_ms,
            },
            "data_locality": list(self.data_locality),
            "observed_at": self.observed_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class NodeLiveness:
    node_id: str
    status: LivenessStatus
    healthy: bool
    reason: str
    age_seconds: float
    last_sequence: int | None
    last_seen_at: datetime | None
    evaluated_at: datetime

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": self.status.value,
            "healthy": self.healthy,
            "reason": self.reason,
            "age_seconds": self.age_seconds,
            "last_sequence": self.last_sequence,
            "last_seen_at": _iso(self.last_seen_at),
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass(frozen=True)
class HeartbeatDecision:
    status: HeartbeatStatus
    node_id: str
    heartbeat_id: str | None
    reason: str
    snapshot: CapabilitySnapshot | None = None
    liveness: NodeLiveness | None = None
    findings: tuple[str, ...] = ()
    decided_at: datetime = field(default_factory=_now)

    @property
    def accepted(self) -> bool:
        return self.status in {HeartbeatStatus.ACCEPTED, HeartbeatStatus.DUPLICATE}

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "node_id": self.node_id,
            "heartbeat_id": self.heartbeat_id,
            "reason": self.reason,
            "snapshot": self.snapshot.as_dict() if self.snapshot else None,
            "liveness": self.liveness.as_dict() if self.liveness else None,
            "findings": list(self.findings),
            "decided_at": self.decided_at.isoformat(),
        }


class NodeHeartbeatStore:
    """Controller-side heartbeat store and capability sync surface."""

    def __init__(
        self,
        *,
        identity_registry: Any | None = None,
        runtime_bus: Any | None = None,
        stale_after_seconds: int = 60,
        expire_after_seconds: int = 300,
        max_future_skew_seconds: int = 30,
        require_session: bool = True,
    ) -> None:
        if stale_after_seconds <= 0:
            raise NodeHeartbeatError("stale_after_seconds must be positive")
        if expire_after_seconds <= stale_after_seconds:
            raise NodeHeartbeatError("expire_after_seconds must be greater than stale_after_seconds")
        self.identity_registry = identity_registry
        self.runtime_bus = runtime_bus
        self.stale_after_seconds = stale_after_seconds
        self.expire_after_seconds = expire_after_seconds
        self.max_future_skew_seconds = max_future_skew_seconds
        self.require_session = require_session
        self._heartbeats: dict[str, NodeHeartbeat] = {}
        self._snapshots: dict[str, CapabilitySnapshot] = {}
        self.decisions: list[HeartbeatDecision] = []

    def ingest(self, heartbeat: NodeHeartbeat, *, session_token: str | None = None, now: datetime | None = None) -> HeartbeatDecision:
        current = now or _now()
        try:
            self._validate(heartbeat, session_token=session_token, now=current)
        except NodeHeartbeatError as exc:
            return self._record(HeartbeatDecision(HeartbeatStatus.DENIED, heartbeat.node_id, heartbeat.id, str(exc)))

        previous = self._heartbeats.get(heartbeat.node_id)
        if previous and heartbeat.sequence < previous.sequence:
            return self._record(HeartbeatDecision(HeartbeatStatus.DENIED, heartbeat.node_id, heartbeat.id, "heartbeat sequence moved backwards"))
        if previous and heartbeat.sequence == previous.sequence:
            snapshot = self._snapshots.get(heartbeat.node_id)
            liveness = snapshot.liveness(stale_after_seconds=self.stale_after_seconds, expire_after_seconds=self.expire_after_seconds, now=current) if snapshot else None
            return self._record(HeartbeatDecision(HeartbeatStatus.DUPLICATE, heartbeat.node_id, heartbeat.id, "duplicate heartbeat sequence", snapshot=snapshot, liveness=liveness))

        findings = _heartbeat_findings(heartbeat)
        snapshot = CapabilitySnapshot(
            node_id=heartbeat.node_id,
            heartbeat_id=heartbeat.id,
            sequence=heartbeat.sequence,
            capabilities=heartbeat.capabilities,
            labels=dict(heartbeat.labels),
            cpu_cores=heartbeat.cpu_cores,
            free_cpu_cores=heartbeat.free_cpu_cores,
            memory_gb=heartbeat.memory_gb,
            free_memory_gb=heartbeat.free_memory_gb,
            gpu_vram_gb=heartbeat.gpu_vram_gb,
            free_vram_gb=heartbeat.free_vram_gb,
            gpu_utilization=min(1.0, heartbeat.gpu_utilization),
            queue_depth=heartbeat.queue_depth,
            latency_ms=heartbeat.latency_ms,
            data_locality=heartbeat.data_locality,
            observed_at=heartbeat.observed_at,
            updated_at=current,
            metadata=dict(heartbeat.metadata),
        )
        self._heartbeats[heartbeat.node_id] = heartbeat
        self._snapshots[heartbeat.node_id] = snapshot
        liveness = snapshot.liveness(stale_after_seconds=self.stale_after_seconds, expire_after_seconds=self.expire_after_seconds, now=current)
        decision = HeartbeatDecision(HeartbeatStatus.ACCEPTED, heartbeat.node_id, heartbeat.id, "heartbeat accepted", snapshot=snapshot, liveness=liveness, findings=tuple(findings))
        self._publish(decision)
        return self._record(decision)

    def last(self, node_id: str) -> NodeHeartbeat | None:
        return self._heartbeats.get(node_id)

    def snapshot(self, node_id: str) -> CapabilitySnapshot | None:
        return self._snapshots.get(node_id)

    def require_snapshot(self, node_id: str) -> CapabilitySnapshot:
        snapshot = self.snapshot(node_id)
        if snapshot is None:
            raise NodeHeartbeatError(f"unknown heartbeat snapshot: {node_id}")
        return snapshot

    def liveness(self, node_id: str, *, now: datetime | None = None) -> NodeLiveness:
        snapshot = self.snapshot(node_id)
        if snapshot is None:
            return NodeLiveness(node_id, LivenessStatus.UNKNOWN, False, "no heartbeat seen", 0.0, None, None, now or _now())
        return snapshot.liveness(stale_after_seconds=self.stale_after_seconds, expire_after_seconds=self.expire_after_seconds, now=now)

    def list_liveness(self, *, now: datetime | None = None) -> tuple[NodeLiveness, ...]:
        return tuple(self.liveness(node_id, now=now) for node_id in sorted(self._snapshots))

    def stale_nodes(self, *, now: datetime | None = None) -> tuple[str, ...]:
        return tuple(item.node_id for item in self.list_liveness(now=now) if item.status in {LivenessStatus.STALE, LivenessStatus.EXPIRED})

    def to_scheduler_nodes(self, *, now: datetime | None = None) -> tuple[Any, ...]:
        nodes = []
        for snapshot in self._snapshots.values():
            liveness = snapshot.liveness(stale_after_seconds=self.stale_after_seconds, expire_after_seconds=self.expire_after_seconds, now=now)
            nodes.append(snapshot.to_node_state(healthy=liveness.healthy))
        return tuple(nodes)

    def sync_router(self, router: Any, *, now: datetime | None = None) -> None:
        for node in self.to_scheduler_nodes(now=now):
            router.upsert_node(node)

    def _validate(self, heartbeat: NodeHeartbeat, *, session_token: str | None, now: datetime) -> None:
        if not heartbeat.node_id:
            raise NodeHeartbeatError("node_id is required")
        if heartbeat.sequence < 0:
            raise NodeHeartbeatError("sequence must be >= 0")
        if heartbeat.observed_at.tzinfo is None:
            raise NodeHeartbeatError("observed_at must be timezone-aware")
        future_skew = (heartbeat.observed_at - now).total_seconds()
        if future_skew > self.max_future_skew_seconds:
            raise NodeHeartbeatError("heartbeat observed_at is too far in the future")
        _validate_metrics(heartbeat)
        if self.identity_registry is not None:
            identity = self.identity_registry.get(heartbeat.node_id)
            if identity is None:
                raise NodeHeartbeatError("unknown node identity")
            if not identity.is_allowed():
                raise NodeHeartbeatError(f"node identity is not enrolled: {getattr(identity.trust_state, 'value', identity.trust_state)}")
            if self.require_session:
                if not heartbeat.session_id:
                    raise NodeHeartbeatError("session_id is required")
                if not session_token:
                    raise NodeHeartbeatError("session_token is required")
                if not self.identity_registry.verify_session(heartbeat.session_id, heartbeat.node_id, session_token):
                    raise NodeHeartbeatError("invalid node session")

    def _publish(self, decision: HeartbeatDecision) -> None:
        if self.runtime_bus is None or Operation is None or OperationType is None:
            return
        self.runtime_bus.publish(
            Operation.from_json_payload(
                OperationType.OBSERVE,
                f"node.heartbeat.{decision.node_id}",
                decision.as_dict(),
            )
        )

    def _record(self, decision: HeartbeatDecision) -> HeartbeatDecision:
        self.decisions.append(decision)
        return decision


def _validate_metrics(heartbeat: NodeHeartbeat) -> None:
    for field_name in (
        "cpu_cores",
        "free_cpu_cores",
        "memory_gb",
        "free_memory_gb",
        "gpu_vram_gb",
        "free_vram_gb",
        "gpu_utilization",
        "latency_ms",
    ):
        _finite_float(getattr(heartbeat, field_name), field_name=field_name)
    _int_metric(heartbeat.queue_depth, field_name="queue_depth")
    if heartbeat.free_cpu_cores > heartbeat.cpu_cores and heartbeat.cpu_cores > 0:
        raise NodeHeartbeatError("free_cpu_cores cannot exceed cpu_cores")
    if heartbeat.free_memory_gb > heartbeat.memory_gb and heartbeat.memory_gb > 0:
        raise NodeHeartbeatError("free_memory_gb cannot exceed memory_gb")
    if heartbeat.free_vram_gb > heartbeat.gpu_vram_gb and heartbeat.gpu_vram_gb > 0:
        raise NodeHeartbeatError("free_vram_gb cannot exceed gpu_vram_gb")


def _heartbeat_findings(heartbeat: NodeHeartbeat) -> list[str]:
    findings: list[str] = []
    if not heartbeat.capabilities:
        findings.append("heartbeat declares no capabilities")
    if heartbeat.gpu_utilization >= 0.95:
        findings.append("gpu utilization is near saturation")
    if heartbeat.queue_depth >= 20:
        findings.append("queue depth is high")
    return findings
