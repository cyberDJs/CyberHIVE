#!/usr/bin/env python3
from __future__ import annotations

from cyberhive_core.node_identity import NodeIdentity, NodeIdentityRegistry, public_key_fingerprint
from cyberhive_core.secure_channel import ChannelDirection, ChannelPurpose, SecureChannel


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

    heartbeat = channel.build_envelope(
        node_id="node.beta",
        session_id=session.id,
        direction=ChannelDirection.NODE_TO_CONTROLLER,
        purpose=ChannelPurpose.HEARTBEAT,
        sequence=7,
        payload={
            "sequence": 7,
            "metrics": {"free_vram_gb": 5.0, "gpu_utilization": 0.42, "queue_depth": 2},
            "capabilities": ["heartbeat", "model.prewarm"],
        },
        session_token=token,
    )
    accepted = channel.verify(heartbeat, session_token=token)
    replay = channel.verify(heartbeat, session_token=token)

    action = channel.build_envelope(
        node_id="node.beta",
        session_id=session.id,
        direction=ChannelDirection.CONTROLLER_TO_NODE,
        purpose=ChannelPurpose.ACTION,
        sequence=1,
        payload={"action": "prewarm_model", "payload": {"model": "llama-small"}, "dry_run": True},
        session_token=token,
        correlation_id="demo-prewarm",
    )
    action_decision = channel.verify(
        action,
        session_token=token,
        expected_direction=ChannelDirection.CONTROLLER_TO_NODE,
        expected_purpose=ChannelPurpose.ACTION,
    )

    print(f"heartbeat: {accepted.status.value} node={accepted.node_id} seq={heartbeat.sequence}")
    print(f"replay: {replay.status.value} reason={replay.reason}")
    print(f"action: {action_decision.status.value} purpose={action.purpose.value} digest={action.digest()[:18]}...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
