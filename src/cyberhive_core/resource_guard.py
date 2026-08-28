"""CyberHIVE Local Resource Guard MVP.

A node worker must not accept arbitrary work just because the controller sent a
valid signed action. This module adds a small local resource governor that can
reserve bounded CPU/RAM/VRAM/IO/concurrency budgets before a handler runs.

The MVP is an in-memory guard. It does not read host metrics, change cgroups,
start containers, or enforce kernel limits. Later runtime adapters can connect
these decisions to actual OS/container controls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
import math
import uuid


class ResourceGuardError(RuntimeError):
    """Raised when local resource guard inputs are invalid."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _finite(value: Any, *, name: str, minimum: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ResourceGuardError(f"{name} must be numeric") from exc
    if not math.isfinite(number):
        raise ResourceGuardError(f"{name} must be finite")
    if number < minimum:
        raise ResourceGuardError(f"{name} must be >= {minimum}")
    return number


class ReservationStatus(str, Enum):
    GRANTED = "granted"
    DENIED = "denied"
    RELEASED = "released"
    DRY_RUN = "dry_run"


@dataclass(frozen=True)
class ResourceBudget:
    """Static local resource budget for one node runtime."""

    cpu_units: float = 1.0
    memory_mb: float = 1024.0
    vram_mb: float = 0.0
    io_weight: float = 1.0
    max_concurrent: int = 1

    def __post_init__(self) -> None:
        _finite(self.cpu_units, name="cpu_units")
        _finite(self.memory_mb, name="memory_mb")
        _finite(self.vram_mb, name="vram_mb")
        _finite(self.io_weight, name="io_weight")
        if int(self.max_concurrent) < 1:
            raise ResourceGuardError("max_concurrent must be at least 1")

    def as_dict(self) -> dict[str, Any]:
        return {
            "cpu_units": self.cpu_units,
            "memory_mb": self.memory_mb,
            "vram_mb": self.vram_mb,
            "io_weight": self.io_weight,
            "max_concurrent": self.max_concurrent,
        }


@dataclass(frozen=True)
class ResourceRequest:
    """Resource request declared by a node action."""

    cpu_units: float = 0.1
    memory_mb: float = 64.0
    vram_mb: float = 0.0
    io_weight: float = 0.1
    concurrency_slots: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _finite(self.cpu_units, name="cpu_units")
        _finite(self.memory_mb, name="memory_mb")
        _finite(self.vram_mb, name="vram_mb")
        _finite(self.io_weight, name="io_weight")
        if int(self.concurrency_slots) < 1:
            raise ResourceGuardError("concurrency_slots must be at least 1")

    def as_dict(self) -> dict[str, Any]:
        return {
            "cpu_units": self.cpu_units,
            "memory_mb": self.memory_mb,
            "vram_mb": self.vram_mb,
            "io_weight": self.io_weight,
            "concurrency_slots": self.concurrency_slots,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ResourceReservation:
    """Decision and optional active reservation for a local node action."""

    node_id: str
    action: str
    request: ResourceRequest
    status: ReservationStatus
    reason: str
    dry_run: bool = True
    created_at: datetime = field(default_factory=_now)
    released_at: datetime | None = None
    id: str = field(default_factory=lambda: f"res_{uuid.uuid4().hex[:20]}")

    @property
    def granted(self) -> bool:
        return self.status in {ReservationStatus.GRANTED, ReservationStatus.DRY_RUN}

    @property
    def active(self) -> bool:
        return self.status == ReservationStatus.GRANTED and self.released_at is None

    def released(self, *, reason: str = "reservation released", now: datetime | None = None) -> "ResourceReservation":
        return ResourceReservation(
            node_id=self.node_id,
            action=self.action,
            request=self.request,
            status=ReservationStatus.RELEASED,
            reason=reason,
            dry_run=self.dry_run,
            created_at=self.created_at,
            released_at=now or _now(),
            id=self.id,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "action": self.action,
            "request": self.request.as_dict(),
            "status": self.status.value,
            "reason": self.reason,
            "dry_run": self.dry_run,
            "created_at": self.created_at.isoformat(),
            "released_at": self.released_at.isoformat() if self.released_at else None,
        }


class LocalResourceGuard:
    """In-memory local resource reservation guard."""

    def __init__(self, *, node_id: str, budget: ResourceBudget | None = None) -> None:
        if not node_id:
            raise ResourceGuardError("node_id is required")
        self.node_id = node_id
        self.budget = budget or ResourceBudget()
        self._active: dict[str, ResourceReservation] = {}
        self.journal: list[ResourceReservation] = []

    def reserve(
        self,
        *,
        action: str,
        request: ResourceRequest | None = None,
        dry_run: bool = True,
        now: datetime | None = None,
    ) -> ResourceReservation:
        if not action:
            raise ResourceGuardError("action is required")
        resource_request = request or default_request_for_action(action)
        denial = self._denial(action, resource_request)
        status = ReservationStatus.DRY_RUN if dry_run and denial is None else ReservationStatus.GRANTED
        if denial is not None:
            reservation = ResourceReservation(
                node_id=self.node_id,
                action=action,
                request=resource_request,
                status=ReservationStatus.DENIED,
                reason=denial,
                dry_run=dry_run,
                created_at=now or _now(),
            )
            self.journal.append(reservation)
            return reservation
        reservation = ResourceReservation(
            node_id=self.node_id,
            action=action,
            request=resource_request,
            status=status,
            reason="dry-run resource preflight passed" if dry_run else "resource reservation granted",
            dry_run=dry_run,
            created_at=now or _now(),
        )
        if not dry_run:
            self._active[reservation.id] = reservation
        self.journal.append(reservation)
        return reservation

    def release(self, reservation_id: str, *, reason: str = "reservation released", now: datetime | None = None) -> ResourceReservation:
        reservation = self._active.pop(reservation_id, None)
        if reservation is None:
            raise ResourceGuardError("active reservation not found")
        released = reservation.released(reason=reason, now=now)
        self.journal.append(released)
        return released

    def usage(self) -> ResourceRequest:
        return ResourceRequest(
            cpu_units=sum(item.request.cpu_units for item in self._active.values()),
            memory_mb=sum(item.request.memory_mb for item in self._active.values()),
            vram_mb=sum(item.request.vram_mb for item in self._active.values()),
            io_weight=sum(item.request.io_weight for item in self._active.values()),
            concurrency_slots=sum(item.request.concurrency_slots for item in self._active.values()) or 1,
        )

    def active_reservations(self) -> tuple[ResourceReservation, ...]:
        return tuple(self._active.values())

    def as_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "budget": self.budget.as_dict(),
            "active": [item.as_dict() for item in self.active_reservations()],
            "journal": [item.as_dict() for item in self.journal],
        }

    def _denial(self, action: str, request: ResourceRequest) -> str | None:
        current = self.usage()
        active_slots = sum(item.request.concurrency_slots for item in self._active.values())
        if active_slots + request.concurrency_slots > self.budget.max_concurrent:
            return "concurrency budget exceeded"
        if current.cpu_units + request.cpu_units > self.budget.cpu_units:
            return "cpu budget exceeded"
        if current.memory_mb + request.memory_mb > self.budget.memory_mb:
            return "memory budget exceeded"
        if current.vram_mb + request.vram_mb > self.budget.vram_mb:
            return "vram budget exceeded"
        if current.io_weight + request.io_weight > self.budget.io_weight:
            return "io budget exceeded"
        return None


def resource_request_from_payload(payload: Mapping[str, Any]) -> ResourceRequest:
    raw = payload.get("resource_request", {})
    if not isinstance(raw, Mapping):
        raw = {}
    return ResourceRequest(
        cpu_units=_finite(raw.get("cpu_units", payload.get("cpu_units", 0.1)), name="cpu_units"),
        memory_mb=_finite(raw.get("memory_mb", payload.get("memory_mb", 64.0)), name="memory_mb"),
        vram_mb=_finite(raw.get("vram_mb", payload.get("vram_mb", 0.0)), name="vram_mb"),
        io_weight=_finite(raw.get("io_weight", payload.get("io_weight", 0.1)), name="io_weight"),
        concurrency_slots=int(raw.get("concurrency_slots", payload.get("concurrency_slots", 1))),
        metadata=dict(raw.get("metadata", {})) if isinstance(raw.get("metadata", {}), Mapping) else {},
    )


def default_request_for_action(action: str) -> ResourceRequest:
    if action == "prewarm_model":
        return ResourceRequest(cpu_units=0.2, memory_mb=256.0, vram_mb=512.0, io_weight=0.2)
    if action == "data_move":
        return ResourceRequest(cpu_units=0.1, memory_mb=128.0, vram_mb=0.0, io_weight=0.6)
    if action == "cache_prime":
        return ResourceRequest(cpu_units=0.1, memory_mb=128.0, vram_mb=0.0, io_weight=0.4)
    return ResourceRequest()
