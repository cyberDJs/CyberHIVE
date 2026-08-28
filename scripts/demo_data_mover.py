#!/usr/bin/env python3
"""Demo CyberHIVE Data Mover MVP."""

from pathlib import Path
import tempfile

from cyberhive_core.data_mover import DataMover, DataMoveRequest


def main() -> int:
    mover = DataMover()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "hdd" / "video.archive.raw"
        target = root / "nvme" / "video.archive.raw"
        source.parent.mkdir(parents=True)
        source.write_text("CyberHIVE archive payload\n" * 10, encoding="utf-8")

        request = DataMoveRequest(
            object_id="video.archive.raw-2026-08-01",
            source_path=source,
            target_path=target,
            reason="promote from HDD to NVMe for near-term processing",
        )

        dry = mover.plan(request, dry_run=True)
        print(f"dry-run plan: {dry.id}")
        for step in dry.steps:
            print(f"  - {step}")
        print(f"source_sha256: {dry.source_sha256[:16]}...")

        plan = mover.plan(request, dry_run=False)
        mover.execute(plan)
        print(f"executed: {plan.id} status={plan.status.value}")
        print(f"target: {plan.target_path}")
        print(f"source kept: {plan.source_path.exists()}")
        print(f"checksum ok: {plan.source_sha256 == plan.target_sha256}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
