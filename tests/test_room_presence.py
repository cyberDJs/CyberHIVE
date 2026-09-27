import tempfile
import unittest
from pathlib import Path

from cyberhive_core.communication_events import EventAccessContext
from cyberhive_core.event_store import RuntimeBusEventStore
from cyberhive_core.log_store import AppendOnlyLog
from cyberhive_core.room_presence import PresenceEntry, RoomPresenceRegistry
from cyberhive_core.runtime_bus import RuntimeBus
from cyberhive_core.state_engine import StateEngine


class RoomPresenceTests(unittest.TestCase):
    def test_join_leave_projection(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = AppendOnlyLog(Path(tmp) / "runtime.jsonl")
            bus = RuntimeBus(node_id="node.test", log_store=log, state_engine=StateEngine())
            store = RuntimeBusEventStore(runtime_bus=bus, log_store=log)
            registry = RoomPresenceRegistry(store)
            context = EventAccessContext(
                actor_id="agent-a",
                actor_type="agent",
                room_ids=("room-1",),
                session_ids=("session-1",),
            )
            registry.join(
                room_id="room-1",
                session_id="session-1",
                entry=PresenceEntry("agent-a", "Agent A", "agent", voice_identity="voice-a"),
                context=context,
                event_id="evt-join",
            )
            current = registry.get_presence(
                room_id="room-1", session_id="session-1", context=context
            )
            self.assertEqual([entry.actor_id for entry in current], ["agent-a"])
            registry.leave(
                room_id="room-1",
                session_id="session-1",
                context=context,
                event_id="evt-leave",
            )
            self.assertEqual(
                registry.get_presence(
                    room_id="room-1", session_id="session-1", context=context
                ),
                (),
            )


if __name__ == "__main__":
    unittest.main()
