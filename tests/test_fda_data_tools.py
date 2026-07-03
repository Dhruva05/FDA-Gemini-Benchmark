import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYZE_PATH = REPO_ROOT / "scripts" / "analyze_fda_data.py"
BUILDER_PATH = REPO_ROOT / "scripts" / "build_hard_fda_tasks.py"
FORBIDDEN_PUBLIC_FIELDS = {"answer", "references", "citations", "context", "gold_passages", "expected_terms"}
EXPECTED_TASKS = [
    "fda-hard-long-label-retrieval",
    "fda-hard-warning-citations",
    "fda-hard-numeric-dosage",
    "fda-hard-near-miss-refusal",
    "fda-hard-multisection-synthesis",
    "fda-hard-cross-label-comparison",
    "fda-hard-mixed-batch",
]


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_jsonl(path, rows):
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True))
            fh.write("\n")


def label_row(idx, drug_name, chunks):
    set_id = f"set-{idx:02d}"
    label_raw = "\n\n".join(f"||PASSAGE_{i:04d}||\n{chunk}" for i, chunk in enumerate(chunks))
    return {
        "set_id": set_id,
        "drug_name": drug_name,
        "drug_id": drug_name.lower().replace(" ", "_"),
        "label_raw": label_raw,
        "chunks": chunks,
    }


def qa_row(idx, label, task, question, answer, contexts, citations=None, references=None):
    return {
        "task": task,
        "source": "fixture",
        "set_id": label["set_id"],
        "question": question,
        "answer": answer,
        "references": references or [],
        "citations": citations or [],
        "drug_name": label["drug_name"],
        "question_type": task,
        "context": contexts,
        "qid": f"qid-{idx:03d}",
        "qfilter_category": task,
        "qfilter_relevance": "fixture",
    }


def context(chunk_index, section_label, section_title, text, has_answer=True):
    return {
        "doc_id": None,
        "section_title": section_title,
        "text": text,
        "doc_chunk_index": chunk_index,
        "section_label": section_label,
        "section_code": "fixture",
        "section_chunk_index": 0,
        "has_answer": has_answer,
    }


class FdaDataToolTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmpdir.name)

        self.labels = [
            label_row(
                1,
                "Alpha Relief",
                [
                    "Uses: temporarily relieves allergy symptoms.",
                    "Warnings: patients with kidney disease should ask a doctor before use.",
                    "Dosage: adults take one 10 mg tablet by mouth every 12 hours; do not exceed 20 mg daily.",
                    "Pregnancy: ask a health professional before use.",
                    "Drug interactions: avoid strong CYP3A inhibitors.",
                ],
            ),
            label_row(
                2,
                "Beta Capsules",
                [
                    "Indications: treatment of reflux symptoms.",
                    "Dosage and Administration: adults take 40 mg capsule orally once daily before meals.",
                    "Warnings and Precautions: serious hypersensitivity and acute kidney injury have been reported.",
                    "Adverse Reactions: headache, diarrhea, and abdominal pain.",
                    "Pregnancy: available data are insufficient to identify drug-associated risk.",
                ],
            ),
            label_row(
                3,
                "Gamma Tablets",
                [
                    "Indications: maintenance treatment.",
                    "Recommended dosage: pediatric patients take 5 mg orally twice daily.",
                    "Contraindications: known hypersensitivity to gamma tablets.",
                    "Warnings: monitor patients for hepatotoxicity and severe rash.",
                    "Lactation: advise patients that data are not available.",
                ],
            ),
            label_row(
                4,
                "Delta Injection",
                [
                    "Indications: acute hospital treatment.",
                    "Dosage: administer 2 mg intravenous injection every 6 hours.",
                    "Warnings: respiratory depression can occur and requires monitoring.",
                    "Renal impairment: reduce dose in severe renal impairment.",
                    "Hepatic impairment: no specific dose adjustment is stated.",
                ],
            ),
            label_row(
                5,
                "Epsilon Oral Solution",
                [
                    "Uses: symptomatic relief.",
                    "Dosage: take 15 mL orally every 8 hours; maximum daily dose is 45 mL.",
                    "Warnings: may cause sedation and impaired coordination.",
                    "Contraindications: concomitant monoamine oxidase inhibitor use.",
                    "Storage: store at room temperature.",
                ],
            ),
            label_row(
                6,
                "Zeta Cream",
                [
                    "Indications: topical treatment.",
                    "Dosage: apply a thin layer topically twice daily.",
                    "Warnings: avoid contact with eyes and mucous membranes.",
                    "Adverse Reactions: application site burning and pruritus.",
                    "Pregnancy: use only if clearly needed.",
                ],
            ),
        ]
        label_by_name = {row["drug_name"]: row for row in self.labels}
        self.qa_rows = [
            qa_row(1, label_by_name["Alpha Relief"], "factual", "What kidney warning is stated for Alpha Relief?", "Patients with kidney disease should ask a doctor before use.", [context(1, "5", "Warnings", self.labels[0]["chunks"][1])], ["5"], ["5 WARNINGS"]),
            qa_row(2, label_by_name["Alpha Relief"], "numeric", "What is the adult dosage for Alpha Relief?", "Adults take one 10 mg tablet by mouth every 12 hours; do not exceed 20 mg daily.", [context(2, "2", "Dosage", self.labels[0]["chunks"][2])], ["2"], ["2 DOSAGE"]),
            qa_row(3, label_by_name["Beta Capsules"], "factual", "What warnings are associated with Beta Capsules?", "Serious hypersensitivity and acute kidney injury have been reported.", [context(2, "5", "Warnings and Precautions", self.labels[1]["chunks"][2])], ["5"], ["5 WARNINGS AND PRECAUTIONS"]),
            qa_row(4, label_by_name["Beta Capsules"], "multihop", "What should be considered for Beta Capsules in pregnancy and kidney safety?", "Pregnancy data are insufficient, and acute kidney injury has been reported.", [context(2, "5", "Warnings and Precautions", self.labels[1]["chunks"][2]), context(4, "8.1", "Pregnancy", self.labels[1]["chunks"][4])], ["5", "8.1"], ["5 WARNINGS", "8.1 PREGNANCY"]),
            qa_row(5, label_by_name["Gamma Tablets"], "numeric", "What pediatric dosage is recommended for Gamma Tablets?", "Pediatric patients take 5 mg orally twice daily.", [context(1, "2", "Recommended dosage", self.labels[2]["chunks"][1])], ["2"], ["2 DOSAGE"]),
            qa_row(6, label_by_name["Gamma Tablets"], "multihop", "What risks should be communicated for Gamma Tablets?", "Monitor for hepatotoxicity and severe rash, and note that lactation data are not available.", [context(3, "5", "Warnings", self.labels[2]["chunks"][3]), context(4, "8.2", "Lactation", self.labels[2]["chunks"][4])], ["5", "8.2"], ["5 WARNINGS", "8.2 LACTATION"]),
            qa_row(7, label_by_name["Delta Injection"], "numeric", "How is Delta Injection administered?", "Administer 2 mg intravenous injection every 6 hours.", [context(1, "2", "Dosage", self.labels[3]["chunks"][1])], ["2"], ["2 DOSAGE"]),
            qa_row(8, label_by_name["Delta Injection"], "refusal", "Does Delta Injection provide a dose adjustment for thyroid dysfunction?", "Information not found!", [], [], []),
            qa_row(9, label_by_name["Epsilon Oral Solution"], "numeric", "What is the maximum daily dose for Epsilon Oral Solution?", "Take 15 mL orally every 8 hours; maximum daily dose is 45 mL.", [context(1, "2", "Dosage", self.labels[4]["chunks"][1])], ["2"], ["2 DOSAGE"]),
            qa_row(10, label_by_name["Epsilon Oral Solution"], "factual", "What safety warning is stated for Epsilon Oral Solution?", "May cause sedation and impaired coordination.", [context(2, "5", "Warnings", self.labels[4]["chunks"][2])], ["5"], ["5 WARNINGS"]),
            qa_row(11, label_by_name["Zeta Cream"], "numeric", "How often is Zeta Cream applied?", "Apply a thin layer topically twice daily.", [context(1, "2", "Dosage", self.labels[5]["chunks"][1])], ["2"], ["2 DOSAGE"]),
            qa_row(12, label_by_name["Zeta Cream"], "refusal", "Does Zeta Cream provide an oral dose for severe renal impairment?", "Information not found!", [], [], []),
        ]

        self.labels_path = self.tmp_path / "labels.jsonl"
        self.qa_path = self.tmp_path / "qa.jsonl"
        self.qa_toy_path = self.tmp_path / "qa_toy.jsonl"
        write_jsonl(self.labels_path, self.labels)
        write_jsonl(self.qa_path, self.qa_rows)
        write_jsonl(self.qa_toy_path, self.qa_rows[:3])

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_profile_data_computes_required_distributions_and_writes_reports(self):
        module = load_module(ANALYZE_PATH, "analyze_fda_data")
        output_dir = self.tmp_path / "analysis"

        profile = module.profile_data(self.labels_path, self.qa_path, self.qa_toy_path, output_dir)

        self.assertEqual(profile["label_count"], 6)
        self.assertEqual(profile["qa_files"]["qa.jsonl"]["row_count"], 12)
        self.assertEqual(profile["qa_files"]["qa_toy.jsonl"]["row_count"], 3)
        self.assertEqual(profile["task_distribution"]["numeric"], 5)
        self.assertIn("context_count_distribution", profile)
        self.assertIn("citation_count_distribution", profile)
        self.assertIn("answer_length_distribution", profile)
        self.assertGreaterEqual(len(profile["longest_labels"]), 3)
        self.assertTrue(profile["candidate_hard_examples"]["many_citations_or_context"])
        self.assertTrue((output_dir / "fda_data_profile.json").exists())
        markdown = (output_dir / "fda_data_profile.md").read_text(encoding="utf-8")
        self.assertIn("Top 20 Longest Labels", markdown)
        self.assertIn("Better Hard/Refusal Questions", markdown)

    def test_build_tasks_creates_public_hidden_split_without_leaking_gold_fields(self):
        module = load_module(BUILDER_PATH, "build_hard_fda_tasks")
        output_root = self.tmp_path / "samples"

        task_dirs = module.build_tasks(
            labels_path=self.labels_path,
            qa_path=self.qa_path,
            output_root=output_root,
            questions_per_task=2,
            overwrite=True,
        )

        self.assertEqual([path.name for path in task_dirs], EXPECTED_TASKS)
        for task_dir in task_dirs:
            for required_path in [
                task_dir / "instruction.md",
                task_dir / "task.toml",
                task_dir / "environment" / "Dockerfile",
                task_dir / "environment" / "data" / "public" / "labels.jsonl",
                task_dir / "environment" / "data" / "public" / "questions.jsonl",
                task_dir / "environment" / "data" / "public" / "README.md",
                task_dir / "data" / "public" / "labels.jsonl",
                task_dir / "data" / "public" / "questions.jsonl",
                task_dir / "data" / "public" / "README.md",
                task_dir / "tests" / "gold.jsonl",
                task_dir / "tests" / "verify.py",
                task_dir / "tests" / "test.sh",
                task_dir / "solution" / "solve.sh",
            ]:
                self.assertTrue(required_path.exists(), required_path)

            public_questions = [
                json.loads(line)
                for line in (task_dir / "data" / "public" / "questions.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertTrue(public_questions)
            for question in public_questions:
                self.assertTrue({"qid", "set_id", "drug_name", "task_type", "question", "required_output_fields"}.issubset(question))
                self.assertFalse(FORBIDDEN_PUBLIC_FIELDS.intersection(question), question)
            public_blob = json.dumps(public_questions, sort_keys=True)
            self.assertNotIn("Information not found!", public_blob)
            self.assertNotIn("maximum daily dose is 45 mL", public_blob)

    def test_generated_verifier_writes_zero_reward_for_missing_answers(self):
        module = load_module(BUILDER_PATH, "build_hard_fda_tasks")
        output_root = self.tmp_path / "samples"
        task_dir = module.build_tasks(
            labels_path=self.labels_path,
            qa_path=self.qa_path,
            output_root=output_root,
            questions_per_task=2,
            overwrite=True,
        )[0]
        logs_dir = self.tmp_path / "logs"
        env = os.environ.copy()
        env.update({
            "ANSWERS_PATH": str(self.tmp_path / "missing_answers.json"),
            "GOLD_PATH": str(task_dir / "tests" / "gold.jsonl"),
            "LABELS_PATH": str(task_dir / "data" / "public" / "labels.jsonl"),
            "LOGS_DIR": str(logs_dir),
        })

        result = subprocess.run(
            [sys.executable, str(task_dir / "tests" / "verify.py")],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((logs_dir / "reward.txt").read_text(encoding="utf-8").strip(), "0.0")
        diagnostics = json.loads((logs_dir / "reward.json").read_text(encoding="utf-8"))
        self.assertEqual(diagnostics["fractional_reward"], 0.0)
        self.assertFalse(diagnostics["passed"])
        self.assertIn("missing required output", diagnostics["schema_errors"][0])

    def test_generated_verifier_writes_fractional_reward_and_binary_pass_diagnostics(self):
        module = load_module(BUILDER_PATH, "build_hard_fda_tasks")
        output_root = self.tmp_path / "samples"
        task_dir = module.build_tasks(
            labels_path=self.labels_path,
            qa_path=self.qa_path,
            output_root=output_root,
            questions_per_task=2,
            overwrite=True,
        )[0]
        gold_rows = [
            json.loads(line)
            for line in (task_dir / "tests" / "gold.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        partial_answers = {
            "answers": [
                {
                    "qid": item["qid"],
                    "status": "ANSWERED",
                    "answer": "This is a generic partial answer.",
                    "citations": [],
                    "structured_fields": {},
                }
                for item in gold_rows
            ]
        }
        answers_path = self.tmp_path / "partial_answers.json"
        answers_path.write_text(json.dumps(partial_answers), encoding="utf-8")
        logs_dir = self.tmp_path / "fractional_logs"
        env = os.environ.copy()
        env.update({
            "ANSWERS_PATH": str(answers_path),
            "GOLD_PATH": str(task_dir / "tests" / "gold.jsonl"),
            "LABELS_PATH": str(task_dir / "data" / "public" / "labels.jsonl"),
            "LOGS_DIR": str(logs_dir),
            "TASK_NAME": task_dir.name,
        })

        result = subprocess.run(
            [sys.executable, str(task_dir / "tests" / "verify.py")],
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        diagnostics = json.loads((logs_dir / "reward.json").read_text(encoding="utf-8"))
        reward_txt = float((logs_dir / "reward.txt").read_text(encoding="utf-8").strip())
        self.assertGreater(diagnostics["fractional_reward"], 0.0)
        self.assertLess(diagnostics["fractional_reward"], 1.0)
        self.assertAlmostEqual(reward_txt, diagnostics["fractional_reward"])
        self.assertEqual(diagnostics["aggregate_score"], diagnostics["fractional_reward"])
        self.assertFalse(diagnostics["passed"])
        self.assertEqual(diagnostics["pass_threshold"], 0.85)
        self.assertEqual(diagnostics["num_questions"], len(gold_rows))
        self.assertEqual(diagnostics["num_answered"], len(gold_rows))
        self.assertEqual(diagnostics["num_missing"], 0)
        self.assertTrue(diagnostics["critical_errors"])
        self.assertTrue(diagnostics["question_scores"])
        first_score = diagnostics["question_scores"][0]
        self.assertIn("subscores", first_score)
        self.assertIn("citation_support", first_score["subscores"])
        self.assertIn("diagnostics", first_score)

    def test_summarize_fractional_rewards_reads_reward_json_and_txt(self):
        module = load_module(REPO_ROOT / "scripts" / "summarize_fractional_rewards.py", "summarize_fractional_rewards")
        input_dir = self.tmp_path / "jobs"
        output_dir = self.tmp_path / "analysis"
        verifier_dir = input_dir / "2026-07-02__10-00-00" / "fda-hard-numeric-dosage__abc" / "verifier"
        verifier_dir.mkdir(parents=True)
        (verifier_dir / "reward.txt").write_text("0.625\n", encoding="utf-8")
        (verifier_dir / "reward.json").write_text(
            json.dumps({
                "fractional_reward": 0.625,
                "aggregate_score": 0.625,
                "passed": False,
                "pass_threshold": 0.85,
                "critical_errors": ["wrong_numeric_dose"],
                "num_questions": 8,
            }),
            encoding="utf-8",
        )

        exit_code = module.main(["--input", str(input_dir), "--output-dir", str(output_dir)])

        self.assertEqual(exit_code, 0)
        csv_text = (output_dir / "fractional_reward_summary.csv").read_text(encoding="utf-8")
        md_text = (output_dir / "fractional_reward_summary.md").read_text(encoding="utf-8")
        self.assertIn("fda-hard-numeric-dosage", csv_text)
        self.assertIn("0.625", csv_text)
        self.assertIn("wrong_numeric_dose", csv_text)
        self.assertIn("Mean Fractional Reward", md_text)


if __name__ == "__main__":
    unittest.main()
