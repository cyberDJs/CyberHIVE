"""CyberHIVE Data Mover MVP.

Safe local filesystem data movement for the Adaptive Data Fabric.

The MVP intentionally uses copy-then-switch and keeps the source in place.
This is slower than direct rename/delete, but safer and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import hashlib
import os
import shutil
import uuid


class DataMoveError(RuntimeError):
    """Raised when a data move cannot be safely planned or executed."""


class DataMoveOperation(str, Enum):
    COPY_THEN_SWITCH = "copy_then_switch"


class DataMoveStatus(str, Enum):
    PLANNED = "planned"
    EXECUTED = "executed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass(frozen=True)
class DataMoveRequest:
    """Request to move or materialize an object at a target path."""

    object_id: str
    source_path: Path | str
    target_path: Path | str
    reason: str = ""
    allow_overwrite: bool = False
    expected_source_sha256: str | None = None


@dataclass
class DataMovePlan:
    """Auditable plan and result of a data move."""

    id: str
    object_id: str
    source_path: Path
    target_path: Path
    temp_path: Path
    backup_path: Path | None
    operation: DataMoveOperation = DataMoveOperation.COPY_THEN_SWITCH
    status: DataMoveStatus = DataMoveStatus.PLANNED
    dry_run: bool = True
    allow_overwrite: bool = False
    source_size_bytes: int = 0
    source_sha256: str = ""
    target_sha256: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    executed_at: datetime | None = None
    audit: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "object_id": self.object_id,
            "source_path": str(self.source_path),
            "target_path": str(self.target_path),
            "temp_path": str(self.temp_path),
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "operation": self.operation.value,
            "status": self.status.value,
            "dry_run": self.dry_run,
            "allow_overwrite": self.allow_overwrite,
            "source_size_bytes": self.source_size_bytes,
            "source_sha256": self.source_sha256,
            "target_sha256": self.target_sha256,
            "created_at": self.created_at.isoformat(),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "steps": list(self.steps),
            "audit": list(self.audit),
        }


class DataMover:
    """Safe local filesystem mover with dry-run and rollback support."""

    def __init__(self, chunk_size_bytes: int = 1024 * 1024) -> None:
        if chunk_size_bytes <= 0:
            raise ValueError("chunk_size_bytes must be positive")
        self.chunk_size_bytes = chunk_size_bytes

    def plan(self, request: DataMoveRequest, dry_run: bool = True) -> DataMovePlan:
        source = Path(request.source_path).expanduser().resolve()
        target = Path(request.target_path).expanduser().resolve()

        if not request.object_id:
            raise DataMoveError("object_id is required")
        if not source.exists():
            raise DataMoveError(f"source does not exist: {source}")
        if not source.is_file():
            raise DataMoveError(f"source is not a regular file: {source}")
        if target.exists() and not request.allow_overwrite:
            raise DataMoveError(f"target already exists and overwrite is disabled: {target}")

        target.parent.mkdir(parents=True, exist_ok=True) if not dry_run else None
        source_sha256 = self.sha256(source)

        if request.expected_source_sha256 and request.expected_source_sha256 != source_sha256:
            raise DataMoveError("source checksum does not match expected_source_sha256")

        move_id = f"dm_{uuid.uuid4().hex[:20]}"
        temp_path = target.with_name(f".{target.name}.{move_id}.tmp")
        backup_path = target.with_name(f".{target.name}.{move_id}.bak") if target.exists() else None
        stat = source.stat()

        steps = [
            "validate source file",
            "calculate source sha256",
            "copy source to temporary target",
            "verify temporary target sha256",
            "switch temporary target into final location",
            "keep source until cleanup policy approves deletion",
        ]
        if backup_path:
            steps.insert(4, "backup existing target before switch")

        audit = [
            f"planned:{datetime.now(timezone.utc).isoformat()}",
            f"reason:{request.reason or 'not specified'}",
            f"source:{source}",
            f"target:{target}",
            f"dry_run:{dry_run}",
        ]

        return DataMovePlan(
            id=move_id,
            object_id=request.object_id,
            source_path=source,
            target_path=target,
            temp_path=temp_path,
            backup_path=backup_path,
            dry_run=dry_run,
            allow_overwrite=request.allow_overwrite,
            source_size_bytes=stat.st_size,
            source_sha256=source_sha256,
            audit=audit,
            steps=steps,
        )

    def execute(self, plan: DataMovePlan) -> DataMovePlan:
        if plan.dry_run:
            raise DataMoveError("cannot execute a dry-run plan; create plan with dry_run=False")
        if plan.status != DataMoveStatus.PLANNED:
            raise DataMoveError(f"plan is not executable in status {plan.status.value}")
        if not plan.source_path.exists():
            raise DataMoveError(f"source disappeared before execution: {plan.source_path}")
        if plan.target_path.exists() and not plan.allow_overwrite:
            raise DataMoveError(f"target exists and overwrite is disabled: {plan.target_path}")

        backup_created = False
        try:
            plan.target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(plan.source_path, plan.temp_path)
            copied_sha256 = self.sha256(plan.temp_path)
            if copied_sha256 != plan.source_sha256:
                raise DataMoveError("temporary copy checksum mismatch")

            if plan.target_path.exists():
                if not plan.backup_path:
                    raise DataMoveError("target exists but backup path is missing")
                os.replace(plan.target_path, plan.backup_path)
                backup_created = True
                plan.audit.append(f"backup_created:{plan.backup_path}")

            os.replace(plan.temp_path, plan.target_path)
            plan.target_sha256 = self.sha256(plan.target_path)
            if plan.target_sha256 != plan.source_sha256:
                raise DataMoveError("final target checksum mismatch")

            plan.status = DataMoveStatus.EXECUTED
            plan.executed_at = datetime.now(timezone.utc)
            plan.audit.append(f"executed:{plan.executed_at.isoformat()}")
            plan.audit.append("source_kept:true")
            return plan
        except Exception as exc:  # noqa: BLE001 - convert to auditable plan failure
            plan.status = DataMoveStatus.FAILED
            plan.audit.append(f"failed:{type(exc).__name__}:{exc}")
            if plan.temp_path.exists():
                try:
                    plan.temp_path.unlink()
                    plan.audit.append("temp_removed:true")
                except OSError as cleanup_exc:
                    plan.audit.append(f"temp_cleanup_failed:{cleanup_exc}")
            if backup_created and plan.backup_path and plan.backup_path.exists():
                try:
                    if plan.target_path.exists():
                        plan.target_path.unlink()
                    os.replace(plan.backup_path, plan.target_path)
                    plan.audit.append(f"backup_restored_on_failure:{plan.target_path}")
                except OSError as restore_exc:
                    plan.audit.append(f"backup_restore_failed:{restore_exc}")
            if isinstance(exc, DataMoveError):
                raise
            raise DataMoveError(str(exc)) from exc

    def rollback(self, plan: DataMovePlan) -> DataMovePlan:
        if plan.status != DataMoveStatus.EXECUTED:
            raise DataMoveError(f"can rollback only executed plans, got {plan.status.value}")

        if plan.backup_path and plan.backup_path.exists():
            if plan.target_path.exists():
                plan.target_path.unlink()
            os.replace(plan.backup_path, plan.target_path)
            plan.audit.append(f"rollback_restored_backup:{plan.target_path}")
        else:
            if plan.target_path.exists() and self.sha256(plan.target_path) == plan.source_sha256:
                plan.target_path.unlink()
                plan.audit.append(f"rollback_removed_new_target:{plan.target_path}")
            else:
                raise DataMoveError("rollback cannot safely identify target to remove")

        plan.status = DataMoveStatus.ROLLED_BACK
        plan.audit.append(f"rolled_back:{datetime.now(timezone.utc).isoformat()}")
        return plan

    def sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(self.chunk_size_bytes)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest()
