import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "scripts" / "benchmark_openai.py"
spec = importlib.util.spec_from_file_location("benchmark_openai", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)


class BenchmarkOpenAITests(unittest.TestCase):
    def test_summary(self):
        runs = [
            module.RunResult(1000.0, 20, 10, 30, 20.0, "pass"),
            module.RunResult(1200.0, 24, 10, 34, 20.0, "pass"),
            module.RunResult(0.0, None, None, None, None, "fail", "boom"),
        ]
        summary = module.summarize(runs)
        self.assertEqual(summary["runs"], 3)
        self.assertEqual(summary["passed"], 2)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["elapsed_ms_median"], 1100.0)
        self.assertEqual(summary["tokens_per_second_median"], 20.0)

    def test_percentile_nearest(self):
        self.assertEqual(module.percentile_nearest([1, 2, 3, 4], 0.95), 4)


if __name__ == "__main__":
    unittest.main()
