from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from cyberhive_core.node_agent import (
    AgentActionStatus,
    AgentActionType,
    LocalNodeAgent,
    NodeActionDispatcher,
    NodeAgentPolicy,
    NodeAgentRegistry,
    NodeDescriptor,
)
from cyberhive_core.node_heartbeat import HeartbeatStatus, NodeHeartbeatStore
from cyberhive_core.node_identity import NodeIdentity, NodeIdentityRegistry, public_key_fingerprint
from cyberhive_core.secure_channel import (
    ChannelDecision,
    ChannelDirection,
    ChannelPurpose,
    SecureChannel,
    SecureChannelRouter,
    SignedChannelEnvelope,
)


class SecureChannelMVPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = NodeIdentityRegistry()
        self.registry.register(
            NodeIdentity(
                node_id="node.beta",
                public_key_fingerprint=public_key_fingerprint("ssh-ed25519 node.beta"),
                capabilities=("heartbeat", "model.prewarm", "cache.prime"),
            )
        )
        self.session, self.token = self.registry.issue_session("node.beta", ttl_seconds=300)
        self.channel = SecureChannel(registry=self.registry)

    def heartbeat(self, *, sequence: int = 1, token: str | None = None, issued_at: datetime | None = None):
        return self.channel.build_envelope(
            node_id="node.beta",
            session_id=self.session.id,
            direction=ChannelDirection.NODE_TO_CONTROLLER,
            purpose=ChannelPurpose.HEARTBEAT,
            sequence=sequence,
            payload={"sequence": sequence, "metrics": {"free_vram_gb": 5.0}, "capabilities": ["heartbeat"]},
            session_token=token or self.token,
            issued_at=issued_at,
        )

    def test_signed_heartbeat_is_accepted(self) -> None:
        envelope = self.heartbeat(sequence=1)
        decision = self.channel.verify(
            envelope,
            session_token=self.token,
            expected_direction=ChannelDirection.NODE_TO_CONTROLLER,
            expected_purpose=ChannelPurpose.HEARTBEAT,
        )
        self.assertEqual(decision.status, ChannelDecision.ACCEPT)
        self.assertTrue(decision.accepted)

    def test_wrong_token_is_denied_by_session_verification(self) -> None:
        envelope = self.heartbeat(sequence=1)
        decision = self.channel.verify(envelope, session_token="wrong-token")
        self.assertEqual(decision.status, ChannelDecision.DENY)
        self.assertIn("session", decision.reason)

    def test_tampered_payload_invalidates_signature(self) -> None:
        envelope = self.heartbeat(sequence=1)
        tampered = SignedChannelEnvelope(
            node_id=envelope.node_id,
            session_id=envelope.session_id,
            direction=envelope.direction,
            purpose=envelope.purpose,
            sequence=envelope.sequence,
            payload={"sequence": 1, "metrics": {"free_vram_gb": 99.0}},
            issued_at=envelope.issued_at,
            expires_at=envelope.expires_at,
            signature=envelope.signature,
            id=envelope.id,
        )
        decision = self.channel.verify(tampered, session_token=self.token)
        self.assertEqual(decision.status, ChannelDecision.DENY)
        self.assertEqual(decision.reason, "signature verification failed")

    def test_replay_sequence_is_rejected(self) -> None:
        first = self.heartbeat(sequence=10)
        self.assertEqual(self.channel.verify(first, session_token=self.token).status, ChannelDecision.ACCEPT)
        second = self.heartbeat(sequence=10)
        replay = self.channel.verify(second, session_token=self.token)
        self.assertEqual(replay.status, ChannelDecision.DUPLICATE)
        self.assertIn("sequence", replay.reason)

    def test_stale_message_is_rejected(self) -> None:
        old = datetime.now(timezone.utc) - timedelta(minutes=10)
        envelope = self.heartbeat(sequence=1, issued_at=old)
        decision = self.channel.verify(envelope, session_token=self.token)
        self.assertEqual(decision.status, ChannelDecision.STALE)

    def test_direction_mismatch_is_denied(self) -> None:
        envelope = self.heartbeat(sequence=1)
        decision = self.channel.verify(
            envelope,
            session_token=self.token,
            expected_direction=ChannelDirection.CONTROLLER_TO_NODE,
        )
        self.assertEqual(decision.status, ChannelDecision.DENY)
        self.assertIn("direction", decision.reason)

    def test_router_ingests_verified_heartbeat(self) -> None:
        store = NodeHeartbeatStore(identity_registry=self.registry)
        router = SecureChannelRouter(channel=self.channel, heartbeat_store=store)
        envelope = self.heartbeat(sequence=1)
        decision, result = router.ingest_heartbeat(envelope, session_token=self.token)
        self.assertEqual(decision.status, ChannelDecision.ACCEPT)
        self.assertEqual(result.status, HeartbeatStatus.ACCEPTED)
        snapshot = store.snapshot("node.beta")
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.free_vram_gb, 5.0)

    def test_router_dispatches_verified_action(self) -> None:
        agent_registry = NodeAgentRegistry()
        agent_registry.register(
            LocalNodeAgent(
                NodeDescriptor(
                    id="node.beta",
                    capabilities=("model.prewarm",),
                    allowed_actions=(AgentActionType.PREWARM_MODEL, AgentActionType.HEALTH_CHECK),
                ),
                policy=NodeAgentPolicy(allow_prewarm=True),
            )
        )
        dispatcher = NodeActionDispatcher(agent_registry)
        router = SecureChannelRouter(channel=self.channel, action_dispatcher=dispatcher)
        envelope = self.channel.build_envelope(
            node_id="node.beta",
            session_id=self.session.id,
            direction=ChannelDirection.CONTROLLER_TO_NODE,
            purpose=ChannelPurpose.ACTION,
            sequence=1,
            payload={"action": "prewarm_model", "payload": {"model": "llama-small"}, "dry_run": True},
            session_token=self.token,
        )
        decision, result = router.dispatch_action(envelope, session_token=self.token)
        self.assertEqual(decision.status, ChannelDecision.ACCEPT)
        self.assertEqual(result.status, AgentActionStatus.DRY_RUN)


if __name__ == "__main__":
    unittest.main()
