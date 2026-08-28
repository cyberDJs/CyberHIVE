from __future__ import annotations

from datetime import datetime, timedelta, timezone
import tempfile
import unittest

from cyberhive_core.node_delivery import DeliveryPolicy, DeliveryStatus, ReliableDeliveryQueue
from cyberhive_core.node_reconciliation import (
    NodeResultReconciler,
    NodeTaskStatus,
    ReconciliationJournal,
)
from cyberhive_core.secure_channel import ChannelDirection, ChannelPurpose
from cyberhive_core.secure_node_gateway import GatewayMessageStatus, GatewayReceipt


def _receipt(*, purpose: ChannelPurpose, payload: dict, status: GatewayMessageStatus = GatewayMessageStatus.RECORDED, envelope_id: str = "msg_result") -> GatewayReceipt:
    return GatewayReceipt(
        status=status,
        envelope_id=envelope_id,
        node_id="node.beta",
        purpose=purpose,
        direction=ChannelDirection.NODE_TO_CONTROLLER,
        reason="test receipt",
        result=payload,
    )


class NodeResultReconciliationTests(unittest.TestCase):
    def test_register_delivery_creates_task_record(self) -> None:
        queue = ReliableDeliveryQueue()
        item = queue.enqueue_action(
            node_id="node.beta",
            session_id="sess_1",
            action="prewarm_model",
            metadata={"plan_id": "plan_1", "execution_run_id": "exec_1", "request_id": "req_1"},
        )
        reconciler = NodeResultReconciler()

        record = reconciler.register_delivery(item)

        self.assertEqual(record.delivery_id, item.id)
        self.assertEqual(record.node_id, "node.beta")
        self.assertEqual(record.plan_id, "plan_1")
        self.assertEqual(record.execution_run_id, "exec_1")
        self.assertEqual(record.status, NodeTaskStatus.REGISTERED)

    def test_ack_receipt_marks_task_acked(self) -> None:
        queue = ReliableDeliveryQueue()
        item = queue.enqueue_action(node_id="node.beta", session_id="sess_1", action="prewarm_model")
        reconciler = NodeResultReconciler()
        reconciler.register_delivery(item)

        record = reconciler.ingest_gateway_receipt(_receipt(purpose=ChannelPurpose.ACK, payload={"delivery_id": item.id}))

        self.assertIsNotNone(record)
        self.assertEqual(record.status, NodeTaskStatus.ACKED)
        self.assertIsNotNone(record.acknowledged_at)

    def test_action_result_success_marks_task_succeeded(self) -> None:
        queue = ReliableDeliveryQueue()
        item = queue.enqueue_action(node_id="node.beta", session_id="sess_1", action="prewarm_model")
        reconciler = NodeResultReconciler()
        reconciler.register_delivery(item)

        record = reconciler.ingest_gateway_receipt(
            _receipt(
                purpose=ChannelPurpose.ACTION_RESULT,
                payload={"delivery_id": item.id, "status": "succeeded", "request_id": "act_1", "action": "prewarm_model"},
            )
        )

        self.assertIsNotNone(record)
        self.assertEqual(record.status, NodeTaskStatus.SUCCEEDED)
        self.assertTrue(record.ok)
        self.assertIsNotNone(record.completed_at)
        self.assertEqual(record.result_payload["request_id"], "act_1")

    def test_action_result_failure_marks_task_failed(self) -> None:
        queue = ReliableDeliveryQueue()
        item = queue.enqueue_action(node_id="node.beta", session_id="sess_1", action="data_move")
        reconciler = NodeResultReconciler()
        reconciler.register_delivery(item)

        record = reconciler.ingest_gateway_receipt(
            _receipt(purpose=ChannelPurpose.ACTION_RESULT, payload={"delivery_id": item.id, "status": "failed", "reason": "disk pressure"})
        )

        self.assertIsNotNone(record)
        self.assertEqual(record.status, NodeTaskStatus.FAILED)
        self.assertFalse(record.ok)

    def test_error_receipt_marks_task_failed(self) -> None:
        queue = ReliableDeliveryQueue()
        item = queue.enqueue_action(node_id="node.beta", session_id="sess_1", action="cache_prime")
        reconciler = NodeResultReconciler()
        reconciler.register_delivery(item)

        record = reconciler.ingest_gateway_receipt(
            _receipt(purpose=ChannelPurpose.ERROR, payload={"delivery_id": item.id, "error": "node refused action"})
        )

        self.assertIsNotNone(record)
        self.assertEqual(record.status, NodeTaskStatus.FAILED)
        self.assertEqual(record.error_payload["error"], "node refused action")

    def test_delivery_dead_letter_sync_is_terminal(self) -> None:
        queue = ReliableDeliveryQueue(policy=DeliveryPolicy(max_attempts=1, ack_timeout_seconds=1, ttl_seconds=30))
        item = queue.enqueue_action(node_id="node.beta", session_id="sess_1", action="noop")
        item.status = DeliveryStatus.DISPATCHED
        item.attempts = 1
        item.last_attempt_at = datetime.now(timezone.utc) - timedelta(seconds=5)
        queue.sweep_timeouts()
        reconciler = NodeResultReconciler()

        record = reconciler.sync_delivery(item)

        self.assertEqual(record.status, NodeTaskStatus.DEAD_LETTER)
        self.assertTrue(record.terminal)

    def test_unknown_action_result_becomes_orphan(self) -> None:
        reconciler = NodeResultReconciler()

        record = reconciler.ingest_gateway_receipt(
            _receipt(purpose=ChannelPurpose.ACTION_RESULT, payload={"status": "succeeded", "request_id": "act_orphan"}, envelope_id="msg_orphan")
        )

        self.assertIsNotNone(record)
        self.assertEqual(record.status, NodeTaskStatus.ORPHANED)
        self.assertTrue(record.terminal)

    def test_non_recorded_receipt_is_ignored(self) -> None:
        reconciler = NodeResultReconciler()

        record = reconciler.ingest_gateway_receipt(
            _receipt(purpose=ChannelPurpose.ACK, payload={"delivery_id": "del_missing"}, status=GatewayMessageStatus.DENIED)
        )

        self.assertIsNone(record)
        self.assertEqual(len(reconciler.ignored_receipts), 1)

    def test_run_summary_tracks_success_and_failure(self) -> None:
        queue = ReliableDeliveryQueue()
        ok = queue.enqueue_action(
            node_id="node.beta",
            session_id="sess_1",
            action="prewarm_model",
            metadata={"execution_run_id": "exec_1"},
        )
        bad = queue.enqueue_action(
            node_id="node.beta",
            session_id="sess_1",
            action="data_move",
            metadata={"execution_run_id": "exec_1"},
        )
        reconciler = NodeResultReconciler()
        reconciler.register_delivery(ok)
        reconciler.register_delivery(bad)
        reconciler.ingest_gateway_receipt(_receipt(purpose=ChannelPurpose.ACTION_RESULT, payload={"delivery_id": ok.id, "status": "succeeded"}))
        reconciler.ingest_gateway_receipt(_receipt(purpose=ChannelPurpose.ERROR, payload={"delivery_id": bad.id, "error": "timeout"}))

        summary = reconciler.summary_for_execution_run("exec_1")

        self.assertEqual(summary.total, 2)
        self.assertEqual(summary.succeeded, 1)
        self.assertEqual(summary.failed, 1)
        self.assertEqual(summary.status, "failed")

    def test_journal_appends_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal = ReconciliationJournal(f"{tmp}/node-reconciliation.jsonl")
            queue = ReliableDeliveryQueue()
            item = queue.enqueue_action(node_id="node.beta", session_id="sess_1", action="noop")
            reconciler = NodeResultReconciler(journal=journal)
            reconciler.register_delivery(item)
            reconciler.ingest_gateway_receipt(_receipt(purpose=ChannelPurpose.ACK, payload={"delivery_id": item.id}))

            self.assertEqual(journal.count(), 1)
            self.assertEqual(journal.iter_records()[0]["status"], "acked")


if __name__ == "__main__":
    unittest.main()
