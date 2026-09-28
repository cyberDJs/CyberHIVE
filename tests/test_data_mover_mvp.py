from pathlib import Path
import tempfile
import unittest

from cyberhive_core.data_mover import (
    DataMoveError,
    DataMover,
    DataMoveRequest,
    DataMoveStatus,
)


class DataMoverMvpTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root / "source" / "payload.txt"
        self.target = self.root / "target" / "payload.txt"
        self.source.parent.mkdir(parents=True)
        self.source.write_text("hello cyberhive\n", encoding="utf-8")
        self.mover = DataMover()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def request(self, **kwargs) -> DataMoveRequest:
        return DataMoveRequest(
            object_id=kwargs.get("object_id", "object.test"),
            source_path=kwargs.get("source_path", self.source),
            target_path=kwargs.get("target_path", self.target),
            reason=kwargs.get("reason", "unit test"),
            allow_overwrite=kwargs.get("allow_overwrite", False),
            expected_source_sha256=kwargs.get("expected_source_sha256"),
        )

    def test_dry_run_does_not_mutate(self) -> None:
        plan = self.mover.plan(self.request(), dry_run=True)
        self.assertEqual(plan.status, DataMoveStatus.PLANNED)
        self.assertTrue(plan.dry_run)
        self.assertFalse(self.target.exists())
        self.assertGreater(plan.source_size_bytes, 0)
        self.assertTrue(plan.source_sha256)

    def test_execute_copy_then_switch_keeps_source(self) -> None:
        plan = self.mover.plan(self.request(), dry_run=False)
        self.mover.execute(plan)
        self.assertEqual(plan.status, DataMoveStatus.EXECUTED)
        self.assertTrue(self.source.exists())
        self.assertTrue(self.target.exists())
        self.assertEqual(self.source.read_text(encoding="utf-8"), self.target.read_text(encoding="utf-8"))
        self.assertEqual(plan.source_sha256, plan.target_sha256)

    def test_refuses_existing_target_without_overwrite(self) -> None:
        self.target.parent.mkdir(parents=True)
        self.target.write_text("old target", encoding="utf-8")
        with self.assertRaises(DataMoveError):
            self.mover.plan(self.request(), dry_run=False)

    def test_overwrite_backup_and_rollback(self) -> None:
        self.target.parent.mkdir(parents=True)
        self.target.write_text("old target", encoding="utf-8")
        plan = self.mover.plan(self.request(allow_overwrite=True), dry_run=False)
        self.mover.execute(plan)
        self.assertEqual(self.target.read_text(encoding="utf-8"), "hello cyberhive\n")
        self.assertIsNotNone(plan.backup_path)
        self.mover.rollback(plan)
        self.assertEqual(plan.status, DataMoveStatus.ROLLED_BACK)
        self.assertEqual(self.target.read_text(encoding="utf-8"), "old target")


    def test_overwrite_failure_restores_original_target(self) -> None:
        class FinalChecksumFailingMover(DataMover):
            def __init__(self, target: Path) -> None:
                super().__init__()
                self.target = target.expanduser().resolve()

            def sha256(self, path: Path) -> str:
                value = super().sha256(path)
                if Path(path).expanduser().resolve() == self.target:
                    return "forced-final-checksum-mismatch"
                return value

        self.target.parent.mkdir(parents=True)
        self.target.write_text("old target", encoding="utf-8")
        mover = FinalChecksumFailingMover(self.target)
        plan = mover.plan(self.request(allow_overwrite=True), dry_run=False)

        with self.assertRaises(DataMoveError):
            mover.execute(plan)

        self.assertEqual(plan.status, DataMoveStatus.FAILED)
        self.assertEqual(self.target.read_text(encoding="utf-8"), "old target")
        self.assertTrue(any(item.startswith("backup_restored_on_failure:") for item in plan.audit))

    def test_expected_checksum_mismatch_fails(self) -> None:
        with self.assertRaises(DataMoveError):
            self.mover.plan(self.request(expected_source_sha256="bad-checksum"), dry_run=True)


if __name__ == "__main__":
    unittest.main()
