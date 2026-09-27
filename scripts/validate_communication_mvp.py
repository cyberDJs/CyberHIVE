#!/usr/bin/env python3
from pathlib import Path
import tempfile

from cyberhive_core.communication_events import CommunicationEvent, EventAccessContext
from cyberhive_core.event_store import EventIdConflictError, RuntimeBusEventStore
from cyberhive_core.log_store import AppendOnlyLog
from cyberhive_core.room_presence import PresenceEntry, RoomPresenceRegistry
from cyberhive_core.runtime_bus import RuntimeBus
from cyberhive_core.state_engine import StateEngine


def build(path: Path):
    log = AppendOnlyLog(path)
    bus = RuntimeBus(node_id="node.validation", log_store=log, state_engine=StateEngine())
    return RuntimeBusEventStore(runtime_bus=bus, log_store=log)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "runtime.jsonl"
        ctx = EventAccessContext(
            "human.validation",
            "human",
            ("room.validation",),
            ("session.validation",),
        )
        store = build(path)
        one = CommunicationEvent.draft(
            event_id="evt-one",
            room_id="room.validation",
            session_id="session.validation",
            actor_id=ctx.actor_id,
            actor_type=ctx.actor_type,
            target="*",
            event_type="message.text",
            payload={"text": "hello"},
        )
        persisted = store.append(one, context=ctx)
        assert store.append(one, context=ctx).sequence == persisted.sequence
        try:
            store.append(
                CommunicationEvent.draft(
                    event_id="evt-one",
                    room_id="room.validation",
                    session_id="session.validation",
                    actor_id=ctx.actor_id,
                    actor_type=ctx.actor_type,
                    target="*",
                    event_type="message.text",
                    payload={"text": "conflict"},
                ),
                context=ctx,
            )
        except EventIdConflictError:
            pass
        else:
            raise SystemExit("duplicate conflict did not fail closed")

        restarted = build(path)
        assert restarted.verify_integrity()
        assert (
            restarted.read(
                "room.validation", "session.validation", context=ctx
            )[0].event_id
            == "evt-one"
        )

        presence = RoomPresenceRegistry(restarted)
        presence.join(
            room_id="room.validation",
            session_id="session.validation",
            entry=PresenceEntry(ctx.actor_id, "Validation User", ctx.actor_type),
            context=ctx,
            event_id="evt-presence",
        )
        assert len(
            presence.get_presence(
                room_id="room.validation", session_id="session.validation", context=ctx
            )
        ) == 1
    print("OK: Communication EventStore MVP validation passed")


if __name__ == "__main__":
    main()
