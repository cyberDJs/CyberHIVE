import argparse
import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
MODULE_PATH = SCRIPTS / "benchmark_openai.py"
spec = importlib.util.spec_from_file_location("benchmark_openai", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)


class BenchmarkOpenAITests(unittest.TestCase):
    def test_sse_parser_and_usage(self):
        lines = [
            b": keepalive\n",
            b"data: {\"choices\":[{\"delta\":{\"content\":\"Hi\"}}]}\n",
            b"\n",
            b"data: {\"choices\":[],\"usage\":{\"prompt_tokens\":10,\"completion_tokens\":2,\"total_tokens\":12}}\n",
            b"\n",
            b"data: [DONE]\n",
            b"\n",
        ]
        events = list(module.iter_sse_json(lines))
        self.assertEqual(module.extract_delta_text(events[0]), "Hi")
        self.assertEqual(module.extract_usage(events[1]), (10, 2, 12))

    def test_calculate_throughput_separates_ttft_and_generation(self):
        prompt_tps, generation_tps = module.calculate_throughput(100, 50, 500.0, 2500.0)
        self.assertEqual(prompt_tps, 200.0)
        self.assertEqual(generation_tps, 25.0)

    def test_should_continue_honors_minimum_runs_and_duration(self):
        self.assertTrue(module.should_continue(0.0, 1.0, 2, 3, 0))
        self.assertFalse(module.should_continue(0.0, 1.0, 3, 3, 0))
        self.assertTrue(module.should_continue(0.0, 9.0, 3, 3, 10))
        self.assertFalse(module.should_continue(0.0, 10.0, 3, 3, 10))

    def test_raw_record_contains_issue_9_required_fields(self):
        resources = module.ResourceSummary(
            samples=4,
            peak_vram_mib=4096.0,
            peak_ram_mib=8192.0,
            peak_gpu_utilization_pct=80.0,
            peak_cpu_utilization_pct=50.0,
            peak_runtime_rss_mib=2048.0,
            sampler_errors=[],
        )
        run = module.RunResult(
            run_index=1,
            timestamp_utc="2026-08-27T00:00:00Z",
            elapsed_ms=2000.0,
            ttft_ms=500.0,
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            prompt_tokens_per_second=200.0,
            generation_tokens_per_second=33.3,
            generated_characters=200,
            result="pass",
            notes="",
            error=None,
            resources=resources,
        )
        args = argparse.Namespace(
            runtime="llama.cpp",
            runtime_version="test",
            model="model",
            model_revision="rev",
            artifact_sha256="a" * 64,
            quantization="Q4_K_M",
            context_length=4096,
        )
        host = {
            "hostname": "node",
            "os": {"system": "Linux", "release": "6.8.0"},
            "nvidia": {
                "cuda_version": "12.8",
                "gpus": [{"name": "NVIDIA GeForce RTX 3070", "driver_version": "580.95"}],
            },
        }
        record = module.build_raw_record(run, host, args)
        required = {
            "schema_version",
            "timestamp_utc",
            "host_id",
            "os",
            "kernel",
            "gpu",
            "driver",
            "cuda",
            "runtime",
            "runtime_version",
            "model_id",
            "model_revision",
            "artifact_sha256",
            "quantization",
            "context_length",
            "ttft_ms",
            "prompt_tokens_per_second",
            "generation_tokens_per_second",
            "peak_vram_mib",
            "peak_ram_mib",
            "result",
            "notes",
        }
        self.assertTrue(required.issubset(record.keys()))

    def test_validate_args_rejects_short_or_unpinned_run(self):
        args = argparse.Namespace(
            runs=2,
            warmup=1,
            duration=0,
            max_tokens=128,
            context_length=4096,
            sample_interval=0.5,
            artifact_sha256="a" * 64,
            runtime_pid=None,
        )
        with self.assertRaises(ValueError):
            module.validate_args(args)


if __name__ == "__main__":
    unittest.main()
