import unittest
from datetime import datetime, timedelta, timezone

from cyberhive_core.node_heartbeat import (
    HeartbeatStatus,
    LivenessStatus,
    NodeHeartbeat,
    NodeHeartbeatStore,
)
from cyberhive_core.node_identity import EnrollmentAuthority, NodeIdentityRegistry
from cyberhive_core.scheduler_router import ComputeRouter, WorkloadKind, WorkloadRequest


def enrolled_store():
    registry = NodeIdentityRegistry()
    authority = EnrollmentAuthority(registry)
    token, secret = authority.create_bootstrap_token(ttl_seconds=300)
    req = authority.build_request(
        proposed_node_id="node.alpha",
        public_key="ssh-ed25519 node-alpha-test",
        token_id=token.id,
        token_secret=secret,
        capabilities=("gpu.nvidia", "model.prewarm", "data.move"),
        labels={"zone": "lab"},
    )
    assert authority.evaluate(req).approved
    session, session_token = registry.issue_session("node.alpha")
    return registry, session, session_token, NodeHeartbeatStore(identity_registry=registry, stale_after_seconds=10, expire_after_seconds=60)


def heartbeat(seq=1, *, node_id="node.alpha", session_id="session"):
    return NodeHeartbeat.from_metrics(
        node_id=node_id,
        sequence=seq,
        session_id=session_id,
        capabilities=("gpu.nvidia", "model.prewarm", "data.move"),
        labels={"zone": "lab"},
        metrics={
            "cpu_cores": 8,
            "free_cpu_cores": 5,
            "memory_gb": 32,
            "free_memory_gb": 20,
            "gpu_vram_gb": 8,
            "free_vram_gb": 5,
            "gpu_utilization": 0.4,
            "queue_depth": 2,
            "latency_ms": 20,
        },
        data_locality=("models/llama-small",),
    )


class NodeHeartbeatMvpTests(unittest.TestCase):
    def test_accepts_authenticated_heartbeat(self):
        _, session, token, store = enrolled_store()
        decision = store.ingest(heartbeat(session_id=session.id), session_token=token)
        self.assertEqual(decision.status, HeartbeatStatus.ACCEPTED)
        self.assertTrue(store.liveness("node.alpha").healthy)

    def test_denies_invalid_session(self):
        _, session, _, store = enrolled_store()
        decision = store.ingest(heartbeat(session_id=session.id), session_token="wrong")
        self.assertEqual(decision.status, HeartbeatStatus.DENIED)
        self.assertIn("invalid node session", decision.reason)

    def test_denies_unknown_node_when_identity_registry_is_enabled(self):
        registry, _, _, _ = enrolled_store()
        store = NodeHeartbeatStore(identity_registry=registry)
        decision = store.ingest(heartbeat(node_id="node.ghost", session_id="missing"), session_token="token")
        self.assertEqual(decision.status, HeartbeatStatus.DENIED)

    def test_rejects_sequence_regression(self):
        _, session, token, store = enrolled_store()
        self.assertTrue(store.ingest(heartbeat(seq=2, session_id=session.id), session_token=token).accepted)
        decision = store.ingest(heartbeat(seq=1, session_id=session.id), session_token=token)
        self.assertEqual(decision.status, HeartbeatStatus.DENIED)
        self.assertIn("moved backwards", decision.reason)

    def test_duplicate_sequence_is_idempotent(self):
        _, session, token, store = enrolled_store()
        self.assertEqual(store.ingest(heartbeat(seq=3, session_id=session.id), session_token=token).status, HeartbeatStatus.ACCEPTED)
        self.assertEqual(store.ingest(heartbeat(seq=3, session_id=session.id), session_token=token).status, HeartbeatStatus.DUPLICATE)

    def test_liveness_transitions_to_stale_and_expired(self):
        _, session, token, store = enrolled_store()
        base = datetime.now(timezone.utc)
        hb = heartbeat(seq=1, session_id=session.id)
        hb = NodeHeartbeat.from_metrics(
            node_id=hb.node_id,
            sequence=hb.sequence,
            session_id=hb.session_id,
            capabilities=hb.capabilities,
            labels=hb.labels,
            metrics=hb.as_dict()["metrics"],
            data_locality=hb.data_locality,
            observed_at=base,
        )
        store.ingest(hb, session_token=token, now=base)
        self.assertEqual(store.liveness("node.alpha", now=base + timedelta(seconds=11)).status, LivenessStatus.STALE)
        self.assertEqual(store.liveness("node.alpha", now=base + timedelta(seconds=61)).status, LivenessStatus.EXPIRED)

    def test_syncs_to_scheduler_router(self):
        _, session, token, store = enrolled_store()
        store.ingest(heartbeat(session_id=session.id), session_token=token)
        router = ComputeRouter()
        store.sync_router(router)
        decision = router.route(WorkloadRequest(kind=WorkloadKind.INTERACTIVE_INFERENCE, required_capabilities=("gpu.nvidia",), estimated_vram_gb=2, interactive=True))
        self.assertEqual(decision.target_node, "node.alpha")

    def test_snapshot_can_become_node_descriptor(self):
        _, session, token, store = enrolled_store()
        store.ingest(heartbeat(session_id=session.id), session_token=token)
        descriptor = store.require_snapshot("node.alpha").to_node_descriptor()
        self.assertEqual(descriptor.id, "node.alpha")
        self.assertTrue(descriptor.supports_action("prewarm_model"))


if __name__ == "__main__":
    unittest.main()
