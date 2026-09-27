"""Room presence projection backed by canonical communication events."""
from __future__ import annotations

from dataclasses import dataclass
import uuid

from .communication_events import CommunicationEvent, EventAccessContext
from .event_store import EventStore


@dataclass(frozen=True, slots=True)
class PresenceEntry:
    actor_id: str
    display_name: str
    actor_type: str
    runtime_status: str = "online"
    voice_identity: str | None = None


class RoomPresenceRegistry:
    def __init__(self, store: EventStore) -> None:
        self.store = store

    def join(
        self,
        *,
        room_id: str,
        session_id: str,
        entry: PresenceEntry,
        context: EventAccessContext,
        event_id: str | None = None,
    ) -> CommunicationEvent:
        event = CommunicationEvent.draft(
            event_id=event_id or f"evt_{uuid.uuid4().hex}",
            room_id=room_id,
            session_id=session_id,
            actor_id=entry.actor_id,
            actor_type=entry.actor_type,
            target="*",
            event_type="presence.join",
            payload={
                "display_name": entry.display_name,
                "runtime_status": entry.runtime_status,
                "voice_identity": entry.voice_identity,
            },
        )
        return self.store.append(event, context=context)

    def leave(
        self,
        *,
        room_id: str,
        session_id: str,
        context: EventAccessContext,
        event_id: str | None = None,
    ) -> CommunicationEvent:
        event = CommunicationEvent.draft(
            event_id=event_id or f"evt_{uuid.uuid4().hex}",
            room_id=room_id,
            session_id=session_id,
            actor_id=context.actor_id,
            actor_type=context.actor_type,
            target="*",
            event_type="presence.leave",
        )
        return self.store.append(event, context=context)

    def get_presence(
        self,
        *,
        room_id: str,
        session_id: str,
        context: EventAccessContext,
    ) -> tuple[PresenceEntry, ...]:
        current: dict[str, PresenceEntry] = {}
        for event in self.store.read(
            room_id, session_id, context=context, limit=1000
        ):
            if event.event_type == "presence.join":
                current[event.actor_id] = PresenceEntry(
                    actor_id=event.actor_id,
                    display_name=str(
                        event.payload.get("display_name", event.actor_id)
                    ),
                    actor_type=event.actor_type,
                    runtime_status=str(
                        event.payload.get("runtime_status", "online")
                    ),
                    voice_identity=(
                        str(event.payload["voice_identity"])
                        if event.payload.get("voice_identity") is not None
                        else None
                    ),
                )
            elif event.event_type == "presence.leave":
                current.pop(event.actor_id, None)
            elif event.event_type == "agent.status" and event.actor_id in current:
                existing = current[event.actor_id]
                current[event.actor_id] = PresenceEntry(
                    actor_id=existing.actor_id,
                    display_name=existing.display_name,
                    actor_type=existing.actor_type,
                    runtime_status=str(
                        event.payload.get(
                            "runtime_status", existing.runtime_status
                        )
                    ),
                    voice_identity=existing.voice_identity,
                )
        return tuple(sorted(current.values(), key=lambda item: item.actor_id))
