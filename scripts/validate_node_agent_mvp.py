#!/usr/bin/env python3
from __future__ import annotations

from cyberhive_core.node_agent import (
    AgentActionRequest,
    AgentActionStatus,
    AgentActionType,
    LocalNodeAgent,
    NodeAgentPolicy,
    NodeDescriptor,
)


def main() -> None:
    agent = LocalNodeAgent(
        NodeDescriptor(id="node.validation", allowed_actions=(AgentActionType.HEALTH_CHECK, AgentActionType.PREWARM_MODEL)),
        policy=NodeAgentPolicy(allow_live_actions=True, allow_prewarm=True),
    )
    health = agent.handle(AgentActionRequest(target_node="node.validation", action=AgentActionType.HEALTH_CHECK))
    if health.status != AgentActionStatus.DRY_RUN:
        raise SystemExit("health dry-run did not pass")
    prewarm = agent.handle(
        AgentActionRequest(
            target_node="node.validation",
            action=AgentActionType.PREWARM_MODEL,
            payload={"model_id": "llama-small"},
            dry_run=False,
            approval_tokens=("runtime.prewarm.execute",),
        )
    )
    if prewarm.status != AgentActionStatus.SUCCEEDED:
        raise SystemExit(f"prewarm failed: {prewarm.reason}")
    if "llama-small" not in agent.warmed_models:
        raise SystemExit("prewarm did not record warmed model")
    print("OK: Node Agent & Action Dispatch MVP validation passed")


if __name__ == "__main__":
    main()
