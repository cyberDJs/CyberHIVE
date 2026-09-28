import time
import unittest

from cyberhive_core.cache_reuse import (
    CacheFabric,
    CacheScope,
    CanonicalOperation,
    ExecutionCost,
    ExecutionPattern,
    ReuseAction,
    ReuseEngine,
    SemanticIntent,
    Sensitivity,
)


class CacheReuseMVPTest(unittest.TestCase):
    def test_canonical_key_is_stable(self):
        left = CanonicalOperation(
            operation="inventory.node.memory",
            normalized_input={"node": "alpha", "unit": "gb"},
            configuration={"format": "short", "lang": "cs"},
        )
        right = CanonicalOperation(
            operation="inventory.node.memory",
            normalized_input={"unit": "gb", "node": "alpha"},
            configuration={"lang": "cs", "format": "short"},
        )
        self.assertEqual(left.key(), right.key())

    def test_unordered_collections_are_canonicalized_before_hashing(self):
        from cyberhive_core.cache_reuse import _stable

        self.assertEqual(_stable({"zeta", "alpha", "middle"}), ["alpha", "middle", "zeta"])
        left = CanonicalOperation(operation="cache.set", normalized_input={"items": {"zeta", "alpha", "middle"}})
        right = CanonicalOperation(operation="cache.set", normalized_input={"items": {"middle", "zeta", "alpha"}})
        self.assertEqual(left.key(), right.key())

    def test_exact_cache_hit_and_decision(self):
        cache = CacheFabric()
        op = CanonicalOperation(operation="runtime.status", normalized_input={"node": "alpha"}, revision=7)
        cache.put_exact(op, {"status": "healthy"}, ttl_seconds=60)
        hit = cache.get_exact(op)
        self.assertIsNotNone(hit)
        self.assertEqual(hit.value["status"], "healthy")

        decision = cache.choose_reuse(
            op,
            recompute_cost=ExecutionCost(cpu_ms=2500, wall_ms=3000, tool_calls=2),
            freshness_tolerance_seconds=60,
        )
        self.assertEqual(decision.action, ReuseAction.REUSE_EXACT)
        self.assertGreater(decision.estimated_saved_score, 0)

    def test_expired_entry_is_not_returned(self):
        cache = CacheFabric()
        op = CanonicalOperation(operation="short.ttl")
        cache.put_exact(op, "value", ttl_seconds=1)
        time.sleep(1.01)
        self.assertIsNone(cache.get_exact(op))

    def test_secret_cache_denied_by_default(self):
        cache = CacheFabric()
        op = CanonicalOperation(operation="secret.lookup")
        with self.assertRaises(ValueError):
            cache.put_exact(
                op,
                "secret",
                sensitivity=Sensitivity.SECRET,
                scope=CacheScope.PRIVATE,
                acl=("johnny",),
            )

    def test_sensitive_cache_requires_acl_and_safe_scope(self):
        cache = CacheFabric()
        op = CanonicalOperation(operation="camera.snapshot", normalized_input={"camera": "frontdoor"})
        with self.assertRaises(ValueError):
            cache.put_exact(
                op,
                {"snapshot": "..."},
                sensitivity=Sensitivity.SENSITIVE,
                scope=CacheScope.PUBLIC,
                ttl_seconds=60,
            )
        entry = cache.put_exact(
            op,
            {"snapshot": "..."},
            sensitivity=Sensitivity.SENSITIVE,
            scope=CacheScope.USER,
            ttl_seconds=60,
            acl=("petr",),
        )
        self.assertIsNone(cache.get_exact(op, subject="lucie"))
        self.assertEqual(cache.get_exact(op, subject="petr").key, entry.key)

    def test_semantic_cache(self):
        cache = CacheFabric()
        intent = SemanticIntent(
            intent="inventory.node.memory",
            entities={"node": "alpha"},
            qualifiers={"unit": "gb"},
            revision=9,
        )
        cache.put_semantic(intent, {"memory_gb": 32}, ttl_seconds=60)
        hit = cache.get_semantic(intent)
        self.assertIsNotNone(hit)
        self.assertEqual(hit.value["memory_gb"], 32)

    def test_state_cache_tracks_latest_revision(self):
        cache = CacheFabric()
        cache.put_state("runtime.alpha", revision=100, value={"queue": 1})
        cache.put_state("runtime.alpha", revision=101, value={"queue": 2})
        self.assertEqual(cache.get_state("runtime.alpha").value["queue"], 2)

    def test_artifact_cache(self):
        cache = CacheFabric()
        cache.put_artifact(
            "embedding.dataset-a",
            {"path": "cache/embedding.dataset-a.bin", "dimensions": 768},
            content_hash="sha256:abc",
        )
        hit = cache.get_artifact("embedding.dataset-a")
        self.assertEqual(hit.value["dimensions"], 768)

    def test_invalidate_by_dependency(self):
        cache = CacheFabric()
        op = CanonicalOperation(operation="knowledge.context", revision="k:1")
        cache.put_exact(op, "context", dependencies=("knowledge:runtime",), ttl_seconds=60)
        self.assertEqual(cache.store.invalidate_by_dependency("knowledge:runtime"), 1)
        self.assertIsNone(cache.get_exact(op))

    def test_execution_pattern_reuse(self):
        engine = ReuseEngine()
        pattern = ExecutionPattern(
            id="pat_log_anomaly_v1",
            pattern_type="log_anomaly_analysis",
            signature={"input": "logs", "scale": "medium", "goal": "anomaly_detection"},
            preferred_plan=("normalize", "partition", "aggregate", "detect", "rank", "report"),
            observed_cost=ExecutionCost(cpu_ms=5000, wall_ms=8000, tool_calls=4),
            success_rate=0.98,
            uses=12,
        )
        engine.cache.record_pattern(pattern)
        decision = engine.resolve_pattern(
            "log_anomaly_analysis",
            {"goal": "anomaly_detection", "scale": "medium", "input": "logs"},
        )
        self.assertEqual(decision.action, ReuseAction.REUSE_PLAN)
        self.assertEqual(decision.pattern_id, "pat_log_anomaly_v1")
        self.assertGreater(decision.confidence, 0.8)


if __name__ == "__main__":
    unittest.main()
