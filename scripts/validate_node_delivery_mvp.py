#!/usr/bin/env python3
"""Validate CyberHIVE Reliable Node Delivery Queue MVP."""

from __future__ import annotations

from datetime import timedelta

from cyberhive_core.node_delivery import DeliveryPolicy, DeliveryStatus, NodeDeliveryService
from cyberhive_core.node_identity import NodeIdentity, NodeIdentityRegistry, public_key_fingerprint
from cyberhive_core.secure_channel import ChannelDirection, ChannelPurpose, SecureChannel
from cyberhive_core.secure_node_gateway import SecureNodeGateway, SessionCredentialVault


def main() -> None:
    registry = NodeIdentityRegistry()
    registry.register(
        NodeIdentity(
            node_id="node.beta",
            public_key_fingerprint=public_key_fingerprint("ssh-ed25519 node.beta"),
            capabilities=("action", "model.prewarm"),
        )
    )
    session, token = registry.issue_session("node.beta", ttl_seconds=600)
    gateway = SecureNodeGateway(channel=SecureChannel(registry=registry), credential_vault=SessionCredentialVault())
    gateway.store_session(session_id=session.id, node_id="node.beta", token=token, expires_at=session.expires_at)
    service = NodeDeliveryService(gateway=gateway)

    item = service.enqueue_action(
        node_id="node.beta",
        session_id=session.id,
        action="prewarm_model",
        payload={"model_id": "llama-small"},
        policy=DeliveryPolicy(max_attempts=2, ack_timeout_seconds=5),
    )
    results = service.dispatch_ready()
    assert len(results) == 1, "expected one dispatch result"
    assert results[0].ok, "dispatch should succeed"
    assert item.status == DeliveryStatus.DISPATCHED, "item should be dispatched"
    assert item.last_envelope_id, "dispatch should record envelope id"

    ack = gateway.channel.build_envelope(
        node_id="node.beta",
        session_id=session.id,
        direction=ChannelDirection.NODE_TO_CONTROLLER,
        purpose=ChannelPurpose.ACK,
        sequence=1,
        payload={"ack_for": item.last_envelope_id},
        session_token=token,
    )
    completed = service.receive_ack_envelope(ack)
    assert completed is item, "ACK should resolve original delivery"
    assert item.status == DeliveryStatus.ACKED, "item should be acked"

    timeout_item = service.enqueue_action(
        node_id="node.beta",
        session_id=session.id,
        action="cache_prime",
        payload={"object_id": "dataset.hot"},
        policy=DeliveryPolicy(max_attempts=1, ack_timeout_seconds=1),
    )
    now = timeout_item.created_at
    service.dispatch_ready(now=now)
    service.sweep_timeouts(now=now + timedelta(seconds=2))
    assert timeout_item.status == DeliveryStatus.DEAD_LETTER, "unacked one-attempt item should dead-letter"

    print("OK: Reliable Node Delivery Queue MVP validation passed")


if __name__ == "__main__":
    main()
