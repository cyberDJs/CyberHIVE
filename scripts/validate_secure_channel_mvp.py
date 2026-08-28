#!/usr/bin/env python3
from __future__ import annotations

from cyberhive_core.node_identity import NodeIdentity, NodeIdentityRegistry, public_key_fingerprint
from cyberhive_core.secure_channel import (
    ChannelDecision,
    ChannelDirection,
    ChannelPurpose,
    SecureChannel,
)


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
    channel = SecureChannel(registry=registry)
    envelope = channel.build_envelope(
        node_id="node.beta",
        session_id=session.id,
        direction=ChannelDirection.NODE_TO_CONTROLLER,
        purpose=ChannelPurpose.HEARTBEAT,
        sequence=1,
        payload={"sequence": 1, "metrics": {"free_vram_gb": 5.0}},
        session_token=token,
    )
    decision = channel.verify(
        envelope,
        session_token=token,
        expected_direction=ChannelDirection.NODE_TO_CONTROLLER,
        expected_purpose=ChannelPurpose.HEARTBEAT,
    )
    if decision.status != ChannelDecision.ACCEPT:
        raise SystemExit(f"validation failed: {decision.reason}")
    replay = channel.verify(envelope, session_token=token)
    if replay.status != ChannelDecision.DUPLICATE:
        raise SystemExit("replay guard did not reject repeated message")
    print("OK: Secure Channel MVP validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
