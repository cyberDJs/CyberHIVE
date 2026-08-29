from __future__ import annotations

from datetime import datetime, timezone
import unittest

from cyberhive_core.action_handlers import build_agent_handler_registry
from cyberhive_core.node_agent import AgentActionResult, AgentActionStatus, AgentActionType, LocalNodeAgent, NodeAgentPolicy, NodeDescriptor
from cyberhive_core.node_delivery import NodeDeliveryService
from cyberhive_core.node_reconciliation import NodeResultReconciler, NodeTaskStatus
from cyberhive_core.resource_guard import LocalResourceGuard, ResourceBudget
from cyberhive_core.secure_channel import SecureChannel
from cyberhive_core.secure_node_gateway import SecureNodeGateway
from cyberhive_core.worker_runtime import NodeWorkerRuntime, WorkerEnvelopeStatus, WorkerRuntimePolicy


class WorkerRuntimeTests(unittest.TestCase):
    def build_stack(self):
        channel = SecureChannel()
        gateway = SecureNodeGateway(channel=channel)
        gateway.store_session(session_id="sess-1", node_id="node.beta", token="token-1")
        delivery = NodeDeliveryService(gateway=gateway)
        agent = LocalNodeAgent(
            NodeDescriptor(
                id="node.beta",
                allowed_actions=(AgentActionType.HEALTH_CHECK, AgentActionType.PREWARM_MODEL, AgentActionType.NOOP),
            ),
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
        return channel, gateway, delivery, runtime

    def test_worker_runtime_acknowledges_handles_and_reconciles_result(self) -> None:
        _channel, gateway, delivery, runtime = self.build_stack()
        item = delivery.enqueue_action(node_id="node.beta", session_id="sess-1", action="health_check", dry_run=True, metadata={"execution_run_id": "run-1"})
        dispatch = delivery.dispatch_ready()[0]
        self.assertTrue(dispatch.ok)
        action_envelope = gateway.outbox[-1]

        reconciler = NodeResultReconciler()
        reconciler.register_delivery(item, execution_run_id="run-1")
        outcome = runtime.process_action_envelope(action_envelope)

        self.assertEqual(outcome.status, WorkerEnvelopeStatus.HANDLED)
        self.assertIsNotNone(outcome.ack_envelope)
        self.assertIsNotNone(outcome.result_envelope)
        self.assertEqual(outcome.action_result.status, AgentActionStatus.DRY_RUN)

        delivery.receive_ack_envelope(outcome.ack_envelope)
        reconciler.sync_delivery(item)
        result_receipt = gateway.receive(outcome.result_envelope)
        record = reconciler.ingest_gateway_receipt(result_receipt)

        self.assertEqual(item.status.value, "acked")
        self.assertEqual(record.status, NodeTaskStatus.SUCCEEDED)
        summary = reconciler.summary_for_execution_run("run-1")
        self.assertEqual(summary.status, "succeeded")

    def test_worker_denies_when_resource_guard_required_but_missing(self) -> None:
        channel = SecureChannel()
        gateway = SecureNodeGateway(channel=channel)
        gateway.store_session(session_id="sess-1", node_id="node.beta", token="token-1")
        agent = LocalNodeAgent(NodeDescriptor(id="node.beta", allowed_actions=(AgentActionType.HEALTH_CHECK,)))
        runtime = NodeWorkerRuntime(
            node_id="node.beta",
            session_id="sess-1",
            session_token="token-1",
            channel=channel,
            handlers=build_agent_handler_registry(agent),
            resource_guard=None,
            policy=WorkerRuntimePolicy(require_resource_guard=True),
        )
        envelope = gateway.build_action_envelope(node_id="node.beta", session_id="sess-1", action="health_check", dry_run=True, correlation_id="del-test")
        outcome = runtime.process_action_envelope(envelope)
        self.assertEqual(outcome.status, WorkerEnvelopeStatus.DENIED)
        self.assertIn("resource guard required", outcome.reason)

    def test_worker_rejects_unsupported_action_without_acknowledging_first(self) -> None:
        _channel, gateway, _delivery, runtime = self.build_stack()
        envelope = gateway.build_action_envelope(node_id="node.beta", session_id="sess-1", action="unsupported_action", dry_run=True, correlation_id="del-bad")

        outcome = runtime.process_action_envelope(envelope)

        self.assertEqual(outcome.status, WorkerEnvelopeStatus.DENIED)
        self.assertIsNone(outcome.ack_envelope)
        self.assertIsNotNone(outcome.result_envelope)
        self.assertEqual(outcome.result_envelope.payload["status"], AgentActionStatus.DENIED.value)
        self.assertEqual(outcome.result_envelope.payload["metadata"]["requested_action"], "unsupported_action")
        self.assertEqual(len(runtime.outbox), 1)

    def test_worker_enforces_result_payload_limit(self) -> None:
        _channel, gateway, delivery, runtime = self.build_stack()
        runtime.policy = WorkerRuntimePolicy(max_result_payload_bytes=1024)

        def large_result(_request, _context):
            current = datetime.now(timezone.utc)
            return AgentActionResult(
                request_id="large-result",
                target_node="node.beta",
                action=AgentActionType.HEALTH_CHECK,
                status=AgentActionStatus.DRY_RUN,
                reason="large result",
                created_at=current,
                completed_at=current,
                metadata={"blob": "x" * 4096},
                events=("y" * 4096,),
            )

        runtime.handlers.register(AgentActionType.HEALTH_CHECK, large_result, replace=True)
        item = delivery.enqueue_action(node_id="node.beta", session_id="sess-1", action="health_check", dry_run=True)
        dispatch = delivery.dispatch_ready()[0]
        outcome = runtime.process_action_envelope(gateway.outbox[-1])

        self.assertTrue(dispatch.ok)
        self.assertEqual(outcome.status, WorkerEnvelopeStatus.HANDLED)
        payload = outcome.result_envelope.payload
        self.assertEqual(payload["status"], AgentActionStatus.FAILED.value)
        self.assertTrue(payload["metadata"]["result_payload_truncated"])
        self.assertLessEqual(runtime._result_payload_bytes(payload), runtime.policy.max_result_payload_bytes)


if __name__ == "__main__":
    unittest.main()
