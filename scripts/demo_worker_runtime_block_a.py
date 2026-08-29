from __future__ import annotations

from cyberhive_core.action_handlers import build_agent_handler_registry
from cyberhive_core.node_agent import AgentActionType, LocalNodeAgent, NodeAgentPolicy, NodeDescriptor
from cyberhive_core.node_delivery import NodeDeliveryService
from cyberhive_core.node_reconciliation import NodeResultReconciler
from cyberhive_core.resource_guard import LocalResourceGuard, ResourceBudget
from cyberhive_core.secure_channel import SecureChannel
from cyberhive_core.secure_node_gateway import SecureNodeGateway
from cyberhive_core.worker_runtime import NodeWorkerRuntime


def main() -> None:
    channel = SecureChannel()
    gateway = SecureNodeGateway(channel=channel)
    gateway.store_session(session_id="sess-1", node_id="node.beta", token="token-1")
    delivery = NodeDeliveryService(gateway=gateway)

    agent = LocalNodeAgent(
        NodeDescriptor(id="node.beta", allowed_actions=(AgentActionType.HEALTH_CHECK, AgentActionType.PREWARM_MODEL)),
        policy=NodeAgentPolicy(allow_live_actions=False),
    )
    runtime = NodeWorkerRuntime(
        node_id="node.beta",
        session_id="sess-1",
        session_token="token-1",
        channel=channel,
        handlers=build_agent_handler_registry(agent),
        resource_guard=LocalResourceGuard(node_id="node.beta", budget=ResourceBudget(cpu_units=2, memory_mb=2048, vram_mb=2048, io_weight=2, max_concurrent=2)),
    )
    reconciler = NodeResultReconciler()

    item = delivery.enqueue_action(node_id="node.beta", session_id="sess-1", action="health_check", dry_run=True, metadata={"execution_run_id": "run-demo"})
    dispatch = delivery.dispatch_ready()[0]
    reconciler.register_delivery(item, execution_run_id="run-demo")
    outcome = runtime.process_action_envelope(gateway.outbox[-1])
    delivery.receive_ack_envelope(outcome.ack_envelope)
    reconciler.sync_delivery(item)
    result_receipt = gateway.receive(outcome.result_envelope)
    record = reconciler.ingest_gateway_receipt(result_receipt)
    summary = reconciler.summary_for_execution_run("run-demo")

    print(f"dispatch: {dispatch.status.value} delivery={item.id} envelope={dispatch.envelope_id}")
    print(f"worker: {outcome.status.value} result={outcome.action_result.status.value}")
    print(f"task: {record.status.value} reason={record.history[-1].reason}")
    print(f"summary: {summary.status} total={summary.total} succeeded={summary.succeeded} failed={summary.failed}")


if __name__ == "__main__":
    main()
