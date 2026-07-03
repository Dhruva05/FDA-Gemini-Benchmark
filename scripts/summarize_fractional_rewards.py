#!/usr/bin/env python3
"""Summarize fractional FDA verifier rewards from Harbor job/log folders."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CSV_COLUMNS = [
    "job",
    "task",
    "agent",
    "model",
    "fractional_reward",
    "passed",
    "aggregate_score",
    "num_questions",
    "critical_error_count",
    "main_failure_modes",
]


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def pass_at_k(n: int, c: int, k: int) -> float:
    if n <= 0 or k <= 0 or c <= 0:
        return 0.0
    if n - c < k or k > n:
        return 1.0
    return 1.0 - (math.comb(n - c, k) / math.comb(n, k))


def task_from_trial_dir(trial_dir: Path) -> str:
    name = trial_dir.name
    if "__" in name:
        return name.split("__", 1)[0]
    return name


def job_from_trial_dir(trial_dir: Path) -> str:
    return trial_dir.parent.name


def reward_from_text(path: Path) -> float | None:
    try:
        return as_float(path.read_text(encoding="utf-8"))
    except OSError:
        return None


def nested_get(data: Any, path: tuple[Any, ...]) -> Any:
    current = data
    for key in path:
        if isinstance(key, int):
            if not isinstance(current, list) or key >= len(current):
                return None
            current = current[key]
        else:
            if not isinstance(current, dict):
                return None
            current = current.get(key)
    return current


def metadata_from_trial(trial_dir: Path) -> tuple[str, str]:
    result = read_json(trial_dir / "result.json")
    config = read_json(trial_dir / "config.json")
    agent = (
        nested_get(result, ("agent_info", "name"))
        or nested_get(result, ("config", "agent", "name"))
        or nested_get(config, ("agent", "name"))
        or ""
    )
    model = (
        nested_get(result, ("agent_info", "model_info", "name"))
        or nested_get(result, ("config", "agent", "model_name"))
        or nested_get(config, ("agent", "model_name"))
        or ""
    )
    return str(agent or ""), str(model or "")


def failure_modes(data: dict[str, Any]) -> list[str]:
    modes = []
    for error in data.get("critical_errors") or []:
        modes.append(str(error))
    for item in data.get("question_scores") or data.get("per_question") or []:
        if not isinstance(item, dict):
            continue
        for error in item.get("critical_errors") or []:
            modes.append(str(error))
        for diagnostic in item.get("diagnostics") or []:
            text = str(diagnostic)
            if "citation" in text.lower():
                modes.append("citation_support")
            elif "refusal" in text.lower() or "not_found" in text.lower():
                modes.append("refusal_behavior")
            elif "structured" in text.lower() or "dose" in text.lower() or "unit" in text.lower():
                modes.append("structured_fields")
            elif "semantic" in text.lower() or "answer" in text.lower():
                modes.append("answer_content")
    return sorted(set(modes))


def row_from_reward(reward_json_path: Path) -> dict[str, Any]:
    verifier_dir = reward_json_path.parent
    trial_dir = verifier_dir.parent
    data = read_json(reward_json_path)
    if not isinstance(data, dict):
        data = {}
    text_reward = reward_from_text(verifier_dir / "reward.txt")
    fractional = (
        as_float(data.get("fractional_reward"))
        or as_float(data.get("aggregate_score"))
        or as_float(data.get("overall_fractional_score"))
        or text_reward
        or 0.0
    )
    aggregate = as_float(data.get("aggregate_score")) or fractional
    critical = data.get("critical_errors") or []
    passed_value = data.get("passed")
    if isinstance(passed_value, bool):
        passed = passed_value
    else:
        passed = aggregate >= float(data.get("pass_threshold", 0.85) or 0.85) and not critical
    agent, model = metadata_from_trial(trial_dir)
    modes = failure_modes(data)
    return {
        "job": job_from_trial_dir(trial_dir),
        "task": str(data.get("task_name") or task_from_trial_dir(trial_dir)),
        "agent": agent,
        "model": model,
        "fractional_reward": f"{fractional:.6g}",
        "passed": "1" if passed else "0",
        "aggregate_score": f"{aggregate:.6g}",
        "num_questions": str(data.get("num_questions", "")),
        "critical_error_count": str(len(critical)),
        "main_failure_modes": ";".join(modes),
    }


def collect_rows(input_dir: Path) -> list[dict[str, Any]]:
    rows = []
    for reward_json in sorted(input_dir.rglob("verifier/reward.json")):
        rows.append(row_from_reward(reward_json))
    seen_trial_dirs = {Path(row["job"]) / row["task"] for row in rows}
    for reward_txt in sorted(input_dir.rglob("verifier/reward.txt")):
        trial_dir = reward_txt.parent.parent
        key = Path(job_from_trial_dir(trial_dir)) / task_from_trial_dir(trial_dir)
        if key in seen_trial_dirs or (reward_txt.parent / "reward.json").exists():
            continue
        fractional = reward_from_text(reward_txt) or 0.0
        agent, model = metadata_from_trial(trial_dir)
        rows.append(
            {
                "job": job_from_trial_dir(trial_dir),
                "task": task_from_trial_dir(trial_dir),
                "agent": agent,
                "model": model,
                "fractional_reward": f"{fractional:.6g}",
                "passed": "1" if fractional >= 0.85 else "0",
                "aggregate_score": f"{fractional:.6g}",
                "num_questions": "",
                "critical_error_count": "",
                "main_failure_modes": "",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def render_markdown(rows: list[dict[str, Any]]) -> str:
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task[row["task"]].append(row)
    lines = [
        "# Fractional Reward Summary",
        "",
        f"- Trials: {len(rows)}",
        "",
        "## Mean Fractional Reward Per Task",
        "",
        "| Task | Trials | Mean Fractional Reward | Pass@1 | Pass@3 |",
        "|---|---:|---:|---:|---:|",
    ]
    for task in sorted(by_task):
        task_rows = by_task[task]
        rewards = [as_float(row["fractional_reward"]) or 0.0 for row in task_rows]
        passes = sum(1 for row in task_rows if row["passed"] == "1")
        lines.append(
            f"| {task} | {len(task_rows)} | {mean(rewards):.3f} | "
            f"{pass_at_k(len(task_rows), passes, 1):.3f} | {pass_at_k(len(task_rows), passes, 3):.3f} |"
        )
    mode_counts = Counter()
    for row in rows:
        for mode in row.get("main_failure_modes", "").split(";"):
            if mode:
                mode_counts[mode] += 1
    lines.extend(["", "## Failure Mode Distribution", ""])
    if mode_counts:
        for mode, count in mode_counts.most_common():
            lines.append(f"- {mode}: {count}")
    else:
        lines.append("- No failure modes recorded.")
    return "\n".join(lines).rstrip() + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("jobs"), help="Harbor jobs or logs directory.")
    parser.add_argument("--output-dir", type=Path, default=Path("analysis"), help="Directory for summary outputs.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = collect_rows(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "fractional_reward_summary.csv", rows)
    (args.output_dir / "fractional_reward_summary.md").write_text(render_markdown(rows), encoding="utf-8")
    print(f"Wrote {len(rows)} rows to {args.output_dir / 'fractional_reward_summary.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
