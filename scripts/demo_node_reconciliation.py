from __future__ import annotations

from cyberhive_core.node_delivery import DeliveryPolicy, ReliableDeliveryQueue
from cyberhive_core.node_reconciliation import NodeResultReconciler
from cyberhive_core.secure_channel import ChannelDirection, ChannelPurpose
from cyberhive_core.secure_node_gateway import GatewayMessageStatus, GatewayReceipt


def receipt(purpose: ChannelPurpose, payload: dict, envelope_id: str, session_id: str = "sess.demo") -> GatewayReceipt:
    return GatewayReceipt(
        status=GatewayMessageStatus.RECORDED,
        envelope_id=envelope_id,
        node_id="node.beta",
        purpose=purpose,
        direction=ChannelDirection.NODE_TO_CONTROLLER,
        reason="demo receipt",
        result=payload,
        session_id=session_id,
    )


def main() -> None:
    queue = ReliableDeliveryQueue(policy=DeliveryPolicy(max_attempts=2, ack_timeout_seconds=2, ttl_seconds=60))
    ok = queue.enqueue_action(
        node_id="node.beta",
        session_id="sess.demo",
        action="prewarm_model",
        payload={"model_id": "llama-small"},
        metadata={"execution_run_id": "exec.demo", "plan_id": "plan.demo"},
    )
    failed = queue.enqueue_action(
        node_id="node.beta",
        session_id="sess.demo",
        action="data_move",
        payload={"object_id": "dataset.hot"},
        metadata={"execution_run_id": "exec.demo", "plan_id": "plan.demo"},
    )

    reconciler = NodeResultReconciler()
    reconciler.register_delivery(ok)
    reconciler.register_delivery(failed)

    reconciler.ingest_gateway_receipt(receipt(ChannelPurpose.ACK, {"delivery_id": ok.id}, "msg.demo.ack"))
    reconciler.ingest_gateway_receipt(
        receipt(ChannelPurpose.ACTION_RESULT, {"delivery_id": ok.id, "status": "succeeded", "action": "prewarm_model"}, "msg.demo.result.ok")
    )
    reconciler.ingest_gateway_receipt(
        receipt(ChannelPurpose.ERROR, {"delivery_id": failed.id, "error": "node refused data move in MVP"}, "msg.demo.result.fail")
    )

    summary = reconciler.summary_for_execution_run("exec.demo")
    print(f"task ok: {ok.id} -> {reconciler.require(ok.id).status.value}")
    print(f"task failed: {failed.id} -> {reconciler.require(failed.id).status.value}")
    print(
        "summary: "
        f"status={summary.status} total={summary.total} succeeded={summary.succeeded} failed={summary.failed} pending={summary.pending}"
    )


if __name__ == "__main__":
    main()
