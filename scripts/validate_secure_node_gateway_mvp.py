#!/usr/bin/env python3
from __future__ import annotations

from cyberhive_core.node_identity import NodeIdentity, NodeIdentityRegistry, public_key_fingerprint
from cyberhive_core.node_heartbeat import NodeHeartbeatStore
from cyberhive_core.secure_channel import ChannelDirection, ChannelPurpose, SecureChannel
from cyberhive_core.secure_node_gateway import GatewayMessageStatus, SecureNodeGateway, SessionCredentialVault


def main() -> int:
    registry = NodeIdentityRegistry()
    registry.register(
        NodeIdentity(
            node_id="node.beta",
            public_key_fingerprint=public_key_fingerprint("ssh-ed25519 node.beta"),
            capabilities=("heartbeat", "model.prewarm"),
        )
    )
    session, token = registry.issue_session("node.beta", ttl_seconds=300)
    store = NodeHeartbeatStore(identity_registry=registry)
    gateway = SecureNodeGateway(
        channel=SecureChannel(registry=registry),
        credential_vault=SessionCredentialVault(),
        heartbeat_store=store,
    )
    gateway.store_session(session_id=session.id, node_id="node.beta", token=token, expires_at=session.expires_at)

    heartbeat = gateway.channel.build_envelope(
        node_id="node.beta",
        session_id=session.id,
        direction=ChannelDirection.NODE_TO_CONTROLLER,
        purpose=ChannelPurpose.HEARTBEAT,
        sequence=1,
        payload={"sequence": 1, "metrics": {"free_vram_gb": 5.0}, "capabilities": ["heartbeat"]},
        session_token=token,
    )
    receipt = gateway.receive(heartbeat)
    assert receipt.status == GatewayMessageStatus.DISPATCHED, receipt.as_dict()
    assert store.snapshot("node.beta") is not None
    action = gateway.build_action_envelope(
        node_id="node.beta",
        session_id=session.id,
        action="prewarm_model",
        payload={"model_id": "llama-small"},
    )
    assert action.signature
    print("OK: Secure Node Gateway MVP validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
