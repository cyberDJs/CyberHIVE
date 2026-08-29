from __future__ import annotations

from cyberhive_core.action_handlers import build_agent_handler_registry
from cyberhive_core.node_agent import AgentActionRequest, AgentActionType, LocalNodeAgent, NodeDescriptor
from cyberhive_core.resource_guard import LocalResourceGuard, ResourceBudget, ResourceRequest
from cyberhive_core.secure_channel import SecureChannel
from cyberhive_core.secure_node_gateway import SecureNodeGateway
from cyberhive_core.worker_runtime import NodeWorkerRuntime, WorkerEnvelopeStatus


def main() -> None:
    agent = LocalNodeAgent(NodeDescriptor(id="node.beta", allowed_actions=(AgentActionType.HEALTH_CHECK,)))
    registry = build_agent_handler_registry(agent)
    request = AgentActionRequest(target_node="node.beta", action=AgentActionType.HEALTH_CHECK, dry_run=True)
    result = registry.dispatch(request)
    assert result.status.value == "dry_run"

    guard = LocalResourceGuard(node_id="node.beta", budget=ResourceBudget(cpu_units=1, memory_mb=512, vram_mb=1024, io_weight=1, max_concurrent=1))
    reservation = guard.reserve(action="health_check", request=ResourceRequest(cpu_units=0.1, memory_mb=64), dry_run=True)
    assert reservation.granted

    channel = SecureChannel()
    gateway = SecureNodeGateway(channel=channel)
    gateway.store_session(session_id="sess-1", node_id="node.beta", token="token-1")
    envelope = gateway.build_action_envelope(node_id="node.beta", session_id="sess-1", action="health_check", dry_run=True, correlation_id="del-validate")
    runtime = NodeWorkerRuntime(node_id="node.beta", session_id="sess-1", session_token="token-1", channel=channel, handlers=registry, resource_guard=guard)
    outcome = runtime.process_action_envelope(envelope)
    assert outcome.status == WorkerEnvelopeStatus.HANDLED
    assert outcome.ack_envelope is not None
    assert outcome.result_envelope is not None
    print("OK: Worker Runtime Block A validation passed")


if __name__ == "__main__":
    main()
