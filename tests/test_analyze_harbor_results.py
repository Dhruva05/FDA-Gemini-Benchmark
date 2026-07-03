import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "analyze_harbor_results.py"


def load_module():
    spec = importlib.util.spec_from_file_location("analyze_harbor_results", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_job(root, timestamp, trial_name, reward_txt=None, result_reward=None, task_path=None):
    job_dir = root / timestamp
    trial_dir = job_dir / trial_name
    verifier_dir = trial_dir / "verifier"
    verifier_dir.mkdir(parents=True)

    if reward_txt is not None:
        (verifier_dir / "reward.txt").write_text(str(reward_txt), encoding="utf-8")

    if result_reward is not None or task_path is not None:
        result = {
            "trial_name": trial_name,
            "verifier_result": {"rewards": {"reward": result_reward}},
        }
        if task_path is not None:
            result["task_id"] = {"path": task_path}
            result["config"] = {"task": {"path": task_path}}
        (trial_dir / "result.json").write_text(json.dumps(result), encoding="utf-8")

    return trial_dir


def write_empty_job(root, timestamp, trial_name):
    trial_dir = root / timestamp / trial_name
    trial_dir.mkdir(parents=True)
    return trial_dir


class HarborAnalysisTests(unittest.TestCase):
    def test_pass_at_k_estimator(self):
        module = load_module()

        self.assertAlmostEqual(module.pass_at_k(3, 1, 1), 1 / 3)
        self.assertAlmostEqual(module.pass_at_k(3, 1, 2), 2 / 3)
        self.assertAlmostEqual(module.pass_at_k(3, 1, 3), 1.0)
        self.assertAlmostEqual(module.pass_at_k(3, 0, 3), 0.0)

    def test_cli_outputs_metrics_with_chronological_fallback_grouping(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "jobs"
            output_dir = tmp_path / "report"

            write_job(
                input_dir,
                "2026-07-02__10-00-00",
                "trial-a",
                reward_txt=0.0,
                result_reward=1.0,
            )
            write_job(input_dir, "2026-07-02__10-01-00", "trial-b", reward_txt=0.5)
            write_job(input_dir, "2026-07-02__10-02-00", "trial-c", reward_txt=0.0)
            write_job(input_dir, "2026-07-02__10-03-00", "trial-d", reward_txt=0.75)

            exit_code = module.main(["--input", str(input_dir), "--output", str(output_dir)])

            self.assertEqual(exit_code, 0)
            self.assertTrue((output_dir / "metrics" / "trial_results.csv").exists())
            self.assertTrue((output_dir / "metrics" / "task_metrics.csv").exists())
            self.assertTrue((output_dir / "metrics" / "aggregate_metrics.json").exists())
            self.assertTrue((output_dir / "metrics" / "failure_annotations.csv").exists())
            self.assertTrue((output_dir / "difficulty_profile.md").exists())

            for figure_name in [
                "aggregate_pass_at_k_curve.png",
                "per_task_pass_rates.png",
                "per_task_mean_fractional_reward.png",
                "reward_distribution_by_task.png",
                "difficulty_curve_sorted.png",
            ]:
                png_path = output_dir / "figures" / figure_name
                self.assertTrue(png_path.exists(), figure_name)
                self.assertEqual(png_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

            with (output_dir / "metrics" / "trial_results.csv").open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual([row["task"] for row in rows], [
                "fda-label-factual-qa",
                "fda-label-factual-qa",
                "fda-label-factual-qa",
                "fda-label-multihop-qa",
            ])
            self.assertEqual(float(rows[0]["reward"]), 1.0)
            self.assertEqual(rows[0]["binary_pass"], "1")

            with (output_dir / "metrics" / "aggregate_metrics.json").open(encoding="utf-8") as fh:
                aggregate = json.load(fh)
            self.assertAlmostEqual(aggregate["aggregate_pass_at_k"]["pass@1"], 1 / 6)
            self.assertAlmostEqual(aggregate["aggregate_pass_at_k"]["pass@3"], 0.5)
            self.assertFalse(aggregate["meets_pass_at_3_target"])

    def test_task_metadata_overrides_fallback_grouping(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "jobs"
            output_dir = tmp_path / "report"

            write_job(
                input_dir,
                "2026-07-02__10-00-00",
                "trial-a",
                reward_txt=0.4,
                task_path="samples/fda-label-citation-retrieval",
            )

            module.main(["--input", str(input_dir), "--output", str(output_dir)])

            with (output_dir / "metrics" / "trial_results.csv").open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual(rows[0]["task"], "fda-label-citation-retrieval")

    def test_known_ui_rewards_are_used_when_reward_files_are_absent(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "jobs"
            output_dir = tmp_path / "report"

            write_empty_job(input_dir, "2026-07-02__10-00-00", "trial-a")
            write_empty_job(input_dir, "2026-07-02__10-01-00", "trial-b")
            write_empty_job(input_dir, "2026-07-02__10-02-00", "trial-c")
            write_empty_job(input_dir, "2026-07-02__10-03-00", "trial-d")

            exit_code = module.main(["--input", str(input_dir), "--output", str(output_dir)])

            self.assertEqual(exit_code, 0)
            with (output_dir / "metrics" / "trial_results.csv").open(newline="", encoding="utf-8") as fh:
                rows = list(csv.DictReader(fh))
            self.assertEqual([row["task"] for row in rows], [
                "fda-label-factual-qa",
                "fda-label-factual-qa",
                "fda-label-factual-qa",
                "fda-label-multihop-qa",
            ])
            self.assertEqual([row["reward"] for row in rows], ["0.78", "0.77", "1", "0.71"])
            self.assertTrue(all(row["reward_source"] == "known_ui_reward_fallback" for row in rows))

    def test_preserves_filled_failure_annotations_and_plots_modes(self):
        module = load_module()

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            input_dir = tmp_path / "jobs"
            output_dir = tmp_path / "report"

            write_job(
                input_dir,
                "2026-07-02__10-00-00",
                "trial-a",
                reward_txt=0.4,
                task_path="samples/fda-label-refusal-qa",
            )
            module.main(["--input", str(input_dir), "--output", str(output_dir)])

            annotations_path = output_dir / "metrics" / "failure_annotations.csv"
            with annotations_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(
                    fh,
                    fieldnames=[
                        "task",
                        "trial_index",
                        "job_name",
                        "reward",
                        "binary_pass",
                        "primary_failure_mode",
                        "secondary_failure_mode",
                        "notes",
                    ],
                )
                writer.writeheader()
                writer.writerow({
                    "task": "fda-label-refusal-qa",
                    "trial_index": "1",
                    "job_name": "trial-a",
                    "reward": "0.4",
                    "binary_pass": "0",
                    "primary_failure_mode": "refusal_calibration_failure",
                    "secondary_failure_mode": "",
                    "notes": "Accepted an unsupported claim.",
                })

            module.main(["--input", str(input_dir), "--output", str(output_dir)])

            self.assertTrue((output_dir / "figures" / "failure_mode_counts.png").exists())
            self.assertTrue((output_dir / "figures" / "failure_modes_by_task.png").exists())
            self.assertIn("Accepted an unsupported claim.", annotations_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
