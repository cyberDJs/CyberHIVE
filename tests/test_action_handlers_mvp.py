from __future__ import annotations

import unittest

from cyberhive_core.action_handlers import ActionHandlerContext, ActionHandlerError, build_agent_handler_registry
from cyberhive_core.node_agent import AgentActionRequest, AgentActionStatus, AgentActionType, LocalNodeAgent, NodeAgentPolicy, NodeDescriptor


class ActionHandlerRegistryTests(unittest.TestCase):
    def build_agent(self) -> LocalNodeAgent:
        return LocalNodeAgent(
            NodeDescriptor(
                id="node.beta",
                allowed_actions=(AgentActionType.HEALTH_CHECK, AgentActionType.PREWARM_MODEL, AgentActionType.NOOP),
            ),
            policy=NodeAgentPolicy(allow_live_actions=False),
        )

    def test_default_registry_wraps_local_node_agent(self) -> None:
        registry = build_agent_handler_registry(self.build_agent())
        request = AgentActionRequest(target_node="node.beta", action=AgentActionType.HEALTH_CHECK, dry_run=True)
        result = registry.dispatch(request, ActionHandlerContext(node_id="node.beta", dry_run=True))
        self.assertEqual(result.status, AgentActionStatus.DRY_RUN)
        self.assertIn("health_check", registry.registered_actions())

    def test_unknown_action_fails_closed(self) -> None:
        registry = build_agent_handler_registry(self.build_agent())
        request = AgentActionRequest(target_node="node.beta", action=AgentActionType.DATA_MOVE, dry_run=True)
        result = registry.dispatch(request, ActionHandlerContext(node_id="node.beta", dry_run=True))
        self.assertEqual(result.status, AgentActionStatus.DENIED)
        self.assertIn("no handler", result.reason)

    def test_duplicate_registration_requires_replace(self) -> None:
        registry = build_agent_handler_registry(self.build_agent())
        with self.assertRaises(ActionHandlerError):
            registry.register(AgentActionType.HEALTH_CHECK, lambda request, context: self.build_agent().handle(request))


if __name__ == "__main__":
    unittest.main()
