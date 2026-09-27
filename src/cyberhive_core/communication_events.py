"""Canonical communication-event contract for CyberHIVE.

Communication events are immutable application records carried by the existing
RuntimeBus. They are intentionally independent from HiveFrame sequence numbers:
conversation sequence is restart-durable and owned by EventStore.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Any, Mapping

MAX_EVENT_BYTES = 64 * 1024
ALLOWED_ACTOR_TYPES = frozenset({"human", "agent", "system", "node"})
ALLOWED_EVENT_TYPES = frozenset(
    {
        "message.text",
        "message.voice.transcript",
        "voice.started",
        "voice.finished",
        "presence.join",
        "presence.leave",
        "agent.status",
        "heartbeat",
        "task.created",
        "task.claimed",
        "task.completed",
        "system.error",
    }
)
_SECRET_KEYS = frozenset(
    {
        "token",
        "access_token",
        "refresh_token",
        "password",
        "passwd",
        "secret",
        "credential",
        "credentials",
        "api_key",
        "access_key",
        "private_key",
    }
)
_SECRET_SUFFIXES = (
    "_token",
    "_password",
    "_secret",
    "_credential",
    "_credentials",
    "_api_key",
    "_access_key",
    "_private_key",
)


class CommunicationEventError(ValueError):
    """Raised when a communication event violates the canonical contract."""


def _secret_key(key: object) -> bool:
    normalized = str(key).strip().lower().replace("-", "_")
    return normalized in _SECRET_KEYS or normalized.endswith(_SECRET_SUFFIXES)


def sanitize_event_value(value: Any) -> Any:
    """Return a JSON-compatible value with secret-bearing fields redacted."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _secret_key(key) else sanitize_event_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_event_value(item) for item in value]
    return str(value)


def _canonical_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _required_text(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CommunicationEventError(f"{name} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class EventAccessContext:
    """Trusted identity/authorization context supplied by an adapter or session."""

    actor_id: str
    actor_type: str
    room_ids: tuple[str, ...]
    session_ids: tuple[str, ...] = ()
    can_impersonate: bool = False
    can_read_all: bool = False

    def __post_init__(self) -> None:
        _required_text("actor_id", self.actor_id)
        if self.actor_type not in ALLOWED_ACTOR_TYPES:
            raise CommunicationEventError("unsupported actor_type")
        if not self.room_ids and not self.can_read_all:
            raise CommunicationEventError("at least one authorized room is required")

    def allows(self, room_id: str, session_id: str) -> bool:
        if self.can_read_all:
            return True
        if room_id not in self.room_ids:
            return False
        return not self.session_ids or session_id in self.session_ids


@dataclass(frozen=True, slots=True)
class CommunicationEvent:
    event_id: str
    timestamp: str
    sequence: int
    room_id: str
    session_id: str
    actor_id: str
    actor_type: str
    target: str
    event_type: str
    payload: Mapping[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None
    causation_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    previous_hash: str | None = None
    event_hash: str = ""

    @classmethod
    def draft(
        cls,
        *,
        event_id: str,
        room_id: str,
        session_id: str,
        actor_id: str,
        actor_type: str,
        target: str,
        event_type: str,
        payload: Mapping[str, Any] | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        timestamp: str | None = None,
    ) -> "CommunicationEvent":
        event = cls(
            event_id=event_id,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            sequence=0,
            room_id=room_id,
            session_id=session_id,
            actor_id=actor_id,
            actor_type=actor_type,
            target=target,
            event_type=event_type,
            payload=sanitize_event_value(payload or {}),
            correlation_id=correlation_id,
            causation_id=causation_id,
            metadata=sanitize_event_value(metadata or {}),
        )
        event.validate()
        return event

    def normalized(self) -> "CommunicationEvent":
        event = replace(
            self,
            event_id=_required_text("event_id", self.event_id),
            timestamp=_required_text("timestamp", self.timestamp),
            room_id=_required_text("room_id", self.room_id),
            session_id=_required_text("session_id", self.session_id),
            actor_id=_required_text("actor_id", self.actor_id),
            target=_required_text("target", self.target),
            payload=sanitize_event_value(self.payload),
            metadata=sanitize_event_value(self.metadata),
        )
        event.validate()
        return event

    def validate(self) -> None:
        _required_text("event_id", self.event_id)
        _required_text("timestamp", self.timestamp)
        _required_text("room_id", self.room_id)
        _required_text("session_id", self.session_id)
        _required_text("actor_id", self.actor_id)
        _required_text("target", self.target)
        if self.sequence < 0:
            raise CommunicationEventError("sequence must be non-negative")
        if self.actor_type not in ALLOWED_ACTOR_TYPES:
            raise CommunicationEventError("unsupported actor_type")
        if self.event_type not in ALLOWED_EVENT_TYPES:
            raise CommunicationEventError("unsupported event_type")
        try:
            datetime.fromisoformat(self.timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise CommunicationEventError("timestamp must be ISO-8601") from exc
        if len(_canonical_bytes(self._hash_payload(include_hash=True))) > MAX_EVENT_BYTES:
            raise CommunicationEventError(f"event exceeds {MAX_EVENT_BYTES} bytes")

    def semantic_payload(self) -> dict[str, Any]:
        """Content compared for idempotency, excluding store-assigned integrity fields."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "room_id": self.room_id,
            "session_id": self.session_id,
            "actor_id": self.actor_id,
            "actor_type": self.actor_type,
            "target": self.target,
            "event_type": self.event_type,
            "payload": sanitize_event_value(self.payload),
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "metadata": sanitize_event_value(self.metadata),
        }

    def _hash_payload(self, *, include_hash: bool = False) -> dict[str, Any]:
        payload = {
            **self.semantic_payload(),
            "sequence": self.sequence,
            "previous_hash": self.previous_hash,
        }
        if include_hash:
            payload["event_hash"] = self.event_hash
        return payload

    def with_integrity(self, *, sequence: int, previous_hash: str | None) -> "CommunicationEvent":
        if sequence <= 0:
            raise CommunicationEventError("persisted sequence must be positive")
        candidate = replace(
            self.normalized(), sequence=sequence, previous_hash=previous_hash, event_hash=""
        )
        digest = sha256(_canonical_bytes(candidate._hash_payload())).hexdigest()
        return replace(candidate, event_hash=digest)

    def verify_hash(self) -> bool:
        if not self.event_hash or self.sequence <= 0:
            return False
        expected = sha256(_canonical_bytes(self._hash_payload())).hexdigest()
        return expected == self.event_hash

    def to_dict(self) -> dict[str, Any]:
        return {**self._hash_payload(), "event_hash": self.event_hash}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CommunicationEvent":
        event = cls(
            event_id=str(data["event_id"]),
            timestamp=str(data["timestamp"]),
            sequence=int(data["sequence"]),
            room_id=str(data["room_id"]),
            session_id=str(data["session_id"]),
            actor_id=str(data["actor_id"]),
            actor_type=str(data["actor_type"]),
            target=str(data["target"]),
            event_type=str(data["event_type"]),
            payload=sanitize_event_value(data.get("payload") or {}),
            correlation_id=(
                str(data["correlation_id"]) if data.get("correlation_id") is not None else None
            ),
            causation_id=(
                str(data["causation_id"]) if data.get("causation_id") is not None else None
            ),
            metadata=sanitize_event_value(data.get("metadata") or {}),
            previous_hash=(
                str(data["previous_hash"]) if data.get("previous_hash") is not None else None
            ),
            event_hash=str(data.get("event_hash", "")),
        )
        event.validate()
        return event
