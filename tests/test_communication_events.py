import unittest

from cyberhive_core.communication_events import CommunicationEvent, CommunicationEventError


class CommunicationEventTests(unittest.TestCase):
    def test_redacts_secret_bearing_fields_before_hashing(self):
        event = CommunicationEvent.draft(
            event_id="evt-1",
            room_id="room-1",
            session_id="session-1",
            actor_id="human-1",
            actor_type="human",
            target="*",
            event_type="message.text",
            payload={"text": "hello", "token": "do-not-store"},
            metadata={"api_key": "also-secret"},
        ).with_integrity(sequence=1, previous_hash=None)
        rendered = str(event.to_dict())
        self.assertNotIn("do-not-store", rendered)
        self.assertNotIn("also-secret", rendered)
        self.assertTrue(event.verify_hash())

    def test_rejects_unknown_event_type(self):
        with self.assertRaises(CommunicationEventError):
            CommunicationEvent.draft(
                event_id="evt-1",
                room_id="room-1",
                session_id="session-1",
                actor_id="human-1",
                actor_type="human",
                target="*",
                event_type="totally.unknown",
            )


if __name__ == "__main__":
    unittest.main()
