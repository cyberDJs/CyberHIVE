"""Adaptive Data Fabric MVP.

This module keeps Patch 002 compatibility while adding a behavior-driven data
placement layer. It intentionally optimizes for runtime behavior, locality,
latency, reconstruction cost and sensitivity -- not cloud billing categories.
"""
from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


class StorageTier(str, Enum):
    L1_RAM = "l1_ram"
    L2_LOCAL_NVME = "l2_local_nvme"
    L3_LOCAL_SSD = "l3_local_ssd"
    L4_HDD_RAID = "l4_hdd_raid"
    L5_NAS_DISTRIBUTED = "l5_nas_distributed"
    L6_ARCHIVE_REMOTE = "l6_archive_remote"


class PlacementAction(str, Enum):
    KEEP = "keep"
    PROMOTE = "promote"
    DEMOTE = "demote"
    REPLICATE = "replicate"
    MOVE = "move"
    EVICT = "evict"


_TIER_ORDER = {
    StorageTier.L1_RAM: 1,
    StorageTier.L2_LOCAL_NVME: 2,
    StorageTier.L3_LOCAL_SSD: 3,
    StorageTier.L4_HDD_RAID: 4,
    StorageTier.L5_NAS_DISTRIBUTED: 5,
    StorageTier.L6_ARCHIVE_REMOTE: 6,
}


@dataclass
class DataObject:
    """A logical data object known to CyberHIVE Data Fabric.

    Patch 002 fields remain supported so older validation scripts continue to
    work. New fields allow lifecycle planning, locality and placement state.
    """

    id: str
    size_bytes: int
    reads_1h: int = 0
    reads_24h: int = 0
    latency_requirement: str = "low"
    exclusivity: str = "shared"
    sensitivity: str = "internal"
    predicted_use: float = 0.0
    reconstruction_seconds: float | None = None
    preferred_nodes: list[str] = field(default_factory=list)
    current_tier: StorageTier | None = None
    current_devices: list[str] = field(default_factory=list)
    replicas: int = 1
    write_frequency: str = "low"
    last_read_age_seconds: float | None = None
    content_hash: str | None = None
    owner_resource_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PlacementDecision:
    tier: StorageTier
    temperature: float
    replicas: int
    reason: str
    action: PlacementAction = PlacementAction.KEEP
    target_devices: tuple[str, ...] = ()
    score: float = 0.0


@dataclass(frozen=True)
class StorageDevice:
    id: str
    tier: StorageTier
    node_id: str
    capacity_bytes: int
    used_bytes: int = 0
    online: bool = True
    encrypted: bool = True
    labels: dict[str, str] = field(default_factory=dict)

    @property
    def free_bytes(self) -> int:
        return max(0, self.capacity_bytes - self.used_bytes)

    @property
    def pressure(self) -> float:
        if self.capacity_bytes <= 0:
            return 1.0
        return max(0.0, min(1.0, self.used_bytes / self.capacity_bytes))

    def can_store(self, size_bytes: int) -> bool:
        return self.online and self.free_bytes >= size_bytes


@dataclass(frozen=True)
class AccessRecord:
    object_id: str
    kind: str = "read"  # read/write/prefetch/evict
    node_id: str | None = None
    timestamp_ns: int = field(default_factory=time.time_ns)
    size_bytes: int = 0


@dataclass(frozen=True)
class DataMove:
    object_id: str
    action: PlacementAction
    from_tier: StorageTier | None
    to_tier: StorageTier
    replicas: int
    target_devices: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class DataProfile:
    object_id: str
    reads_1h: int
    reads_24h: int
    writes_1h: int
    last_read_age_seconds: float | None
    preferred_nodes: tuple[str, ...]


class PlacementEngine:
    """Performance-first placement engine.

    The score intentionally avoids direct monetary pricing. It optimizes for
    data behavior: frequency, recency, predicted use, latency, fanout, locality,
    reconstruction penalty and safety constraints.
    """

    latency_weights = {
        "low": 0.05,
        "medium": 0.15,
        "high": 0.25,
        "critical": 0.35,
    }
    exclusivity_weights = {
        "single_consumer": 0.0,
        "shared": 0.10,
        "high_fanout": 0.20,
    }
    write_weights = {
        "none": 0.0,
        "low": 0.03,
        "medium": 0.08,
        "high": 0.12,
    }

    def temperature(self, data: DataObject) -> float:
        frequency = min(0.35, (data.reads_1h / 100) * 0.25 + (data.reads_24h / 1000) * 0.10)
        predicted = max(0.0, min(0.25, data.predicted_use * 0.25))
        latency = self.latency_weights.get(data.latency_requirement, 0.05)
        fanout = self.exclusivity_weights.get(data.exclusivity, 0.10)
        writes = self.write_weights.get(data.write_frequency, 0.03)
        recency = 0.0
        if data.last_read_age_seconds is not None:
            if data.last_read_age_seconds <= 60:
                recency = 0.12
            elif data.last_read_age_seconds <= 3600:
                recency = 0.08
            elif data.last_read_age_seconds <= 86400:
                recency = 0.03
        reconstruction = 0.0
        if data.reconstruction_seconds is not None:
            reconstruction = min(0.25, data.reconstruction_seconds / 3600 * 0.25)
        score = frequency + predicted + latency + fanout + writes + recency + reconstruction
        return round(max(0.0, min(1.0, score)), 4)

    def decide(self, data: DataObject, devices: Iterable[StorageDevice] | None = None) -> PlacementDecision:
        temp = self.temperature(data)
        tier = self._tier_for(data, temp)
        replicas = self._replicas_for(data)
        targets = self._choose_devices(data=data, tier=tier, replicas=replicas, devices=list(devices or []))
        action = self._action_for(data.current_tier, tier, current_replicas=data.replicas, target_replicas=replicas)
        reason = self._reason_for(data=data, temperature=temp, tier=tier, action=action)
        return PlacementDecision(tier=tier, temperature=temp, replicas=replicas, reason=reason, action=action, target_devices=targets, score=temp)

    def _tier_for(self, data: DataObject, temperature: float) -> StorageTier:
        if data.sensitivity == "secret":
            # Secret data remains local and reasonably fast by default. The aim
            # is security and predictable access, not archival convenience.
            return StorageTier.L2_LOCAL_NVME
        if data.sensitivity == "sensitive" and temperature < 0.15:
            return StorageTier.L4_HDD_RAID
        if temperature >= 0.85:
            return StorageTier.L1_RAM
        if temperature >= 0.60:
            return StorageTier.L2_LOCAL_NVME
        if temperature >= 0.35:
            return StorageTier.L3_LOCAL_SSD
        if temperature >= 0.15:
            return StorageTier.L4_HDD_RAID
        return StorageTier.L6_ARCHIVE_REMOTE

    def _replicas_for(self, data: DataObject) -> int:
        replicas = 1
        if data.exclusivity == "high_fanout" or data.reads_24h > 500:
            replicas = 2
        if data.reads_24h > 2000 and data.sensitivity == "public":
            replicas = 3
        if data.sensitivity in {"sensitive", "secret"}:
            replicas = min(replicas, 1)
        return replicas

    def _choose_devices(
        self,
        *,
        data: DataObject,
        tier: StorageTier,
        replicas: int,
        devices: list[StorageDevice],
    ) -> tuple[str, ...]:
        if not devices:
            return ()
        candidates = [device for device in devices if device.tier == tier and device.can_store(data.size_bytes)]
        if data.sensitivity in {"sensitive", "secret"}:
            candidates = [device for device in candidates if device.encrypted]
        candidates.sort(
            key=lambda device: (
                0 if device.node_id in data.preferred_nodes else 1,
                device.pressure,
                device.id,
            )
        )
        return tuple(device.id for device in candidates[:replicas])

    def _action_for(
        self,
        current: StorageTier | None,
        target: StorageTier,
        *,
        current_replicas: int,
        target_replicas: int,
    ) -> PlacementAction:
        if current is None:
            return PlacementAction.MOVE
        if current == target and current_replicas == target_replicas:
            return PlacementAction.KEEP
        if current == target and target_replicas > current_replicas:
            return PlacementAction.REPLICATE
        if _TIER_ORDER[target] < _TIER_ORDER[current]:
            return PlacementAction.PROMOTE
        if _TIER_ORDER[target] > _TIER_ORDER[current]:
            return PlacementAction.DEMOTE
        return PlacementAction.MOVE

    def _reason_for(self, *, data: DataObject, temperature: float, tier: StorageTier, action: PlacementAction) -> str:
        parts = [f"temperature={temperature:.4f}", f"tier={tier.value}", f"action={action.value}"]
        if data.reconstruction_seconds and data.reconstruction_seconds > 1800:
            parts.append("expensive-to-reconstruct")
        if data.exclusivity == "high_fanout":
            parts.append("high-fanout")
        if data.sensitivity in {"sensitive", "secret"}:
            parts.append(f"sensitivity={data.sensitivity}")
        return "; ".join(parts)


class DataObjectRegistry:
    """In-memory catalog of data objects for the MVP."""

    def __init__(self) -> None:
        self._objects: dict[str, DataObject] = {}

    def upsert(self, obj: DataObject) -> None:
        if not obj.id:
            raise ValueError("data object id is required")
        if obj.size_bytes < 0:
            raise ValueError("size_bytes must not be negative")
        self._objects[obj.id] = obj

    def get(self, object_id: str) -> DataObject:
        try:
            return self._objects[object_id]
        except KeyError as exc:
            raise KeyError(f"unknown data object: {object_id}") from exc

    def all(self) -> list[DataObject]:
        return list(self._objects.values())


class DataFabric:
    """Coordinates access observations, temperature and placement decisions."""

    def __init__(self, *, max_access_records: int = 10000, placement_engine: PlacementEngine | None = None) -> None:
        self.objects = DataObjectRegistry()
        self.devices: dict[str, StorageDevice] = {}
        self.access_log: deque[AccessRecord] = deque(maxlen=max_access_records)
        self.placement_engine = placement_engine or PlacementEngine()

    def register_device(self, device: StorageDevice) -> None:
        if not device.id:
            raise ValueError("storage device id is required")
        self.devices[device.id] = device

    def register_object(self, obj: DataObject) -> None:
        self.objects.upsert(obj)

    def record_access(
        self,
        object_id: str,
        *,
        kind: str = "read",
        node_id: str | None = None,
        size_bytes: int = 0,
        timestamp_ns: int | None = None,
    ) -> None:
        self.objects.get(object_id)
        self.access_log.append(
            AccessRecord(
                object_id=object_id,
                kind=kind,
                node_id=node_id,
                timestamp_ns=timestamp_ns or time.time_ns(),
                size_bytes=size_bytes,
            )
        )

    def profile(self, object_id: str, *, now_ns: int | None = None) -> DataProfile:
        self.objects.get(object_id)
        now_ns = now_ns or time.time_ns()
        one_hour_ns = 3600 * 1_000_000_000
        one_day_ns = 86400 * 1_000_000_000
        reads_1h = reads_24h = writes_1h = 0
        last_read_ns: int | None = None
        node_reads: dict[str, int] = {}
        for record in self.access_log:
            if record.object_id != object_id:
                continue
            age = now_ns - record.timestamp_ns
            if record.kind == "read" and age <= one_day_ns:
                reads_24h += 1
                if record.node_id:
                    node_reads[record.node_id] = node_reads.get(record.node_id, 0) + 1
                if last_read_ns is None or record.timestamp_ns > last_read_ns:
                    last_read_ns = record.timestamp_ns
            if record.kind == "read" and age <= one_hour_ns:
                reads_1h += 1
            if record.kind == "write" and age <= one_hour_ns:
                writes_1h += 1
        preferred_nodes = tuple(node for node, _ in sorted(node_reads.items(), key=lambda item: (-item[1], item[0]))[:3])
        last_read_age_seconds = None if last_read_ns is None else max(0.0, (now_ns - last_read_ns) / 1_000_000_000)
        return DataProfile(
            object_id=object_id,
            reads_1h=reads_1h,
            reads_24h=reads_24h,
            writes_1h=writes_1h,
            last_read_age_seconds=last_read_age_seconds,
            preferred_nodes=preferred_nodes,
        )

    def enriched_object(self, object_id: str) -> DataObject:
        obj = self.objects.get(object_id)
        profile = self.profile(object_id)
        write_frequency = obj.write_frequency
        if profile.writes_1h > 50:
            write_frequency = "high"
        elif profile.writes_1h > 5:
            write_frequency = "medium"
        preferred_nodes = list(profile.preferred_nodes or tuple(obj.preferred_nodes))
        return DataObject(
            id=obj.id,
            size_bytes=obj.size_bytes,
            reads_1h=max(obj.reads_1h, profile.reads_1h),
            reads_24h=max(obj.reads_24h, profile.reads_24h),
            latency_requirement=obj.latency_requirement,
            exclusivity=obj.exclusivity,
            sensitivity=obj.sensitivity,
            predicted_use=obj.predicted_use,
            reconstruction_seconds=obj.reconstruction_seconds,
            preferred_nodes=preferred_nodes,
            current_tier=obj.current_tier,
            current_devices=list(obj.current_devices),
            replicas=obj.replicas,
            write_frequency=write_frequency,
            last_read_age_seconds=profile.last_read_age_seconds if profile.last_read_age_seconds is not None else obj.last_read_age_seconds,
            content_hash=obj.content_hash,
            owner_resource_id=obj.owner_resource_id,
            metadata=dict(obj.metadata),
        )

    def decide(self, object_id: str) -> PlacementDecision:
        return self.placement_engine.decide(self.enriched_object(object_id), self.devices.values())

    def migration_plan(self) -> list[DataMove]:
        moves: list[DataMove] = []
        for obj in self.objects.all():
            enriched = self.enriched_object(obj.id)
            decision = self.placement_engine.decide(enriched, self.devices.values())
            if decision.action == PlacementAction.KEEP:
                continue
            moves.append(
                DataMove(
                    object_id=obj.id,
                    action=decision.action,
                    from_tier=obj.current_tier,
                    to_tier=decision.tier,
                    replicas=decision.replicas,
                    target_devices=decision.target_devices,
                    reason=decision.reason,
                )
            )
        return moves

    def tier_usage(self) -> dict[str, dict[str, int]]:
        result: dict[str, dict[str, int]] = {}
        for device in self.devices.values():
            tier = device.tier.value
            current = result.setdefault(tier, {"capacity_bytes": 0, "used_bytes": 0, "free_bytes": 0, "devices": 0})
            current["capacity_bytes"] += device.capacity_bytes
            current["used_bytes"] += device.used_bytes
            current["free_bytes"] += device.free_bytes
            current["devices"] += 1
        return result
