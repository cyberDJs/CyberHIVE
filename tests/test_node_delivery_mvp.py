from __future__ import annotations

from datetime import datetime, timedelta, timezone
import unittest

from cyberhive_core.node_delivery import (
    DeliveryPolicy,
    DeliveryPriority,
    DeliveryStatus,
    NodeDeliveryError,
    NodeDeliveryService,
    ReliableDeliveryQueue,
)
from cyberhive_core.node_identity import NodeIdentity, NodeIdentityRegistry, public_key_fingerprint
from cyberhive_core.secure_channel import ChannelDirection, ChannelPurpose, SecureChannel
from cyberhive_core.secure_node_gateway import GatewayMessageStatus, GatewayReceipt, SecureNodeGateway, SessionCredentialVault


class NodeDeliveryMVPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = NodeIdentityRegistry()
        self.registry.register(
            NodeIdentity(
                node_id="node.beta",
                public_key_fingerprint=public_key_fingerprint("ssh-ed25519 node.beta"),
                capabilities=("action", "model.prewarm"),
            )
        )
        self.session, self.token = self.registry.issue_session("node.beta", ttl_seconds=600)
        self.gateway = SecureNodeGateway(
            channel=SecureChannel(registry=self.registry),
            credential_vault=SessionCredentialVault(),
        )
        self.gateway.store_session(
            session_id=self.session.id,
            node_id="node.beta",
            token=self.token,
            expires_at=self.session.expires_at,
        )
        self.service = NodeDeliveryService(gateway=self.gateway)

    def enqueue(self, **kwargs):
        defaults = {
            "node_id": "node.beta",
            "session_id": self.session.id,
            "action": "prewarm_model",
            "payload": {"model_id": "llama-small"},
        }
        defaults.update(kwargs)
        return self.service.enqueue_action(**defaults)

    def ack(self, payload: dict[str, str], sequence: int = 1):
        return self.gateway.channel.build_envelope(
            node_id="node.beta",
            session_id=self.session.id,
            direction=ChannelDirection.NODE_TO_CONTROLLER,
            purpose=ChannelPurpose.ACK,
            sequence=sequence,
            payload=payload,
            session_token=self.token,
        )

    def test_queue_orders_ready_items_by_priority(self) -> None:
        queue = ReliableDeliveryQueue()
        low = queue.enqueue_action(node_id="node.beta", session_id=self.session.id, action="noop", priority=DeliveryPriority.LOW)
        critical = queue.enqueue_action(node_id="node.beta", session_id=self.session.id, action="noop", priority=DeliveryPriority.CRITICAL)
        high = queue.enqueue_action(node_id="node.beta", session_id=self.session.id, action="noop", priority=DeliveryPriority.HIGH)
        ready = queue.ready()
        self.assertEqual([item.id for item in ready], [critical.id, high.id, low.id])

    def test_dispatch_ready_builds_signed_action_envelope(self) -> None:
        item = self.enqueue()
        results = self.service.dispatch_ready()
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].ok)
        self.assertEqual(item.status, DeliveryStatus.DISPATCHED)
        self.assertEqual(item.attempts, 1)
        self.assertEqual(len(self.gateway.outbox), 1)
        self.assertEqual(self.gateway.outbox[0].correlation_id, item.id)
        self.assertTrue(self.gateway.outbox[0].signature)

    def test_ack_by_envelope_id_marks_delivery_acked(self) -> None:
        item = self.enqueue()
        self.service.dispatch_ready()
        envelope_id = item.last_envelope_id
        self.assertIsNotNone(envelope_id)
        completed = self.service.receive_ack_envelope(self.ack({"ack_for": envelope_id}, sequence=1))
        self.assertIsNotNone(completed)
        self.assertEqual(completed.id, item.id)
        self.assertEqual(item.status, DeliveryStatus.ACKED)
        self.assertIsNotNone(item.acknowledged_at)

    def test_ack_by_delivery_id_marks_delivery_acked(self) -> None:
        item = self.enqueue()
        self.service.dispatch_ready()
        completed = self.service.receive_ack_envelope(self.ack({"delivery_id": item.id}, sequence=1))
        self.assertEqual(completed.id, item.id)
        self.assertEqual(item.status, DeliveryStatus.ACKED)


    def test_ack_from_different_authenticated_node_is_rejected(self) -> None:
        self.registry.register(
            NodeIdentity(
                node_id="node.alpha",
                public_key_fingerprint=public_key_fingerprint("ssh-ed25519 node.alpha"),
                capabilities=("action",),
            )
        )
        alpha_session, alpha_token = self.registry.issue_session("node.alpha", ttl_seconds=600)
        self.gateway.store_session(
            session_id=alpha_session.id,
            node_id="node.alpha",
            token=alpha_token,
            expires_at=alpha_session.expires_at,
        )
        item = self.enqueue()
        self.service.dispatch_ready()
        forged_ack = self.gateway.channel.build_envelope(
            node_id="node.alpha",
            session_id=alpha_session.id,
            direction=ChannelDirection.NODE_TO_CONTROLLER,
            purpose=ChannelPurpose.ACK,
            sequence=1,
            payload={"delivery_id": item.id},
            session_token=alpha_token,
        )

        with self.assertRaises(NodeDeliveryError):
            self.service.receive_ack_envelope(forged_ack)
        self.assertEqual(item.status, DeliveryStatus.DISPATCHED)


    def test_outbound_ack_receipt_does_not_complete_delivery(self) -> None:
        item = self.enqueue()
        self.service.dispatch_ready()
        receipt = GatewayReceipt(
            status=GatewayMessageStatus.RECORDED,
            envelope_id="msg_outbound_ack",
            node_id="node.beta",
            purpose=ChannelPurpose.ACK,
            direction=ChannelDirection.CONTROLLER_TO_NODE,
            reason="controller-produced ACK should not complete delivery",
            result={"delivery_id": item.id},
        )

        completed = self.service.record_gateway_receipt(receipt)

        self.assertIsNone(completed)
        self.assertEqual(item.status, DeliveryStatus.DISPATCHED)

    def test_ack_timeout_schedules_retry_and_dispatches_again(self) -> None:
        policy = DeliveryPolicy(max_attempts=3, ack_timeout_seconds=5, initial_backoff_seconds=0)
        item = self.enqueue(policy=policy)
        now = item.created_at
        self.service.dispatch_ready(now=now)
        self.service.sweep_timeouts(now=now + timedelta(seconds=6))
        self.assertEqual(item.status, DeliveryStatus.RETRY_WAIT)
        results = self.service.dispatch_ready(now=now + timedelta(seconds=6))
        self.assertEqual(len(results), 1)
        self.assertEqual(item.status, DeliveryStatus.DISPATCHED)
        self.assertEqual(item.attempts, 2)
        self.assertNotEqual(item.history[1].envelope_id, item.last_envelope_id)

    def test_max_attempts_moves_to_dead_letter(self) -> None:
        policy = DeliveryPolicy(max_attempts=1, ack_timeout_seconds=5, initial_backoff_seconds=0)
        item = self.enqueue(policy=policy)
        now = item.created_at
        self.service.dispatch_ready(now=now)
        changed = self.service.sweep_timeouts(now=now + timedelta(seconds=6))
        self.assertEqual(changed[0].status, DeliveryStatus.DEAD_LETTER)
        self.assertEqual(item.status, DeliveryStatus.DEAD_LETTER)
        self.assertEqual(len(self.service.queue.dead_letters()), 1)

    def test_ttl_expiry_marks_item_expired(self) -> None:
        item = self.enqueue(policy=DeliveryPolicy(ttl_seconds=10))
        now = item.created_at
        changed = self.service.sweep_timeouts(now=now + timedelta(seconds=20))
        self.assertIn(item, changed)
        self.assertEqual(item.status, DeliveryStatus.EXPIRED)

    def test_dispatch_failure_without_gateway_credential_schedules_retry(self) -> None:
        gateway = SecureNodeGateway(channel=SecureChannel(registry=self.registry), credential_vault=SessionCredentialVault())
        service = NodeDeliveryService(gateway=gateway)
        item = service.enqueue_action(node_id="node.beta", session_id=self.session.id, action="noop")
        results = service.dispatch_ready()
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].ok)
        self.assertEqual(item.status, DeliveryStatus.RETRY_WAIT)
        self.assertIn("credential", item.last_error)

    def test_unknown_ack_raises_clear_error(self) -> None:
        with self.assertRaises(NodeDeliveryError):
            self.service.receive_ack_envelope(self.ack({"ack_for": "missing-envelope"}, sequence=1))


if __name__ == "__main__":
    unittest.main()
