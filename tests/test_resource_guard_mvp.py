from __future__ import annotations

import unittest

from cyberhive_core.resource_guard import LocalResourceGuard, ReservationStatus, ResourceBudget, ResourceRequest, resource_request_from_payload


class ResourceGuardTests(unittest.TestCase):
    def test_dry_run_does_not_consume_capacity(self) -> None:
        guard = LocalResourceGuard(node_id="node.beta", budget=ResourceBudget(cpu_units=1, memory_mb=512, vram_mb=1024, io_weight=1, max_concurrent=1))
        first = guard.reserve(action="prewarm_model", request=ResourceRequest(cpu_units=0.5, memory_mb=128, vram_mb=512), dry_run=True)
        second = guard.reserve(action="prewarm_model", request=ResourceRequest(cpu_units=0.5, memory_mb=128, vram_mb=512), dry_run=True)
        self.assertEqual(first.status, ReservationStatus.DRY_RUN)
        self.assertEqual(second.status, ReservationStatus.DRY_RUN)
        self.assertEqual(len(guard.active_reservations()), 0)

    def test_live_reservation_blocks_over_capacity_until_release(self) -> None:
        guard = LocalResourceGuard(node_id="node.beta", budget=ResourceBudget(cpu_units=1, memory_mb=512, vram_mb=1024, io_weight=1, max_concurrent=1))
        granted = guard.reserve(action="health_check", request=ResourceRequest(cpu_units=0.2, memory_mb=128), dry_run=False)
        denied = guard.reserve(action="health_check", request=ResourceRequest(cpu_units=0.2, memory_mb=128), dry_run=False)
        self.assertEqual(granted.status, ReservationStatus.GRANTED)
        self.assertEqual(denied.status, ReservationStatus.DENIED)
        self.assertIn("concurrency", denied.reason)
        released = guard.release(granted.id)
        self.assertEqual(released.status, ReservationStatus.RELEASED)
        self.assertEqual(len(guard.active_reservations()), 0)

    def test_request_can_be_parsed_from_payload(self) -> None:
        request = resource_request_from_payload({"resource_request": {"cpu_units": 0.3, "memory_mb": 256, "vram_mb": 512, "io_weight": 0.2}})
        self.assertEqual(request.vram_mb, 512)


if __name__ == "__main__":
    unittest.main()
