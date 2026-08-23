import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "collect_host_facts.py"
spec = importlib.util.spec_from_file_location("collect_host_facts", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


class CollectHostFactsTests(unittest.TestCase):
    def test_parse_nvidia_smi_csv(self):
        text = "0, NVIDIA GeForce RTX 3070, GPU-abc, 8192, 580.95, 8.6"
        parsed = module.parse_nvidia_smi_csv(text)
        self.assertEqual(parsed[0]["name"], "NVIDIA GeForce RTX 3070")
        self.assertEqual(parsed[0]["memory_total_mib"], 8192)
        self.assertEqual(parsed[0]["compute_capability"], "8.6")

    def test_read_meminfo(self):
        with tempfile.NamedTemporaryFile("w", delete=False) as tmp:
            tmp.write("MemTotal:       1024 kB\nMemAvailable:    512 kB\n")
            path = tmp.name
        try:
            result = module.read_meminfo(path)
            self.assertEqual(result["MemTotal"], 1024 * 1024)
            self.assertEqual(result["MemAvailable"], 512 * 1024)
        finally:
            Path(path).unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
