#!/usr/bin/env python3
from datetime import datetime, timezone

from cyberhive_core.node_heartbeat import NodeHeartbeat, NodeHeartbeatStore
from cyberhive_core.node_identity import EnrollmentAuthority, NodeIdentityRegistry


def main() -> None:
    registry = NodeIdentityRegistry()
    authority = EnrollmentAuthority(registry)
    token, secret = authority.create_bootstrap_token(ttl_seconds=300)
    request = authority.build_request(
        proposed_node_id="node.alpha",
        public_key="ssh-ed25519 demo-node-alpha",
        token_id=token.id,
        token_secret=secret,
        capabilities=("gpu.nvidia", "model.prewarm", "data.move"),
        labels={"zone": "lab"},
    )
    decision = authority.evaluate(request)
    assert decision.approved, decision.as_dict()
    session, session_token = registry.issue_session("node.alpha")

    store = NodeHeartbeatStore(identity_registry=registry, stale_after_seconds=30, expire_after_seconds=120)
    heartbeat = NodeHeartbeat.from_metrics(
        node_id="node.alpha",
        sequence=1,
        session_id=session.id,
        capabilities=("gpu.nvidia", "model.prewarm", "data.move"),
        labels={"zone": "lab"},
        metrics={
            "cpu_cores": 8,
            "free_cpu_cores": 5,
            "memory_gb": 32,
            "free_memory_gb": 20,
            "gpu_vram_gb": 8,
            "free_vram_gb": 5,
            "gpu_utilization": 0.42,
            "queue_depth": 2,
            "latency_ms": 18,
        },
        data_locality=("models/llama-small",),
        observed_at=datetime.now(timezone.utc),
    )
    hb_decision = store.ingest(heartbeat, session_token=session_token)
    assert hb_decision.accepted, hb_decision.as_dict()
    assert store.snapshot("node.alpha") is not None
    assert store.liveness("node.alpha").healthy
    assert store.to_scheduler_nodes()[0].id == "node.alpha"
    print("OK: Node Heartbeat & Capability Sync MVP validation passed")


if __name__ == "__main__":
    main()
