#!/usr/bin/env python3
"""Validate CyberHIVE Data Mover MVP."""

from pathlib import Path
import tempfile

from cyberhive_core.data_mover import DataMover, DataMoveRequest, DataMoveStatus


def main() -> int:
    mover = DataMover()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "source" / "dataset.bin"
        target = root / "nvme" / "dataset.bin"
        source.parent.mkdir(parents=True)
        source.write_bytes(b"cyberhive-data-mover-validation" * 128)

        dry_plan = mover.plan(
            DataMoveRequest(
                object_id="dataset.validation",
                source_path=source,
                target_path=target,
                reason="validation dry-run",
            ),
            dry_run=True,
        )
        assert dry_plan.status == DataMoveStatus.PLANNED
        assert not target.exists()

        plan = mover.plan(
            DataMoveRequest(
                object_id="dataset.validation",
                source_path=source,
                target_path=target,
                reason="validation execute",
            ),
            dry_run=False,
        )
        mover.execute(plan)
        assert plan.status == DataMoveStatus.EXECUTED
        assert source.exists()
        assert target.exists()
        assert target.read_bytes() == source.read_bytes()
        assert plan.source_sha256 == plan.target_sha256

    print("OK: Data Mover MVP validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
