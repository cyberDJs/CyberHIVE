#!/usr/bin/env python3
"""Demonstrate CyberHIVE Cache & Reuse Fabric MVP."""

from cyberhive_core.cache_reuse import (
    CacheFabric,
    CanonicalOperation,
    ExecutionCost,
    ExecutionPattern,
    ReuseEngine,
    SemanticIntent,
)


def main() -> int:
    cache = CacheFabric()
    engine = ReuseEngine(cache)

    op = CanonicalOperation(
        operation="knowledge.context",
        normalized_input={"topic": "rtx3070-runtime-selection"},
        relevant_state={"knowledge_revision": "kh-293"},
        model_version="retriever-v1",
        revision="kh-293",
    )
    cache.put_exact(
        op,
        {"context_id": "ctx_rtx3070_runtime", "chunks": 8},
        ttl_seconds=300,
        dependencies=("knowledge:rtx3070", "model:retriever-v1"),
        tags=("knowledge", "rtx3070"),
    )

    decision = engine.resolve_operation(
        op,
        recompute_cost=ExecutionCost(cpu_ms=4200, wall_ms=5800, token_count=3200, tool_calls=3),
        freshness_tolerance_seconds=300,
    )
    print(f"operation decision: {decision.action.value} key={decision.cache_key}")
    print(f"  reason: {decision.reason}")
    print(f"  saved_score: {decision.estimated_saved_score:.4f}")

    intent = SemanticIntent(
        intent="inventory.node.memory",
        entities={"node": "alpha"},
        qualifiers={"unit": "gb"},
        revision=12,
    )
    cache.put_semantic(intent, {"memory_gb": 32}, ttl_seconds=120)
    semantic_hit = cache.get_semantic(intent)
    print(f"semantic cache: memory_gb={semantic_hit.value['memory_gb']} hits={semantic_hit.hits}")

    pattern = ExecutionPattern(
        id="pat_log_anomaly_v1",
        pattern_type="log_anomaly_analysis",
        signature={"input": "logs", "scale": "medium", "goal": "anomaly_detection"},
        preferred_plan=("normalize", "partition", "aggregate", "detect", "rank", "report"),
        observed_cost=ExecutionCost(cpu_ms=9000, wall_ms=14000, tool_calls=5),
        success_rate=0.98,
        uses=14,
    )
    cache.record_pattern(pattern)
    pattern_decision = engine.resolve_pattern(
        "log_anomaly_analysis",
        {"goal": "anomaly_detection", "input": "logs", "scale": "medium"},
    )
    print(f"pattern decision: {pattern_decision.action.value} pattern={pattern_decision.pattern_id}")
    print(f"  confidence: {pattern_decision.confidence:.4f}")
    print(f"  plan: {', '.join(pattern.preferred_plan)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
