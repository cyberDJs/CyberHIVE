#!/usr/bin/env python3
"""Demo CyberHIVE Reliable Node Delivery Queue MVP."""

from __future__ import annotations

from datetime import timedelta

from cyberhive_core.node_delivery import DeliveryPolicy, NodeDeliveryService
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

    delivery = service.enqueue_action(
        node_id="node.beta",
        session_id=session.id,
        action="prewarm_model",
        payload={"model_id": "llama-small"},
        policy=DeliveryPolicy(max_attempts=3, ack_timeout_seconds=5, initial_backoff_seconds=0),
    )
    dispatch = service.dispatch_ready()[0]
    print(f"dispatch: {dispatch.status.value} delivery={delivery.id} envelope={dispatch.envelope_id}")

    ack = gateway.channel.build_envelope(
        node_id="node.beta",
        session_id=session.id,
        direction=ChannelDirection.NODE_TO_CONTROLLER,
        purpose=ChannelPurpose.ACK,
        sequence=1,
        payload={"ack_for": dispatch.envelope_id},
        session_token=token,
    )
    service.receive_ack_envelope(ack)
    print(f"ack: {delivery.status.value} attempts={delivery.attempts}")

    retry = service.enqueue_action(
        node_id="node.beta",
        session_id=session.id,
        action="cache_prime",
        payload={"object_id": "dataset.hot"},
        policy=DeliveryPolicy(max_attempts=2, ack_timeout_seconds=2, initial_backoff_seconds=0),
    )
    now = retry.created_at
    service.dispatch_ready(now=now)
    service.sweep_timeouts(now=now + timedelta(seconds=3))
    print(f"retry: {retry.status.value} attempts={retry.attempts} next={retry.not_before.isoformat()}")
    service.dispatch_ready(now=now + timedelta(seconds=3))
    service.sweep_timeouts(now=now + timedelta(seconds=6))
    print(f"final: {retry.status.value} attempts={retry.attempts} dead_letters={len(service.queue.dead_letters())}")


if __name__ == "__main__":
    main()
