#!/usr/bin/env python3
from datetime import datetime, timedelta, timezone

from cyberhive_core.node_heartbeat import NodeHeartbeat, NodeHeartbeatStore
from cyberhive_core.node_identity import EnrollmentAuthority, NodeIdentityRegistry
from cyberhive_core.scheduler_router import ComputeRouter, WorkloadKind, WorkloadRequest


def enroll_demo_node(node_id: str, capabilities: tuple[str, ...]):
    registry = NodeIdentityRegistry()
    authority = EnrollmentAuthority(registry)
    token, secret = authority.create_bootstrap_token(ttl_seconds=300)
    request = authority.build_request(
        proposed_node_id=node_id,
        public_key=f"ssh-ed25519 demo-{node_id}",
        token_id=token.id,
        token_secret=secret,
        capabilities=capabilities,
        labels={"zone": "lab"},
    )
    decision = authority.evaluate(request)
    if not decision.approved:
        raise SystemExit(decision.reason)
    session, session_token = registry.issue_session(node_id)
    return registry, session, session_token


def main() -> None:
    registry, session, session_token = enroll_demo_node("node.beta", ("gpu.nvidia", "model.prewarm", "data.move"))
    store = NodeHeartbeatStore(identity_registry=registry, stale_after_seconds=10, expire_after_seconds=60)
    heartbeat = NodeHeartbeat.from_metrics(
        node_id="node.beta",
        sequence=7,
        session_id=session.id,
        capabilities=("gpu.nvidia", "model.prewarm", "data.move"),
        labels={"zone": "lab", "gpu": "rtx3070"},
        metrics={
            "cpu_cores": 8,
            "free_cpu_cores": 6,
            "memory_gb": 32,
            "free_memory_gb": 22,
            "gpu_vram_gb": 8,
            "free_vram_gb": 5,
            "gpu_utilization": 0.37,
            "queue_depth": 1,
            "latency_ms": 14,
        },
        data_locality=("models/llama-small",),
    )
    decision = store.ingest(heartbeat, session_token=session_token)
    print(f"heartbeat: {decision.status.value} node={decision.node_id} seq={heartbeat.sequence}")
    live = store.liveness("node.beta")
    print(f"liveness: {live.status.value} healthy={live.healthy} reason={live.reason}")

    router = ComputeRouter()
    store.sync_router(router)
    route = router.route(
        WorkloadRequest(
            kind=WorkloadKind.INTERACTIVE_INFERENCE,
            required_capabilities=("gpu.nvidia",),
            estimated_cpu_cores=1,
            estimated_memory_gb=2,
            estimated_vram_gb=2,
            interactive=True,
            model_id="llama-small",
            data_affinity=("models/llama-small",),
        )
    )
    print(f"route: {route.action.value} target={route.target_node} score={route.score:.4f}")

    stale_at = datetime.now(timezone.utc) + timedelta(seconds=15)
    stale = store.liveness("node.beta", now=stale_at)
    print(f"future liveness: {stale.status.value} healthy={stale.healthy}")


if __name__ == "__main__":
    main()
