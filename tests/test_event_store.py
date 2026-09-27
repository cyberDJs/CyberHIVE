import tempfile
import unittest
from pathlib import Path

from cyberhive_core.communication_events import CommunicationEvent, EventAccessContext
from cyberhive_core.event_store import (
    EventAuthorizationError,
    EventIdConflictError,
    RuntimeBusEventStore,
)
from cyberhive_core.log_store import AppendOnlyLog
from cyberhive_core.runtime_bus import RuntimeBus
from cyberhive_core.state_engine import StateEngine


def make_store(path: Path):
    log = AppendOnlyLog(path)
    bus = RuntimeBus(node_id="node.test", log_store=log, state_engine=StateEngine())
    return RuntimeBusEventStore(runtime_bus=bus, log_store=log), bus


def human_context():
    return EventAccessContext(
        actor_id="human-1",
        actor_type="human",
        room_ids=("room-1",),
        session_ids=("session-1",),
    )


def draft(event_id="evt-1", text="hello"):
    return CommunicationEvent.draft(
        event_id=event_id,
        room_id="room-1",
        session_id="session-1",
        actor_id="human-1",
        actor_type="human",
        target="*",
        event_type="message.text",
        payload={"text": text},
    )


class EventStoreTests(unittest.TestCase):
    def test_append_read_order_and_restart_resume(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "runtime.jsonl"
            store, bus = make_store(path)
            first = store.append(draft("evt-1", "one"), context=human_context())
            second = store.append(draft("evt-2", "two"), context=human_context())
            self.assertEqual((first.sequence, second.sequence), (1, 2))
            self.assertEqual(second.previous_hash, first.event_hash)
            self.assertEqual(bus.sequence, 2)

            restarted, restarted_bus = make_store(path)
            self.assertTrue(restarted.verify_integrity())
            self.assertEqual(restarted_bus.sequence, 2)
            resumed = restarted.read(
                "room-1", "session-1", context=human_context(), after_sequence=1
            )
            self.assertEqual([event.event_id for event in resumed], ["evt-2"])

            third = restarted.append(draft("evt-3", "three"), context=human_context())
            self.assertEqual(third.sequence, 3)
            self.assertEqual(restarted_bus.sequence, 3)

    def test_duplicate_same_content_is_idempotent_but_conflict_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _ = make_store(Path(tmp) / "runtime.jsonl")
            original = draft("evt-1", "same")
            first = store.append(original, context=human_context())
            duplicate = store.append(original, context=human_context())
            self.assertEqual(first.to_dict(), duplicate.to_dict())
            with self.assertRaises(EventIdConflictError):
                store.append(draft("evt-1", "different"), context=human_context())

    def test_rejects_actor_spoof_and_room_access(self):
        with tempfile.TemporaryDirectory() as tmp:
            store, _ = make_store(Path(tmp) / "runtime.jsonl")
            spoof = CommunicationEvent.draft(
                event_id="evt-spoof",
                room_id="room-1",
                session_id="session-1",
                actor_id="agent-x",
                actor_type="agent",
                target="*",
                event_type="message.text",
                payload={"text": "spoof"},
            )
            with self.assertRaises(EventAuthorizationError):
                store.append(spoof, context=human_context())
            with self.assertRaises(EventAuthorizationError):
                store.read("room-2", "session-1", context=human_context())


if __name__ == "__main__":
    unittest.main()
