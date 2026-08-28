from __future__ import annotations

from cyberhive_core.node_delivery import ReliableDeliveryQueue
from cyberhive_core.node_reconciliation import NodeResultReconciler, NodeTaskStatus
from cyberhive_core.secure_channel import ChannelDirection, ChannelPurpose
from cyberhive_core.secure_node_gateway import GatewayMessageStatus, GatewayReceipt


def main() -> None:
    queue = ReliableDeliveryQueue()
    item = queue.enqueue_action(
        node_id="node.beta",
        session_id="sess.validation",
        action="prewarm_model",
        payload={"model_id": "llama-small"},
        metadata={"plan_id": "plan.validation", "execution_run_id": "exec.validation"},
    )
    reconciler = NodeResultReconciler()
    record = reconciler.register_delivery(item)
    if record.status != NodeTaskStatus.REGISTERED:
        raise SystemExit("record was not registered")

    ack = GatewayReceipt(
        status=GatewayMessageStatus.RECORDED,
        envelope_id="msg.validation.ack",
        node_id="node.beta",
        purpose=ChannelPurpose.ACK,
        direction=ChannelDirection.NODE_TO_CONTROLLER,
        reason="ack recorded",
        result={"delivery_id": item.id},
    )
    record = reconciler.ingest_gateway_receipt(ack)
    if record is None or record.status != NodeTaskStatus.ACKED:
        raise SystemExit("ACK was not reconciled")

    result = GatewayReceipt(
        status=GatewayMessageStatus.RECORDED,
        envelope_id="msg.validation.result",
        node_id="node.beta",
        purpose=ChannelPurpose.ACTION_RESULT,
        direction=ChannelDirection.NODE_TO_CONTROLLER,
        reason="action result recorded",
        result={"delivery_id": item.id, "status": "succeeded", "action": "prewarm_model"},
    )
    record = reconciler.ingest_gateway_receipt(result)
    if record is None or record.status != NodeTaskStatus.SUCCEEDED:
        raise SystemExit("action result was not reconciled")

    summary = reconciler.summary_for_execution_run("exec.validation")
    if summary.status != "succeeded":
        raise SystemExit(f"unexpected summary status: {summary.status}")

    print("OK: Node Result Reconciliation MVP validation passed")


if __name__ == "__main__":
    main()
