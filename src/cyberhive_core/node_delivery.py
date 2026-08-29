"""CyberHIVE Reliable Node Delivery Queue MVP.

Patch 018 added a secure node gateway that can build signed action envelopes
and record incoming ACK / ERROR / result messages. This module adds the missing
reliability boundary between "we created an action" and "a node acknowledged
that it received it".

The MVP deliberately does not open sockets, start workers, persist secrets, or
perform remote execution. It only models delivery intent, retry/backoff,
acknowledgement correlation, expiry and dead-letter handling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Mapping, Sequence
import uuid

from .secure_channel import ChannelDirection, ChannelPurpose, SignedChannelEnvelope
from .secure_node_gateway import GatewayMessageStatus, GatewayReceipt, SecureNodeGateway, SecureNodeGatewayError


class NodeDeliveryError(RuntimeError):
    """Raised when a delivery queue operation is invalid."""


class DeliveryStatus(str, Enum):
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    ACKED = "acked"
    RETRY_WAIT = "retry_wait"
    EXPIRED = "expired"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"


class DeliveryPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


_PRIORITY_WEIGHT = {
    DeliveryPriority.CRITICAL: 100,
    DeliveryPriority.HIGH: 75,
    DeliveryPriority.NORMAL: 50,
    DeliveryPriority.LOW: 25,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_priority(value: DeliveryPriority | str) -> DeliveryPriority:
    if isinstance(value, DeliveryPriority):
        return value
    return DeliveryPriority(value)


@dataclass(frozen=True)
class DeliveryPolicy:
    """Retry and expiry policy for queued controller-to-node messages."""

    max_attempts: int = 3
    ack_timeout_seconds: int = 30
    initial_backoff_seconds: int = 2
    backoff_multiplier: float = 2.0
    max_backoff_seconds: int = 60
    ttl_seconds: int = 300

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise NodeDeliveryError("max_attempts must be at least 1")
        if self.ack_timeout_seconds < 1:
            raise NodeDeliveryError("ack_timeout_seconds must be positive")
        if self.initial_backoff_seconds < 0:
            raise NodeDeliveryError("initial_backoff_seconds cannot be negative")
        if self.backoff_multiplier < 1:
            raise NodeDeliveryError("backoff_multiplier must be at least 1")
        if self.max_backoff_seconds < self.initial_backoff_seconds:
            raise NodeDeliveryError("max_backoff_seconds must be >= initial_backoff_seconds")
        if self.ttl_seconds < 1:
            raise NodeDeliveryError("ttl_seconds must be positive")

    def ack_timeout(self) -> timedelta:
        return timedelta(seconds=self.ack_timeout_seconds)

    def ttl(self) -> timedelta:
        return timedelta(seconds=self.ttl_seconds)

    def backoff_for_attempt(self, attempts: int) -> timedelta:
        # attempts is the number of already dispatched attempts.
        exponent = max(0, attempts - 1)
        delay = self.initial_backoff_seconds * (self.backoff_multiplier ** exponent)
        return timedelta(seconds=min(int(delay), self.max_backoff_seconds))

    def as_dict(self) -> dict[str, Any]:
        return {
            "max_attempts": self.max_attempts,
            "ack_timeout_seconds": self.ack_timeout_seconds,
            "initial_backoff_seconds": self.initial_backoff_seconds,
            "backoff_multiplier": self.backoff_multiplier,
            "max_backoff_seconds": self.max_backoff_seconds,
            "ttl_seconds": self.ttl_seconds,
        }


@dataclass(frozen=True)
class DeliveryHistoryEvent:
    """Auditable delivery lifecycle event."""

    status: DeliveryStatus
    reason: str
    created_at: datetime = field(default_factory=_now)
    envelope_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "created_at": self.created_at.isoformat(),
            "envelope_id": self.envelope_id,
            "metadata": dict(self.metadata),
        }


@dataclass
class DeliveryItem:
    """Controller-to-node message tracked until ACK, expiry or dead-letter."""

    node_id: str
    session_id: str
    action: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    dry_run: bool = True
    approval_tokens: tuple[str, ...] = ()
    requested_by: str = "node-delivery-service"
    priority: DeliveryPriority = DeliveryPriority.NORMAL
    policy: DeliveryPolicy = field(default_factory=DeliveryPolicy)
    created_at: datetime = field(default_factory=_now)
    not_before: datetime | None = None
    expires_at: datetime | None = None
    id: str = field(default_factory=lambda: f"del_{uuid.uuid4().hex[:20]}")
    status: DeliveryStatus = DeliveryStatus.QUEUED
    attempts: int = 0
    last_attempt_at: datetime | None = None
    last_envelope_id: str | None = None
    acknowledged_at: datetime | None = None
    last_error: str | None = None
    history: list[DeliveryHistoryEvent] = field(default_factory=list)
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_id:
            raise NodeDeliveryError("node_id is required")
        if not self.session_id:
            raise NodeDeliveryError("session_id is required")
        if not self.action:
            raise NodeDeliveryError("action is required")
        self.priority = _coerce_priority(self.priority)
        if self.expires_at is None:
            self.expires_at = self.created_at + self.policy.ttl()
        if self.not_before is None:
            self.not_before = self.created_at
        self.record(DeliveryStatus.QUEUED, "delivery queued")

    @property
    def terminal(self) -> bool:
        return self.status in {
            DeliveryStatus.ACKED,
            DeliveryStatus.EXPIRED,
            DeliveryStatus.DEAD_LETTER,
            DeliveryStatus.CANCELLED,
        }

    def expired(self, now: datetime | None = None) -> bool:
        current = now or _now()
        return self.expires_at is not None and current >= self.expires_at

    def ready(self, now: datetime | None = None) -> bool:
        current = now or _now()
        return (
            not self.terminal
            and self.status in {DeliveryStatus.QUEUED, DeliveryStatus.RETRY_WAIT}
            and self.not_before is not None
            and self.not_before <= current
            and not self.expired(current)
        )

    def awaiting_ack(self, now: datetime | None = None) -> bool:
        current = now or _now()
        if self.status != DeliveryStatus.DISPATCHED or self.last_attempt_at is None:
            return False
        if self.expired(current):
            return False
        return current - self.last_attempt_at < self.policy.ack_timeout()

    def ack_timed_out(self, now: datetime | None = None) -> bool:
        current = now or _now()
        if self.status != DeliveryStatus.DISPATCHED or self.last_attempt_at is None:
            return False
        return current - self.last_attempt_at >= self.policy.ack_timeout()

    def record(
        self,
        status: DeliveryStatus,
        reason: str,
        *,
        envelope_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        now: datetime | None = None,
    ) -> None:
        self.history.append(
            DeliveryHistoryEvent(
                status=status,
                reason=reason,
                created_at=now or _now(),
                envelope_id=envelope_id,
                metadata=metadata or {},
            )
        )

    def mark_dispatched(self, envelope: SignedChannelEnvelope, *, now: datetime | None = None) -> None:
        current = now or _now()
        self.status = DeliveryStatus.DISPATCHED
        self.attempts += 1
        self.last_attempt_at = current
        self.last_envelope_id = envelope.id
        self.last_error = None
        self.record(DeliveryStatus.DISPATCHED, "envelope dispatched", envelope_id=envelope.id, now=current)

    def schedule_retry(self, reason: str, *, now: datetime | None = None) -> None:
        current = now or _now()
        if self.attempts >= self.policy.max_attempts:
            self.mark_dead_letter(reason, now=current)
            return
        self.status = DeliveryStatus.RETRY_WAIT
        self.last_error = reason
        self.not_before = current + self.policy.backoff_for_attempt(self.attempts)
        self.record(
            DeliveryStatus.RETRY_WAIT,
            reason,
            envelope_id=self.last_envelope_id,
            metadata={"not_before": self.not_before.isoformat(), "attempts": self.attempts},
            now=current,
        )

    def mark_acked(self, reason: str = "ack received", *, now: datetime | None = None) -> None:
        current = now or _now()
        self.status = DeliveryStatus.ACKED
        self.acknowledged_at = current
        self.record(DeliveryStatus.ACKED, reason, envelope_id=self.last_envelope_id, now=current)

    def mark_expired(self, reason: str = "delivery expired", *, now: datetime | None = None) -> None:
        current = now or _now()
        self.status = DeliveryStatus.EXPIRED
        self.last_error = reason
        self.record(DeliveryStatus.EXPIRED, reason, envelope_id=self.last_envelope_id, now=current)

    def mark_dead_letter(self, reason: str, *, now: datetime | None = None) -> None:
        current = now or _now()
        self.status = DeliveryStatus.DEAD_LETTER
        self.last_error = reason
        self.record(DeliveryStatus.DEAD_LETTER, reason, envelope_id=self.last_envelope_id, now=current)

    def cancel(self, reason: str = "delivery cancelled", *, now: datetime | None = None) -> None:
        current = now or _now()
        if self.terminal:
            raise NodeDeliveryError("terminal delivery cannot be cancelled")
        self.status = DeliveryStatus.CANCELLED
        self.last_error = reason
        self.record(DeliveryStatus.CANCELLED, reason, envelope_id=self.last_envelope_id, now=current)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "session_id": self.session_id,
            "action": self.action,
            "payload": dict(self.payload),
            "dry_run": self.dry_run,
            "approval_tokens": list(self.approval_tokens),
            "requested_by": self.requested_by,
            "priority": self.priority.value,
            "policy": self.policy.as_dict(),
            "created_at": self.created_at.isoformat(),
            "not_before": self.not_before.isoformat() if self.not_before else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.value,
            "attempts": self.attempts,
            "last_attempt_at": self.last_attempt_at.isoformat() if self.last_attempt_at else None,
            "last_envelope_id": self.last_envelope_id,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "last_error": self.last_error,
            "metadata": dict(self.metadata),
            "history": [event.as_dict() for event in self.history],
        }


class ReliableDeliveryQueue:
    """In-memory reliable delivery queue with retry and dead-letter semantics."""

    def __init__(self, policy: DeliveryPolicy | None = None) -> None:
        self.default_policy = policy or DeliveryPolicy()
        self._items: dict[str, DeliveryItem] = {}
        self._by_envelope: dict[str, str] = {}

    def enqueue_action(
        self,
        *,
        node_id: str,
        session_id: str,
        action: str,
        payload: Mapping[str, Any] | None = None,
        dry_run: bool = True,
        approval_tokens: Sequence[str] = (),
        priority: DeliveryPriority | str = DeliveryPriority.NORMAL,
        requested_by: str = "node-delivery-service",
        policy: DeliveryPolicy | None = None,
        not_before: datetime | None = None,
        expires_at: datetime | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> DeliveryItem:
        item = DeliveryItem(
            node_id=node_id,
            session_id=session_id,
            action=action,
            payload=dict(payload or {}),
            dry_run=dry_run,
            approval_tokens=tuple(approval_tokens),
            requested_by=requested_by,
            priority=_coerce_priority(priority),
            policy=policy or self.default_policy,
            not_before=not_before,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        self._items[item.id] = item
        return item

    def get(self, delivery_id: str) -> DeliveryItem | None:
        return self._items.get(delivery_id)

    def require(self, delivery_id: str) -> DeliveryItem:
        item = self.get(delivery_id)
        if item is None:
            raise NodeDeliveryError("delivery item not found")
        return item

    def all(self) -> tuple[DeliveryItem, ...]:
        return tuple(self._items.values())

    def ready(self, now: datetime | None = None, limit: int | None = None) -> tuple[DeliveryItem, ...]:
        current = now or _now()
        ready_items = [item for item in self._items.values() if item.ready(current)]
        ready_items.sort(key=lambda item: (-_PRIORITY_WEIGHT[item.priority], item.created_at, item.id))
        if limit is not None:
            ready_items = ready_items[:limit]
        return tuple(ready_items)

    def pending(self) -> tuple[DeliveryItem, ...]:
        return tuple(item for item in self._items.values() if not item.terminal)

    def dead_letters(self) -> tuple[DeliveryItem, ...]:
        return tuple(item for item in self._items.values() if item.status == DeliveryStatus.DEAD_LETTER)

    def register_dispatch(self, item: DeliveryItem, envelope: SignedChannelEnvelope, *, now: datetime | None = None) -> None:
        if item.id not in self._items:
            raise NodeDeliveryError("delivery item is not owned by this queue")
        item.mark_dispatched(envelope, now=now)
        self._by_envelope[envelope.id] = item.id

    def match_ack(self, ack_payload: Mapping[str, Any]) -> DeliveryItem | None:
        candidates = (
            ack_payload.get("delivery_id"),
            ack_payload.get("correlation_id"),
            ack_payload.get("ack_for"),
            ack_payload.get("envelope_id"),
        )
        for candidate in candidates:
            if not isinstance(candidate, str) or not candidate:
                continue
            if candidate in self._items:
                return self._items[candidate]
            delivery_id = self._by_envelope.get(candidate)
            if delivery_id is not None:
                return self._items.get(delivery_id)
        return None

    def mark_acked(
        self,
        ack_payload: Mapping[str, Any],
        *,
        node_id: str | None = None,
        session_id: str | None = None,
        now: datetime | None = None,
    ) -> DeliveryItem:
        item = self.match_ack(ack_payload)
        if item is None:
            raise NodeDeliveryError("ACK does not match a known delivery")
        if node_id is not None and item.node_id != node_id:
            raise NodeDeliveryError("ACK authenticated node does not match delivery node")
        if session_id is None:
            raise NodeDeliveryError("ACK authenticated session is required")
        if item.session_id != session_id:
            raise NodeDeliveryError("ACK authenticated session does not match delivery session")
        if item.terminal:
            return item
        item.mark_acked("ack received", now=now)
        return item

    def sweep_timeouts(self, now: datetime | None = None) -> tuple[DeliveryItem, ...]:
        current = now or _now()
        changed: list[DeliveryItem] = []
        for item in self._items.values():
            if item.terminal:
                continue
            if item.expired(current):
                item.mark_expired("delivery ttl expired", now=current)
                changed.append(item)
                continue
            if item.ack_timed_out(current):
                item.schedule_retry("ack timeout", now=current)
                changed.append(item)
        return tuple(changed)

    def cancel(self, delivery_id: str, reason: str = "delivery cancelled", *, now: datetime | None = None) -> DeliveryItem:
        item = self.require(delivery_id)
        item.cancel(reason, now=now)
        return item

    def as_dict(self) -> dict[str, Any]:
        return {
            "default_policy": self.default_policy.as_dict(),
            "items": [item.as_dict() for item in self.all()],
            "dead_letters": [item.id for item in self.dead_letters()],
        }


@dataclass(frozen=True)
class DeliveryDispatchResult:
    """Outcome of attempting to dispatch a queued delivery item."""

    delivery_id: str
    status: DeliveryStatus
    reason: str
    envelope_id: str | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == DeliveryStatus.DISPATCHED

    def as_dict(self) -> dict[str, Any]:
        return {
            "delivery_id": self.delivery_id,
            "status": self.status.value,
            "reason": self.reason,
            "envelope_id": self.envelope_id,
            "error": self.error,
        }


class NodeDeliveryService:
    """Coordinates reliable delivery queue with SecureNodeGateway."""

    def __init__(self, *, gateway: SecureNodeGateway, queue: ReliableDeliveryQueue | None = None) -> None:
        self.gateway = gateway
        self.queue = queue or ReliableDeliveryQueue()
        self.dispatch_results: list[DeliveryDispatchResult] = []

    def enqueue_action(self, **kwargs: Any) -> DeliveryItem:
        return self.queue.enqueue_action(**kwargs)

    def dispatch_ready(self, *, now: datetime | None = None, limit: int | None = None) -> tuple[DeliveryDispatchResult, ...]:
        current = now or _now()
        self.queue.sweep_timeouts(current)
        results: list[DeliveryDispatchResult] = []
        for item in self.queue.ready(current, limit=limit):
            try:
                envelope = self.gateway.build_action_envelope(
                    node_id=item.node_id,
                    session_id=item.session_id,
                    action=item.action,
                    payload=item.payload,
                    dry_run=item.dry_run,
                    approval_tokens=item.approval_tokens,
                    requested_by=item.requested_by,
                    correlation_id=item.id,
                )
            except SecureNodeGatewayError as exc:
                item.schedule_retry(str(exc), now=current)
                result = DeliveryDispatchResult(
                    delivery_id=item.id,
                    status=item.status,
                    reason="dispatch failed",
                    error=str(exc),
                )
            else:
                self.queue.register_dispatch(item, envelope, now=current)
                result = DeliveryDispatchResult(
                    delivery_id=item.id,
                    status=DeliveryStatus.DISPATCHED,
                    reason="envelope queued for transport",
                    envelope_id=envelope.id,
                )
            self.dispatch_results.append(result)
            results.append(result)
        return tuple(results)

    def record_gateway_receipt(self, receipt: GatewayReceipt, *, now: datetime | None = None) -> DeliveryItem | None:
        if receipt.status != GatewayMessageStatus.RECORDED or receipt.purpose != ChannelPurpose.ACK:
            return None
        if receipt.direction != ChannelDirection.NODE_TO_CONTROLLER:
            return None
        payload = receipt.result if isinstance(receipt.result, Mapping) else {}
        return self.queue.mark_acked(payload, node_id=receipt.node_id, session_id=receipt.session_id, now=now)

    def receive_ack_envelope(self, envelope: SignedChannelEnvelope, *, now: datetime | None = None) -> DeliveryItem | None:
        if envelope.direction != ChannelDirection.NODE_TO_CONTROLLER or envelope.purpose != ChannelPurpose.ACK:
            raise NodeDeliveryError("only node-to-controller ACK envelopes can complete deliveries")
        receipt = self.gateway.receive(envelope, now=now)
        return self.record_gateway_receipt(receipt, now=now)

    def sweep_timeouts(self, *, now: datetime | None = None) -> tuple[DeliveryItem, ...]:
        return self.queue.sweep_timeouts(now=now)

    def as_dict(self) -> dict[str, Any]:
        return {
            "queue": self.queue.as_dict(),
            "dispatch_results": [result.as_dict() for result in self.dispatch_results],
        }
