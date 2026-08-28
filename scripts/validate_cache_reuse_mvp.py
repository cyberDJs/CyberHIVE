#!/usr/bin/env python3
"""Validate CyberHIVE Cache & Reuse Fabric MVP."""

from cyberhive_core.cache_reuse import (
    CacheFabric,
    CanonicalOperation,
    ExecutionCost,
    ExecutionPattern,
    ReuseAction,
    ReuseEngine,
    SemanticIntent,
)


def main() -> int:
    cache = CacheFabric()

    op = CanonicalOperation(
        operation="inventory.node.memory",
        normalized_input={"node": "alpha", "unit": "gb"},
        relevant_state={"inventory_revision": 42},
        revision=42,
    )
    cache.put_exact(op, {"memory_gb": 32}, ttl_seconds=60, dependencies=("inventory:42",))
    decision = cache.choose_reuse(
        op,
        recompute_cost=ExecutionCost(cpu_ms=1500, wall_ms=2200, tool_calls=1),
        freshness_tolerance_seconds=60,
    )
    assert decision.action == ReuseAction.REUSE_EXACT
    assert decision.entry is not None
    assert decision.entry.value["memory_gb"] == 32

    intent = SemanticIntent(
        intent="inventory.node.memory",
        entities={"node": "alpha"},
        qualifiers={"unit": "gb"},
        revision=42,
    )
    cache.put_semantic(intent, {"memory_gb": 32}, ttl_seconds=60, dependencies=("inventory:42",))
    semantic = cache.get_semantic(intent)
    assert semantic is not None
    assert semantic.value["memory_gb"] == 32

    engine = ReuseEngine(cache)
    pattern = ExecutionPattern(
        id="pat_runtime_status_v1",
        pattern_type="runtime_status_report",
        signature={"input": "state", "goal": "status_report"},
        preferred_plan=("load_state", "summarize", "report"),
        observed_cost=ExecutionCost(cpu_ms=500, wall_ms=700, tool_calls=1),
        success_rate=0.97,
        uses=10,
    )
    cache.record_pattern(pattern)
    pattern_decision = engine.resolve_pattern(
        "runtime_status_report",
        {"goal": "status_report", "input": "state"},
    )
    assert pattern_decision.action == ReuseAction.REUSE_PLAN

    removed = cache.store.invalidate_by_dependency("inventory:42")
    assert removed >= 2

    print("OK: Cache & Reuse Fabric MVP validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
