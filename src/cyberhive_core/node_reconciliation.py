"""CyberHIVE Node Result Reconciliation MVP.

Patch 019 made node message delivery reliable up to ACK/dead-letter state.
This module adds the missing reconciliation boundary between delivery/gateway
receipts and execution-visible node task state.

The MVP does not execute remote work and does not trust unauthenticated payloads.
It consumes already-verified SecureNodeGateway receipts, correlates ACK/result/error
messages with delivery items, records auditable history and projects per-run state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import json
from pathlib import Path
from typing import Any, Mapping, Sequence
import uuid

from .node_delivery import DeliveryItem, DeliveryStatus
from .secure_channel import ChannelDirection, ChannelPurpose
from .secure_node_gateway import GatewayMessageStatus, GatewayReceipt


class ReconciliationError(RuntimeError):
    """Raised when node-result reconciliation input is invalid."""


class NodeTaskStatus(str, Enum):
    """Controller-side view of one node task lifecycle."""

    REGISTERED = "registered"
    QUEUED = "queued"
    DISPATCHED = "dispatched"
    RETRY_WAIT = "retry_wait"
    ACKED = "acked"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"
    ORPHANED = "orphaned"
    IGNORED = "ignored"


_TERMINAL_STATUSES = {
    NodeTaskStatus.SUCCEEDED,
    NodeTaskStatus.FAILED,
    NodeTaskStatus.EXPIRED,
    NodeTaskStatus.DEAD_LETTER,
    NodeTaskStatus.CANCELLED,
    NodeTaskStatus.ORPHANED,
}


_DELIVERY_STATUS_MAP = {
    DeliveryStatus.QUEUED: NodeTaskStatus.QUEUED,
    DeliveryStatus.DISPATCHED: NodeTaskStatus.DISPATCHED,
    DeliveryStatus.ACKED: NodeTaskStatus.ACKED,
    DeliveryStatus.RETRY_WAIT: NodeTaskStatus.RETRY_WAIT,
    DeliveryStatus.EXPIRED: NodeTaskStatus.EXPIRED,
    DeliveryStatus.DEAD_LETTER: NodeTaskStatus.DEAD_LETTER,
    DeliveryStatus.CANCELLED: NodeTaskStatus.CANCELLED,
}


_SUCCESS_ACTION_STATUSES = {"succeeded", "skipped", "dry_run"}
_FAILURE_ACTION_STATUSES = {"failed", "denied"}
_ACKLIKE_ACTION_STATUSES = {"accepted"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _payload_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _string_candidates(payload: Mapping[str, Any], *names: str) -> tuple[str, ...]:
    values: list[str] = []
    for name in names:
        value = payload.get(name)
        if isinstance(value, str) and value:
            values.append(value)
    return tuple(values)


@dataclass(frozen=True)
class NodeTaskEvent:
    """Append-only node task reconciliation event."""

    status: NodeTaskStatus
    reason: str
    source: str
    created_at: datetime = field(default_factory=_now)
    envelope_id: str | None = None
    payload: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "reason": self.reason,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "envelope_id": self.envelope_id,
            "payload": dict(self.payload),
        }


@dataclass
class NodeTaskRecord:
    """Controller-side projection of a node action lifecycle."""

    delivery_id: str
    node_id: str
    action: str
    session_id: str | None = None
    plan_id: str | None = None
    execution_run_id: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    status: NodeTaskStatus = NodeTaskStatus.REGISTERED
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    acknowledged_at: datetime | None = None
    completed_at: datetime | None = None
    attempts: int = 0
    last_envelope_id: str | None = None
    result_payload: Mapping[str, Any] | None = None
    error_payload: Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    history: list[NodeTaskEvent] = field(default_factory=list)
    id: str = field(default_factory=lambda: f"ntask_{uuid.uuid4().hex[:20]}")

    @property
    def terminal(self) -> bool:
        return self.status in _TERMINAL_STATUSES

    @property
    def ok(self) -> bool:
        return self.status == NodeTaskStatus.SUCCEEDED

    def record(
        self,
        status: NodeTaskStatus,
        reason: str,
        *,
        source: str,
        envelope_id: str | None = None,
        payload: Mapping[str, Any] | None = None,
        now: datetime | None = None,
        force: bool = False,
    ) -> None:
        current = now or _now()
        if self.terminal and not force:
            self.history.append(
                NodeTaskEvent(
                    status=NodeTaskStatus.IGNORED,
                    reason=f"ignored after terminal status {self.status.value}: {reason}",
                    source=source,
                    created_at=current,
                    envelope_id=envelope_id,
                    payload=payload or {},
                )
            )
            self.updated_at = current
            return
        self.status = status
        self.updated_at = current
        if envelope_id:
            self.last_envelope_id = envelope_id
        self.history.append(
            NodeTaskEvent(
                status=status,
                reason=reason,
                source=source,
                created_at=current,
                envelope_id=envelope_id,
                payload=payload or {},
            )
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "delivery_id": self.delivery_id,
            "node_id": self.node_id,
            "session_id": self.session_id,
            "action": self.action,
            "plan_id": self.plan_id,
            "execution_run_id": self.execution_run_id,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "attempts": self.attempts,
            "last_envelope_id": self.last_envelope_id,
            "result_payload": None if self.result_payload is None else dict(self.result_payload),
            "error_payload": None if self.error_payload is None else dict(self.error_payload),
            "metadata": dict(self.metadata),
            "history": [event.as_dict() for event in self.history],
        }


@dataclass(frozen=True)
class RunReconciliationSummary:
    """Aggregated node-task state for one execution run or orchestration plan."""

    key: str
    total: int
    pending: int
    acked: int
    succeeded: int
    failed: int
    expired: int
    dead_letters: int
    orphaned: int
    status: str
    task_ids: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "total": self.total,
            "pending": self.pending,
            "acked": self.acked,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "expired": self.expired,
            "dead_letters": self.dead_letters,
            "orphaned": self.orphaned,
            "status": self.status,
            "task_ids": list(self.task_ids),
        }


class ReconciliationJournal:
    """Append-only JSONL journal for reconciled node task records."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.touch(exist_ok=True)

    def append(self, record: NodeTaskRecord) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.as_dict(), ensure_ascii=False, separators=(",", ":")))
            handle.write("\n")

    def iter_records(self) -> tuple[dict[str, Any], ...]:
        rows: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if stripped:
                    rows.append(json.loads(stripped))
        return tuple(rows)

    def count(self) -> int:
        return len(self.iter_records())


class NodeResultReconciler:
    """Correlates secure gateway receipts and delivery state into node tasks."""

    def __init__(self, *, journal: ReconciliationJournal | None = None) -> None:
        self.journal = journal
        self._records: dict[str, NodeTaskRecord] = {}
        self._aliases: dict[str, str] = {}
        self.ignored_receipts: list[GatewayReceipt] = []

    def register_delivery(
        self,
        item: DeliveryItem,
        *,
        plan_id: str | None = None,
        execution_run_id: str | None = None,
        request_id: str | None = None,
        now: datetime | None = None,
    ) -> NodeTaskRecord:
        record = self._records.get(item.id)
        current = now or _now()
        metadata = dict(item.metadata)
        inferred_plan_id = plan_id or _str_or_none(metadata.get("plan_id"))
        inferred_run_id = execution_run_id or _str_or_none(metadata.get("execution_run_id"))
        inferred_request_id = request_id or _str_or_none(metadata.get("request_id"))
        if record is None:
            record = NodeTaskRecord(
                delivery_id=item.id,
                node_id=item.node_id,
                session_id=item.session_id,
                action=item.action,
                plan_id=inferred_plan_id,
                execution_run_id=inferred_run_id,
                request_id=inferred_request_id,
                correlation_id=item.id,
                attempts=item.attempts,
                last_envelope_id=item.last_envelope_id,
                metadata=metadata,
                created_at=current,
                updated_at=current,
            )
            self._records[item.id] = record
            record.record(NodeTaskStatus.REGISTERED, "delivery registered for reconciliation", source="delivery", now=current)
        else:
            record.plan_id = record.plan_id or inferred_plan_id
            record.execution_run_id = record.execution_run_id or inferred_run_id
            record.request_id = record.request_id or inferred_request_id
            record.attempts = item.attempts
            record.last_envelope_id = item.last_envelope_id or record.last_envelope_id
        self._index_record(record)
        return record

    def sync_delivery(self, item: DeliveryItem, *, now: datetime | None = None) -> NodeTaskRecord:
        record = self.register_delivery(item, now=now)
        current = now or _now()
        record.attempts = item.attempts
        record.last_envelope_id = item.last_envelope_id or record.last_envelope_id
        status = _DELIVERY_STATUS_MAP[item.status]
        if status == NodeTaskStatus.ACKED:
            record.acknowledged_at = item.acknowledged_at or current
        record.record(status, f"delivery status synced: {item.status.value}", source="delivery", envelope_id=item.last_envelope_id, now=current)
        self._index_record(record)
        self._append(record)
        return record

    def ingest_gateway_receipt(self, receipt: GatewayReceipt, *, now: datetime | None = None) -> NodeTaskRecord | None:
        current = now or _now()
        if receipt.status != GatewayMessageStatus.RECORDED:
            self.ignored_receipts.append(receipt)
            return None
        if receipt.direction != ChannelDirection.NODE_TO_CONTROLLER:
            self.ignored_receipts.append(receipt)
            return None
        if receipt.purpose not in {ChannelPurpose.ACK, ChannelPurpose.ACTION_RESULT, ChannelPurpose.ERROR}:
            self.ignored_receipts.append(receipt)
            return None

        payload = _payload_mapping(receipt.result)
        record = self._find_or_orphan(payload, receipt, now=current)

        if receipt.purpose == ChannelPurpose.ACK:
            record.acknowledged_at = current
            record.record(NodeTaskStatus.ACKED, "node ACK reconciled", source="gateway", envelope_id=receipt.envelope_id, payload=payload, now=current)
        elif receipt.purpose == ChannelPurpose.ACTION_RESULT:
            self._record_action_result(record, payload, receipt, now=current)
        elif receipt.purpose == ChannelPurpose.ERROR:
            record.error_payload = dict(payload)
            record.completed_at = current
            record.record(NodeTaskStatus.FAILED, "node error reconciled", source="gateway", envelope_id=receipt.envelope_id, payload=payload, now=current)

        self._index_record(record)
        self._append(record)
        return record

    def ingest_many(self, receipts: Sequence[GatewayReceipt], *, now: datetime | None = None) -> tuple[NodeTaskRecord, ...]:
        records: list[NodeTaskRecord] = []
        for receipt in receipts:
            record = self.ingest_gateway_receipt(receipt, now=now)
            if record is not None:
                records.append(record)
        return tuple(records)

    def get(self, delivery_id: str) -> NodeTaskRecord | None:
        return self._records.get(delivery_id)

    def require(self, delivery_id: str) -> NodeTaskRecord:
        record = self.get(delivery_id)
        if record is None:
            raise ReconciliationError("node task record not found")
        return record

    def all(self) -> tuple[NodeTaskRecord, ...]:
        return tuple(self._records.values())

    def summary_for_execution_run(self, execution_run_id: str) -> RunReconciliationSummary:
        tasks = [record for record in self._records.values() if record.execution_run_id == execution_run_id]
        return _summarize(execution_run_id, tasks)

    def summary_for_plan(self, plan_id: str) -> RunReconciliationSummary:
        tasks = [record for record in self._records.values() if record.plan_id == plan_id]
        return _summarize(plan_id, tasks)

    def as_dict(self) -> dict[str, Any]:
        return {
            "records": [record.as_dict() for record in self.all()],
            "ignored_receipts": [receipt.as_dict() for receipt in self.ignored_receipts],
        }

    def _record_action_result(self, record: NodeTaskRecord, payload: Mapping[str, Any], receipt: GatewayReceipt, *, now: datetime) -> None:
        record.result_payload = dict(payload)
        record.completed_at = now
        action_status = str(payload.get("status") or "").lower()
        if action_status in _SUCCESS_ACTION_STATUSES:
            status = NodeTaskStatus.SUCCEEDED
            reason = f"node action result reconciled: {action_status}"
        elif action_status in _FAILURE_ACTION_STATUSES:
            status = NodeTaskStatus.FAILED
            reason = f"node action result reconciled: {action_status}"
        elif action_status in _ACKLIKE_ACTION_STATUSES:
            status = NodeTaskStatus.ACKED
            reason = f"node action result is not terminal yet: {action_status}"
            record.completed_at = None
        else:
            status = NodeTaskStatus.FAILED
            reason = "node action result missing/unknown status"
        record.record(status, reason, source="gateway", envelope_id=receipt.envelope_id, payload=payload, now=now)

    def _find_or_orphan(self, payload: Mapping[str, Any], receipt: GatewayReceipt, *, now: datetime) -> NodeTaskRecord:
        candidates = self._candidate_ids(payload, receipt)
        for candidate in candidates:
            delivery_id = self._aliases.get(candidate, candidate)
            record = self._records.get(delivery_id)
            if record is not None:
                return record

        delivery_id = next((candidate for candidate in candidates if candidate.startswith("del_")), None)
        if delivery_id is None:
            delivery_id = f"orphan_{receipt.envelope_id}"
        record = NodeTaskRecord(
            delivery_id=delivery_id,
            node_id=receipt.node_id,
            action=str(payload.get("action") or "unknown"),
            session_id=_str_or_none(payload.get("session_id")),
            plan_id=_str_or_none(payload.get("plan_id")),
            execution_run_id=_str_or_none(payload.get("execution_run_id")),
            request_id=_str_or_none(payload.get("request_id")),
            correlation_id=_str_or_none(payload.get("correlation_id")),
            status=NodeTaskStatus.ORPHANED,
            last_envelope_id=receipt.envelope_id,
            result_payload=dict(payload) if receipt.purpose == ChannelPurpose.ACTION_RESULT else None,
            error_payload=dict(payload) if receipt.purpose == ChannelPurpose.ERROR else None,
            created_at=now,
            updated_at=now,
            metadata={"orphan": True, "receipt_id": receipt.id},
        )
        self._records[delivery_id] = record
        record.record(NodeTaskStatus.ORPHANED, "gateway receipt did not match known delivery", source="gateway", envelope_id=receipt.envelope_id, payload=payload, now=now, force=True)
        self._index_record(record)
        return record

    def _candidate_ids(self, payload: Mapping[str, Any], receipt: GatewayReceipt) -> tuple[str, ...]:
        values = list(
            _string_candidates(
                payload,
                "delivery_id",
                "correlation_id",
                "ack_for",
                "envelope_id",
                "request_id",
                "action_request_id",
            )
        )
        if receipt.verification is not None:
            values.append(receipt.verification.envelope_id)
        values.append(receipt.envelope_id)
        return tuple(dict.fromkeys(value for value in values if value))

    def _index_record(self, record: NodeTaskRecord) -> None:
        aliases = {
            record.delivery_id,
            record.id,
            record.request_id,
            record.correlation_id,
            record.last_envelope_id,
        }
        if record.result_payload:
            aliases.update(_string_candidates(record.result_payload, "request_id", "correlation_id", "delivery_id", "ack_for", "envelope_id"))
        if record.error_payload:
            aliases.update(_string_candidates(record.error_payload, "request_id", "correlation_id", "delivery_id", "ack_for", "envelope_id"))
        for alias in aliases:
            if isinstance(alias, str) and alias:
                self._aliases[alias] = record.delivery_id

    def _append(self, record: NodeTaskRecord) -> None:
        if self.journal is not None:
            self.journal.append(record)


def _summarize(key: str, tasks: Sequence[NodeTaskRecord]) -> RunReconciliationSummary:
    total = len(tasks)
    succeeded = sum(1 for task in tasks if task.status == NodeTaskStatus.SUCCEEDED)
    failed = sum(1 for task in tasks if task.status == NodeTaskStatus.FAILED)
    expired = sum(1 for task in tasks if task.status == NodeTaskStatus.EXPIRED)
    dead_letters = sum(1 for task in tasks if task.status == NodeTaskStatus.DEAD_LETTER)
    orphaned = sum(1 for task in tasks if task.status == NodeTaskStatus.ORPHANED)
    acked = sum(1 for task in tasks if task.status == NodeTaskStatus.ACKED)
    pending = sum(1 for task in tasks if task.status not in _TERMINAL_STATUSES and task.status != NodeTaskStatus.ACKED)
    if total == 0:
        status = "empty"
    elif failed or expired or dead_letters or orphaned:
        status = "failed"
    elif succeeded == total:
        status = "succeeded"
    elif pending:
        status = "waiting"
    else:
        status = "acked"
    return RunReconciliationSummary(
        key=key,
        total=total,
        pending=pending,
        acked=acked,
        succeeded=succeeded,
        failed=failed,
        expired=expired,
        dead_letters=dead_letters,
        orphaned=orphaned,
        status=status,
        task_ids=tuple(task.delivery_id for task in tasks),
    )


def _str_or_none(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
