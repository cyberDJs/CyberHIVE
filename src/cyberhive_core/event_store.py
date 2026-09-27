"""Communication EventStore adapter over the existing CyberHIVE RuntimeBus."""
from __future__ import annotations

from typing import Protocol

from .communication_events import CommunicationEvent, EventAccessContext
from .hiveframe import Operation, OperationType

_EVENT_RESOURCE_PREFIX = "communication.event."


class EventStoreError(RuntimeError):
    pass


class EventAuthorizationError(EventStoreError):
    pass


class EventIdConflictError(EventStoreError):
    pass


class EventStoreIntegrityError(EventStoreError):
    pass


class EventStore(Protocol):
    def append(
        self, event: CommunicationEvent, *, context: EventAccessContext
    ) -> CommunicationEvent: ...

    def read(
        self,
        room_id: str,
        session_id: str,
        *,
        context: EventAccessContext,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> tuple[CommunicationEvent, ...]: ...


class RuntimeBusEventStore:
    """Single-node communication ledger using RuntimeBus + AppendOnlyLog.

    RuntimeBus remains the only bus. Communication sequencing is derived from
    persisted communication events and therefore survives process restarts.
    """

    def __init__(self, *, runtime_bus, log_store) -> None:
        self.runtime_bus = runtime_bus
        self.log_store = log_store
        self._events: list[CommunicationEvent] = []
        self._by_id: dict[str, CommunicationEvent] = {}
        self._max_frame_sequence = 0
        self._load()
        if self.runtime_bus.sequence < self._max_frame_sequence:
            self.runtime_bus.sequence = self._max_frame_sequence

    def _load(self) -> None:
        for frame in self.log_store.iter_frames():
            self._max_frame_sequence = max(self._max_frame_sequence, frame.sequence)
            for operation in frame.operations:
                if not operation.resource_id.startswith(_EVENT_RESOURCE_PREFIX):
                    continue
                payload = operation.json_payload()
                if not isinstance(payload, dict):
                    raise EventStoreIntegrityError(
                        "communication event payload must be an object"
                    )
                event = CommunicationEvent.from_dict(payload)
                if event.event_id in self._by_id:
                    previous = self._by_id[event.event_id]
                    if previous.to_dict() != event.to_dict():
                        raise EventStoreIntegrityError(
                            "duplicate persisted event_id has conflicting content"
                        )
                    continue
                self._events.append(event)
                self._by_id[event.event_id] = event
        self._events.sort(key=lambda item: item.sequence)
        self.verify_integrity()

    @property
    def last_sequence(self) -> int:
        return self._events[-1].sequence if self._events else 0

    def _authorize(
        self, room_id: str, session_id: str, context: EventAccessContext
    ) -> None:
        if not context.allows(room_id, session_id):
            raise EventAuthorizationError("room/session access denied")

    def append(
        self, event: CommunicationEvent, *, context: EventAccessContext
    ) -> CommunicationEvent:
        normalized = event.normalized()
        self._authorize(normalized.room_id, normalized.session_id, context)
        if not context.can_impersonate:
            if (
                normalized.actor_id != context.actor_id
                or normalized.actor_type != context.actor_type
            ):
                raise EventAuthorizationError(
                    "actor identity does not match trusted context"
                )

        existing = self._by_id.get(normalized.event_id)
        if existing is not None:
            if existing.semantic_payload() == normalized.semantic_payload():
                return existing
            raise EventIdConflictError(
                "event_id already exists with different canonical content"
            )

        persisted = normalized.with_integrity(
            sequence=self.last_sequence + 1,
            previous_hash=self._events[-1].event_hash if self._events else None,
        )
        self.runtime_bus.publish(
            Operation.from_json_payload(
                OperationType.OBSERVE,
                f"{_EVENT_RESOURCE_PREFIX}{persisted.event_id}",
                persisted.to_dict(),
                priority=100,
            )
        )
        self.runtime_bus.flush()
        self._events.append(persisted)
        self._by_id[persisted.event_id] = persisted
        return persisted

    def read(
        self,
        room_id: str,
        session_id: str,
        *,
        context: EventAccessContext,
        after_sequence: int = 0,
        limit: int = 100,
    ) -> tuple[CommunicationEvent, ...]:
        self._authorize(room_id, session_id, context)
        if after_sequence < 0:
            raise ValueError("after_sequence must be non-negative")
        if limit <= 0 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        return tuple(
            event
            for event in self._events
            if event.room_id == room_id
            and event.session_id == session_id
            and event.sequence > after_sequence
        )[:limit]

    def verify_integrity(self) -> bool:
        previous_hash: str | None = None
        previous_sequence = 0
        for event in self._events:
            if event.sequence != previous_sequence + 1:
                raise EventStoreIntegrityError(
                    "communication sequence is not contiguous"
                )
            if event.previous_hash != previous_hash:
                raise EventStoreIntegrityError("communication hash chain is broken")
            if not event.verify_hash():
                raise EventStoreIntegrityError("communication event hash mismatch")
            previous_sequence = event.sequence
            previous_hash = event.event_hash
        return True
