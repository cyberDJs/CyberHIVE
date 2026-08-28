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
from cyberhive_core.secure_channel import ChannelDecision, ChannelDirection, ChannelPurpose, SecureChannel
from cyberhive_core.secure_node_gateway import GatewayMessageStatus, SecureNodeGateway, SessionCredentialVault


class SecureNodeGatewayMVPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = NodeIdentityRegistry()
        self.registry.register(
            NodeIdentity(
                node_id="node.beta",
                public_key_fingerprint=public_key_fingerprint("ssh-ed25519 node.beta"),
                capabilities=("heartbeat", "model.prewarm"),
            )
        )
        self.session, self.token = self.registry.issue_session("node.beta", ttl_seconds=300)
        self.store = NodeHeartbeatStore(identity_registry=self.registry)
        self.gateway = SecureNodeGateway(
            channel=SecureChannel(registry=self.registry),
            credential_vault=SessionCredentialVault(),
            heartbeat_store=self.store,
        )
        self.gateway.store_session(session_id=self.session.id, node_id="node.beta", token=self.token, expires_at=self.session.expires_at)

    def heartbeat(self, sequence: int = 1):
        return self.gateway.channel.build_envelope(
            node_id="node.beta",
            session_id=self.session.id,
            direction=ChannelDirection.NODE_TO_CONTROLLER,
            purpose=ChannelPurpose.HEARTBEAT,
            sequence=sequence,
            payload={"sequence": sequence, "metrics": {"free_vram_gb": 5.0}, "capabilities": ["heartbeat"]},
            session_token=self.token,
        )

    def test_gateway_ingests_heartbeat_without_call_site_token(self) -> None:
        receipt = self.gateway.receive(self.heartbeat(1))
        self.assertEqual(receipt.status, GatewayMessageStatus.DISPATCHED)
        self.assertEqual(receipt.verification.status, ChannelDecision.ACCEPT)
        self.assertEqual(receipt.result.status, HeartbeatStatus.ACCEPTED)
        self.assertEqual(self.store.snapshot("node.beta").free_vram_gb, 5.0)

    def test_missing_credential_denies_message(self) -> None:
        gateway = SecureNodeGateway(channel=SecureChannel(registry=self.registry), heartbeat_store=self.store)
        receipt = gateway.receive(self.heartbeat(1))
        self.assertEqual(receipt.status, GatewayMessageStatus.DENIED)
        self.assertIn("credential", receipt.reason)

    def test_replay_is_denied_by_gateway(self) -> None:
        first = self.heartbeat(2)
        self.assertEqual(self.gateway.receive(first).status, GatewayMessageStatus.DISPATCHED)
        replay = self.heartbeat(2)
        receipt = self.gateway.receive(replay)
        self.assertEqual(receipt.status, GatewayMessageStatus.DENIED)
        self.assertIn("sequence", receipt.reason)

    def test_gateway_builds_signed_action_envelope(self) -> None:
        envelope = self.gateway.build_action_envelope(
            node_id="node.beta",
            session_id=self.session.id,
            action="prewarm_model",
            payload={"model_id": "llama-small"},
        )
        self.assertEqual(envelope.direction, ChannelDirection.CONTROLLER_TO_NODE)
        self.assertEqual(envelope.purpose, ChannelPurpose.ACTION)
        self.assertTrue(envelope.signature)
        self.assertEqual(len(self.gateway.outbox), 1)

    def test_gateway_dispatches_controller_action_to_local_agent(self) -> None:
        agent_registry = NodeAgentRegistry()
        agent_registry.register(
            LocalNodeAgent(
                NodeDescriptor(
                    id="node.beta",
                    capabilities=("model.prewarm",),
                    allowed_actions=(AgentActionType.HEALTH_CHECK, AgentActionType.PREWARM_MODEL),
                ),
                policy=NodeAgentPolicy(allow_prewarm=True),
            )
        )
        gateway = SecureNodeGateway(
            channel=SecureChannel(registry=self.registry),
            credential_vault=SessionCredentialVault(),
            action_dispatcher=NodeActionDispatcher(agent_registry),
        )
        gateway.store_session(session_id=self.session.id, node_id="node.beta", token=self.token, expires_at=self.session.expires_at)
        envelope = gateway.build_action_envelope(
            node_id="node.beta",
            session_id=self.session.id,
            action="prewarm_model",
            payload={"model_id": "llama-small"},
            dry_run=True,
        )
        receipt = gateway.receive(envelope)
        self.assertEqual(receipt.status, GatewayMessageStatus.DISPATCHED)
        self.assertEqual(receipt.result.status, AgentActionStatus.DRY_RUN)

    def test_action_result_is_recorded(self) -> None:
        envelope = self.gateway.channel.build_envelope(
            node_id="node.beta",
            session_id=self.session.id,
            direction=ChannelDirection.NODE_TO_CONTROLLER,
            purpose=ChannelPurpose.ACTION_RESULT,
            sequence=1,
            payload={"request_id": "act_1", "status": "succeeded"},
            session_token=self.token,
        )
        receipt = self.gateway.receive(envelope)
        self.assertEqual(receipt.status, GatewayMessageStatus.RECORDED)
        self.assertEqual(len(self.gateway.action_results), 1)

    def test_expired_vault_credential_denies_before_verification(self) -> None:
        gateway = SecureNodeGateway(channel=SecureChannel(registry=self.registry), heartbeat_store=self.store)
        gateway.store_session(
            session_id=self.session.id,
            node_id="node.beta",
            token=self.token,
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        receipt = gateway.receive(self.heartbeat(1))
        self.assertEqual(receipt.status, GatewayMessageStatus.DENIED)
        self.assertIn("not active", receipt.reason)

    def test_ack_is_recorded(self) -> None:
        envelope = self.gateway.channel.build_envelope(
            node_id="node.beta",
            session_id=self.session.id,
            direction=ChannelDirection.NODE_TO_CONTROLLER,
            purpose=ChannelPurpose.ACK,
            sequence=1,
            payload={"ack_for": "msg_demo"},
            session_token=self.token,
        )
        receipt = self.gateway.receive(envelope)
        self.assertEqual(receipt.status, GatewayMessageStatus.RECORDED)
        self.assertEqual(len(self.gateway.acks), 1)


if __name__ == "__main__":
    unittest.main()
