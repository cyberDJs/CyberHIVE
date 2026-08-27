import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE_PATH = SCRIPTS / "benchmark_resources.py"
spec = importlib.util.spec_from_file_location("benchmark_resources", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class BenchmarkResourcesTests(unittest.TestCase):
    def test_meminfo_used_ram(self):
        parsed = module.parse_meminfo("MemTotal: 1048576 kB\nMemAvailable: 524288 kB\n")
        self.assertEqual(module.host_ram_used_mib(parsed), 512.0)

    def test_cpu_utilization(self):
        previous = module.parse_proc_stat("cpu  100 0 100 800 0 0 0 0 0 0\n")
        current = module.parse_proc_stat("cpu  150 0 150 900 0 0 0 0 0 0\n")
        self.assertAlmostEqual(module.cpu_utilization_pct(previous, current), 50.0)

    def test_parse_nvidia_sample(self):
        memory, util = module.parse_nvidia_smi_sample("4096, 73\n")
        self.assertEqual(memory, 4096.0)
        self.assertEqual(util, 73.0)


if __name__ == "__main__":
    unittest.main()
