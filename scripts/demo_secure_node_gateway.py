#!/usr/bin/env python3
from __future__ import annotations

from cyberhive_core.node_agent import AgentActionType, LocalNodeAgent, NodeActionDispatcher, NodeAgentPolicy, NodeAgentRegistry, NodeDescriptor
from cyberhive_core.node_heartbeat import NodeHeartbeatStore
from cyberhive_core.node_identity import NodeIdentity, NodeIdentityRegistry, public_key_fingerprint
from cyberhive_core.secure_channel import ChannelDirection, ChannelPurpose, SecureChannel
from cyberhive_core.secure_node_gateway import SecureNodeGateway


def main() -> int:
    identities = NodeIdentityRegistry()
    identities.register(
        NodeIdentity(
            node_id="node.beta",
            public_key_fingerprint=public_key_fingerprint("ssh-ed25519 node.beta"),
            capabilities=("heartbeat", "model.prewarm"),
        )
    )
    session, token = identities.issue_session("node.beta", ttl_seconds=300)

    heartbeat_store = NodeHeartbeatStore(identity_registry=identities)
    agents = NodeAgentRegistry()
    agents.register(
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
        channel=SecureChannel(registry=identities),
        heartbeat_store=heartbeat_store,
        action_dispatcher=NodeActionDispatcher(agents),
    )
    gateway.store_session(session_id=session.id, node_id="node.beta", token=token, expires_at=session.expires_at)

    hb = gateway.channel.build_envelope(
        node_id="node.beta",
        session_id=session.id,
        direction=ChannelDirection.NODE_TO_CONTROLLER,
        purpose=ChannelPurpose.HEARTBEAT,
        sequence=1,
        payload={
            "sequence": 1,
            "metrics": {"free_vram_gb": 5.0, "gpu_utilization": 0.32, "queue_depth": 1},
            "capabilities": ["heartbeat", "model.prewarm"],
        },
        session_token=token,
    )
    hb_receipt = gateway.receive(hb)

    action = gateway.build_action_envelope(
        node_id="node.beta",
        session_id=session.id,
        action="prewarm_model",
        payload={"model_id": "llama-small"},
        dry_run=True,
        correlation_id="demo-action",
    )
    action_receipt = gateway.receive(action)

    result = gateway.channel.build_envelope(
        node_id="node.beta",
        session_id=session.id,
        direction=ChannelDirection.NODE_TO_CONTROLLER,
        purpose=ChannelPurpose.ACTION_RESULT,
        sequence=1,
        payload={"request_id": "demo-action", "status": "dry_run", "message": "prewarm would run"},
        session_token=token,
        correlation_id="demo-action",
    )
    result_receipt = gateway.receive(result)

    print(f"heartbeat: {hb_receipt.status.value} reason={hb_receipt.reason}")
    print(f"action: {action_receipt.status.value} reason={action_receipt.reason}")
    print(f"result: {result_receipt.status.value} stored_results={len(gateway.action_results)}")
    print(f"outbox={len(gateway.outbox)} inbox={len(gateway.inbox)} receipts={len(gateway.receipts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
