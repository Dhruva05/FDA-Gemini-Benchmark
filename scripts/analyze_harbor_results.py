#!/usr/bin/env python3
"""Analyze repeated Harbor task runs and generate report-ready metrics."""

import argparse
import csv
import json
import math
import re
import statistics
import struct
import sys
import zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


TASK_ORDER = [
    "fda-label-factual-qa",
    "fda-label-multihop-qa",
    "fda-label-refusal-qa",
    "fda-label-citation-retrieval",
    "fda-label-mixed-batch",
]
TASK_DISPLAY = {
    "fda-label-factual-qa": "Factual QA",
    "fda-label-multihop-qa": "Multihop QA",
    "fda-label-refusal-qa": "Refusal QA",
    "fda-label-citation-retrieval": "Citation Retrieval",
    "fda-label-mixed-batch": "Mixed Batch",
}
KNOWN_UI_REWARDS_BY_TASK = {
    "fda-label-factual-qa": [0.78, 0.77, 1.00],
    "fda-label-multihop-qa": [0.71, 0.80, 0.74],
    "fda-label-refusal-qa": [0.00, 0.84, 0.76],
    "fda-label-citation-retrieval": [0.85, 0.74, 0.73],
    "fda-label-mixed-batch": [0.79, 0.78, 0.81],
}
FAILURE_MODES = [
    "citation_grounding_failure",
    "exact_clinical_detail_failure",
    "multihop_synthesis_failure",
    "refusal_calibration_failure",
    "batch_consistency_failure",
    "schema_or_format_failure",
    "tool_or_file_handling_failure",
    "verifier_or_task_issue",
]
SUCCESS_THRESHOLD = 1.0 - 1e-9
TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}__\d{2}-\d{2}-\d{2}")

TRIAL_COLUMNS = [
    "task",
    "trial_index",
    "job_name",
    "job_folder",
    "timestamp",
    "reward",
    "binary_pass",
    "reward_source",
    "task_source",
]
TASK_COLUMNS = [
    "task",
    "n",
    "rewards",
    "mean_reward",
    "median_reward",
    "min_reward",
    "max_reward",
    "std_reward",
    "num_successes",
    "pass@1",
    "pass@2",
    "pass@3",
]
FAILURE_COLUMNS = [
    "task",
    "trial_index",
    "job_name",
    "reward",
    "binary_pass",
    "primary_failure_mode",
    "secondary_failure_mode",
    "notes",
]


def pass_at_k(n, c, k):
    """Standard pass@k estimator for n samples and c binary successes."""
    if n <= 0 or k <= 0:
        return 0.0
    if c <= 0:
        return 0.0
    if n - c < k:
        return 1.0
    if k > n:
        return 1.0
    return 1.0 - (math.comb(n - c, k) / math.comb(n, k))


def as_float(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            number = float(stripped)
        except ValueError:
            return None
    else:
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def nested_get(obj, path):
    current = obj
    for key in path:
        if isinstance(key, int):
            if not isinstance(current, list) or len(current) <= key:
                return None
            current = current[key]
        else:
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
    return current


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def reward_from_json_data(data):
    if not isinstance(data, dict):
        return None

    direct_paths = [
        ("verifier_result", "rewards", "reward"),
        ("verifier_result", "reward"),
        ("rewards", "reward"),
        ("reward",),
        ("overall_reward",),
        ("score",),
    ]
    for path in direct_paths:
        value = as_float(nested_get(data, path))
        if value is not None:
            return value

    evals = nested_get(data, ("stats", "evals"))
    if isinstance(evals, dict):
        for eval_data in evals.values():
            metrics = eval_data.get("metrics") if isinstance(eval_data, dict) else None
            if isinstance(metrics, list):
                for metric in metrics:
                    value = as_float(metric.get("mean") if isinstance(metric, dict) else None)
                    if value is not None:
                        return value
    return None


def task_name_from_value(value, require_known=False):
    if value is None:
        return None
    text = str(value)
    for task in TASK_ORDER:
        if task in text:
            return task
    if require_known:
        return None
    if "/" in text:
        text = text.rstrip("/").split("/")[-1]
    if "__" in text:
        text = text.split("__", 1)[0]
    if text:
        return text
    return None


def task_from_json_data(data):
    if not isinstance(data, dict):
        return None
    paths = [
        ("task_id", "path"),
        ("config", "task", "path"),
        ("task", "path"),
        ("tasks", 0, "path"),
        ("task_name",),
    ]
    for path in paths:
        task = task_name_from_value(nested_get(data, path))
        if task:
            return task
    return task_name_from_value(nested_get(data, ("trial_name",)), require_known=True)


def path_timestamp(path):
    for part in path.parts:
        match = TIMESTAMP_RE.search(part)
        if match:
            return match.group(0)
    return ""


def sort_key_for_trial(path):
    timestamp = path_timestamp(path)
    return (timestamp or path.name, str(path))


def has_nested_candidate(path):
    for child in path.iterdir() if path.exists() else []:
        if child.is_dir() and (
            (child / "result.json").exists()
            or (child / "verifier" / "reward.txt").exists()
            or (child / "verifier" / "reward.json").exists()
        ):
            return True
    return False


def discover_trial_dirs(input_dir):
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    candidates = set()

    for reward_path in input_dir.rglob("verifier/reward.txt"):
        candidates.add(reward_path.parent.parent)
    for reward_path in input_dir.rglob("verifier/reward.json"):
        candidates.add(reward_path.parent.parent)
    for result_path in input_dir.rglob("result.json"):
        result_dir = result_path.parent
        if has_nested_candidate(result_dir):
            continue
        candidates.add(result_dir)

    timestamp_dirs = []
    if TIMESTAMP_RE.search(input_dir.name):
        timestamp_dirs.append(input_dir)
    timestamp_dirs.extend(path for path in input_dir.rglob("*") if path.is_dir() and TIMESTAMP_RE.search(path.name))
    for job_dir in timestamp_dirs:
        children = [child for child in job_dir.iterdir() if child.is_dir()]
        if children:
            for child in children:
                candidates.add(child)
        else:
            candidates.add(job_dir)

    return sorted(candidates, key=sort_key_for_trial)


def read_reward(trial_dir):
    result_path = trial_dir / "result.json"
    if result_path.exists():
        data = read_json(result_path)
        value = reward_from_json_data(data)
        if value is not None:
            return value, str(result_path)

    reward_txt = trial_dir / "verifier" / "reward.txt"
    if reward_txt.exists():
        value = as_float(reward_txt.read_text(encoding="utf-8"))
        if value is not None:
            return value, str(reward_txt)

    reward_json = trial_dir / "verifier" / "reward.json"
    if reward_json.exists():
        data = read_json(reward_json)
        value = reward_from_json_data(data)
        if value is not None:
            return value, str(reward_json)

    parent_result = trial_dir.parent / "result.json"
    if parent_result.exists():
        data = read_json(parent_result)
        value = reward_from_json_data(data)
        if value is not None:
            return value, str(parent_result)

    raise ValueError(f"No reward value found for trial folder: {trial_dir}")


def known_ui_reward(task, trial_index):
    rewards = KNOWN_UI_REWARDS_BY_TASK.get(task)
    if not rewards or trial_index < 1 or trial_index > len(rewards):
        return None
    return rewards[trial_index - 1]


def read_task(trial_dir):
    for path in [
        trial_dir / "result.json",
        trial_dir / "config.json",
        trial_dir.parent / "config.json",
        trial_dir.parent / "result.json",
    ]:
        if path.exists():
            task = task_from_json_data(read_json(path))
            if task:
                return task, str(path)

    task = task_name_from_value(trial_dir.name, require_known=True)
    if task:
        return task, "trial_folder_name"

    task = task_name_from_value(trial_dir.parent.name, require_known=True)
    if task:
        return task, "job_folder_name"

    return None, "chronological_fallback"


def job_folder_name(trial_dir):
    timestamp = path_timestamp(trial_dir)
    if timestamp:
        return timestamp
    return trial_dir.parent.name if trial_dir.parent != trial_dir else trial_dir.name


def parse_trials(input_dir, fallback_trials_per_task=3):
    trial_dirs = discover_trial_dirs(input_dir)
    rows = []
    per_task_counts = defaultdict(int)
    for index, trial_dir in enumerate(trial_dirs):
        task, task_source = read_task(trial_dir)
        if not task:
            task_group = (index // fallback_trials_per_task) % len(TASK_ORDER)
            task = TASK_ORDER[task_group]
            task_source = "chronological_fallback"
        per_task_counts[task] += 1
        trial_index = per_task_counts[task]
        try:
            reward, reward_source = read_reward(trial_dir)
        except ValueError:
            reward = known_ui_reward(task, trial_index)
            if reward is None:
                raise
            reward_source = "known_ui_reward_fallback"
        rows.append({
            "task": task,
            "trial_dir": trial_dir,
            "job_name": trial_dir.name,
            "job_folder": job_folder_name(trial_dir),
            "timestamp": path_timestamp(trial_dir),
            "trial_index": trial_index,
            "reward": reward,
            "binary_pass": int(reward >= SUCCESS_THRESHOLD),
            "reward_source": reward_source,
            "task_source": task_source,
        })
    return rows


def ordered_tasks(rows):
    seen = []
    for task in TASK_ORDER:
        if any(row["task"] == task for row in rows):
            seen.append(task)
    for row in rows:
        if row["task"] not in seen:
            seen.append(row["task"])
    return seen


def format_float(value):
    return f"{value:.6f}".rstrip("0").rstrip(".")


def compute_task_metrics(rows):
    metrics = []
    rows_by_task = defaultdict(list)
    for row in rows:
        rows_by_task[row["task"]].append(row)

    for task in ordered_tasks(rows):
        task_rows = rows_by_task[task]
        rewards = [row["reward"] for row in task_rows]
        n = len(rewards)
        c = sum(1 for reward in rewards if reward >= SUCCESS_THRESHOLD)
        metrics.append({
            "task": task,
            "n": n,
            "rewards": rewards,
            "mean_reward": statistics.mean(rewards),
            "median_reward": statistics.median(rewards),
            "min_reward": min(rewards),
            "max_reward": max(rewards),
            "std_reward": statistics.pstdev(rewards) if n > 1 else 0.0,
            "num_successes": c,
            "pass@1": pass_at_k(n, c, 1),
            "pass@2": pass_at_k(n, c, 2),
            "pass@3": pass_at_k(n, c, 3),
        })
    return metrics


def compute_aggregate_metrics(task_metrics, rows, input_path, target_pass_at_3):
    aggregate_pass = {}
    for k in [1, 2, 3]:
        key = f"pass@{k}"
        aggregate_pass[key] = statistics.mean(metric[key] for metric in task_metrics) if task_metrics else 0.0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(input_path),
        "total_trials": len(rows),
        "num_tasks": len(task_metrics),
        "success_threshold": SUCCESS_THRESHOLD,
        "target_pass_at_3": target_pass_at_3,
        "meets_pass_at_3_target": aggregate_pass["pass@3"] < target_pass_at_3,
        "aggregate_pass_at_k": aggregate_pass,
        "tasks": task_metrics,
    }


def write_trial_results(path, rows):
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=TRIAL_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "task": row["task"],
                "trial_index": row["trial_index"],
                "job_name": row["job_name"],
                "job_folder": row["job_folder"],
                "timestamp": row["timestamp"],
                "reward": format_float(row["reward"]),
                "binary_pass": row["binary_pass"],
                "reward_source": row["reward_source"],
                "task_source": row["task_source"],
            })


def write_task_metrics(path, task_metrics):
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=TASK_COLUMNS)
        writer.writeheader()
        for metric in task_metrics:
            row = {}
            for column in TASK_COLUMNS:
                value = metric[column]
                if column == "rewards":
                    row[column] = json.dumps([round(reward, 6) for reward in value])
                elif isinstance(value, float):
                    row[column] = format_float(value)
                else:
                    row[column] = value
            writer.writerow(row)


def read_existing_annotations(path):
    if not path.exists():
        return {}
    existing = {}
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            key = (row.get("task", ""), row.get("trial_index", ""), row.get("job_name", ""))
            existing[key] = row
    return existing


def write_failure_annotations(path, rows):
    existing = read_existing_annotations(path)
    merged = []
    for row in rows:
        base = {
            "task": row["task"],
            "trial_index": str(row["trial_index"]),
            "job_name": row["job_name"],
            "reward": format_float(row["reward"]),
            "binary_pass": str(row["binary_pass"]),
            "primary_failure_mode": "",
            "secondary_failure_mode": "",
            "notes": "",
        }
        key = (base["task"], base["trial_index"], base["job_name"])
        if key in existing:
            for column in ["primary_failure_mode", "secondary_failure_mode", "notes"]:
                base[column] = existing[key].get(column, "")
        merged.append(base)

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FAILURE_COLUMNS)
        writer.writeheader()
        writer.writerows(merged)
    return merged


def validate_failure_annotations(rows):
    allowed = set(FAILURE_MODES)
    for row in rows:
        for column in ["primary_failure_mode", "secondary_failure_mode"]:
            mode = row.get(column, "").strip()
            if mode and mode not in allowed:
                raise ValueError(
                    f"Invalid {column} '{mode}' for {row.get('task')} trial "
                    f"{row.get('trial_index')}. Allowed modes: {', '.join(FAILURE_MODES)}"
                )


def annotations_have_modes(rows):
    for row in rows:
        if row.get("primary_failure_mode", "").strip() or row.get("secondary_failure_mode", "").strip():
            return True
    return False


def write_json(path, data):
    with path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def percent(value):
    return f"{value * 100:.1f}%"


def task_label(task):
    return TASK_DISPLAY.get(task, task.replace("fda-label-", "").replace("-", " ").title())


def short_task_label(task):
    return {
        "fda-label-factual-qa": "Factual",
        "fda-label-multihop-qa": "Multihop",
        "fda-label-refusal-qa": "Refusal",
        "fda-label-citation-retrieval": "Citation",
        "fda-label-mixed-batch": "Mixed",
    }.get(task, task_label(task))


def write_difficulty_profile(path, task_metrics, aggregate):
    sorted_tasks = sorted(task_metrics, key=lambda metric: metric["mean_reward"])
    hardest = sorted_tasks[0] if sorted_tasks else None
    easiest = sorted_tasks[-1] if sorted_tasks else None
    pass1 = aggregate["aggregate_pass_at_k"]["pass@1"]
    pass3 = aggregate["aggregate_pass_at_k"]["pass@3"]
    target = aggregate["target_pass_at_3"]
    target_sentence = (
        f"The task set meets the take-home target because aggregate pass@3 is below {percent(target)}."
        if aggregate["meets_pass_at_3_target"]
        else f"The task set does not meet the take-home target because aggregate pass@3 is not below {percent(target)}."
    )

    lines = [
        "# Difficulty Profile",
        "",
        "This analysis reports both fractional reward and binary pass@k because they answer different questions. Fractional reward captures partial progress on the deterministic verifier, such as correct schema, label selection, section selection, answer content, or grounded evidence even when the full task is not solved. Binary pass@k is stricter: a trial only counts as a pass when reward is effectively 1.0, so it measures whether repeated attempts produce fully correct task completions.",
        "",
        f"Across {aggregate['num_tasks']} tasks and {aggregate['total_trials']} trials, aggregate pass@1 is {percent(pass1)} and aggregate pass@3 is {percent(pass3)}. Aggregate pass@k is computed as the mean of the per-task pass@k estimates, so each task contributes equally regardless of the number of available trials.",
        "",
        target_sentence,
        "",
        "The difficulty curve sorts tasks by mean fractional reward from lowest to highest. Tasks on the left are the hardest under the fractional verifier, while tasks on the right are easier or at least more consistently partially solved. This curve should be read together with pass@k: a task can have a respectable mean reward while still having low binary pass rates if the model repeatedly earns partial credit without reaching a fully correct answer.",
    ]

    if hardest and easiest:
        lines.extend([
            "",
            f"In this run set, the lowest mean fractional reward is {task_label(hardest['task'])} at {percent(hardest['mean_reward'])}, and the highest mean fractional reward is {task_label(easiest['task'])} at {percent(easiest['mean_reward'])}.",
        ])

    lines.extend([
        "",
        "Failure-mode annotations should be discussed in the failure analysis section after filling `report/metrics/failure_annotations.csv`. Use `primary_failure_mode` for the dominant cause, `secondary_failure_mode` for an important contributing cause, and `notes` for concise examples from the trajectory or verifier diagnostics. Once annotations are present, the script generates `report/figures/failure_mode_counts.png` and `report/figures/failure_modes_by_task.png` for that discussion.",
        "",
    ])

    path.write_text("\n".join(lines), encoding="utf-8")


def make_dirs(output_dir):
    metrics_dir = output_dir / "metrics"
    figures_dir = output_dir / "figures"
    metrics_dir.mkdir(parents=True, exist_ok=True)
    figures_dir.mkdir(parents=True, exist_ok=True)
    return metrics_dir, figures_dir


def write_basic_png(path, width=900, height=560):
    raw = bytearray()
    for _ in range(height):
        raw.append(0)
        raw.extend(b"\xff\xff\xff" * width)

    def chunk(kind, data):
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    png = bytearray(b"\x89PNG\r\n\x1a\n")
    png.extend(chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)))
    png.extend(chunk(b"IDAT", zlib.compress(bytes(raw), 9)))
    png.extend(chunk(b"IEND", b""))
    path.write_bytes(bytes(png))


try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - exercised only on minimal Python installs
    Image = None
    ImageDraw = None
    ImageFont = None


COLORS = [
    "#2f6bff",
    "#2fb344",
    "#f59f00",
    "#d9480f",
    "#7048e8",
    "#1098ad",
    "#c2255c",
    "#495057",
]


def font(size=18, bold=False):
    if ImageFont is None:
        return None
    names = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size=size)
    return ImageFont.load_default(size=size)


def text_size(draw, text, text_font):
    box = draw.textbbox((0, 0), text, font=text_font)
    return box[2] - box[0], box[3] - box[1]


def draw_centered_text(draw, xy, text, text_font, fill="#212529"):
    width, height = text_size(draw, text, text_font)
    x, y = xy
    draw.text((x - width / 2, y - height / 2), text, fill=fill, font=text_font)


def y_pos(value, top, bottom):
    value = max(0.0, min(1.0, value))
    return bottom - value * (bottom - top)


def new_canvas(width=900, height=560):
    image = Image.new("RGB", (width, height), "white")
    return image, ImageDraw.Draw(image)


def draw_title(draw, title, width):
    draw_centered_text(draw, (width / 2, 28), title, font(24, bold=True), "#1f2933")


def draw_percent_axis(draw, left, top, right, bottom):
    axis_font = font(14)
    draw.line((left, bottom, right, bottom), fill="#343a40", width=2)
    draw.line((left, top, left, bottom), fill="#343a40", width=2)
    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = y_pos(tick, top, bottom)
        draw.line((left - 5, y, right, y), fill="#e9ecef", width=1)
        draw.text((left - 52, y - 8), percent(tick), fill="#495057", font=axis_font)


def draw_legend(draw, entries, x, y):
    legend_font = font(14)
    cursor = x
    for label, color in entries:
        draw.rectangle((cursor, y, cursor + 14, y + 14), fill=color)
        draw.text((cursor + 20, y - 1), label, fill="#343a40", font=legend_font)
        label_width, _ = text_size(draw, label, legend_font)
        cursor += label_width + 48


def save_image(image, path):
    image.save(path, format="PNG")


def plot_aggregate_pass(path, aggregate_pass, target_pass_at_3):
    if Image is None:
        write_basic_png(path)
        return
    width, height = 900, 560
    image, draw = new_canvas(width, height)
    left, top, right, bottom = 95, 80, 840, 455
    draw_title(draw, "Aggregate Pass@k", width)
    draw_percent_axis(draw, left, top, right, bottom)

    x_values = [1, 2, 3]
    points = []
    for index, k in enumerate(x_values):
        x = left + index * ((right - left) / 2)
        y = y_pos(aggregate_pass[f"pass@{k}"], top, bottom)
        points.append((x, y))
    draw.line(points, fill=COLORS[0], width=4)
    for x, y in points:
        draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=COLORS[0])
    for index, k in enumerate(x_values):
        x = left + index * ((right - left) / 2)
        draw_centered_text(draw, (x, bottom + 28), f"pass@{k}", font(16), "#343a40")
        draw_centered_text(draw, (x, y_pos(aggregate_pass[f"pass@{k}"], top, bottom) - 22), percent(aggregate_pass[f"pass@{k}"]), font(14), COLORS[0])

    target_y = y_pos(target_pass_at_3, top, bottom)
    dash = 10
    x = left
    while x < right:
        draw.line((x, target_y, min(x + dash, right), target_y), fill="#d9480f", width=2)
        x += dash * 2
    draw.text((right - 156, target_y - 24), "30% target line", fill="#d9480f", font=font(14, bold=True))
    draw.text((left, height - 56), "Binary success requires reward >= 1.0 - 1e-9. Aggregate values average per-task pass@k.", fill="#495057", font=font(14))
    save_image(image, path)


def plot_grouped_pass_rates(path, task_metrics):
    if Image is None:
        write_basic_png(path)
        return
    width, height = 1050, 600
    image, draw = new_canvas(width, height)
    left, top, right, bottom = 92, 96, 998, 480
    draw_title(draw, "Per-Task Binary Pass Rates", width)
    draw_percent_axis(draw, left, top, right, bottom)
    draw_legend(draw, [("pass@1", COLORS[0]), ("pass@2", COLORS[1]), ("pass@3", COLORS[2])], left + 5, 62)

    tasks = [metric["task"] for metric in task_metrics]
    group_width = (right - left) / max(len(tasks), 1)
    bar_width = min(42, group_width / 5)
    for i, metric in enumerate(task_metrics):
        center = left + group_width * (i + 0.5)
        for j, key in enumerate(["pass@1", "pass@2", "pass@3"]):
            value = metric[key]
            x0 = center + (j - 1) * (bar_width + 4) - bar_width / 2
            y0 = y_pos(value, top, bottom)
            draw.rectangle((x0, y0, x0 + bar_width, bottom), fill=COLORS[j])
        draw_centered_text(draw, (center, bottom + 30), short_task_label(metric["task"]), font(14), "#343a40")
    save_image(image, path)


def plot_mean_rewards(path, task_metrics):
    if Image is None:
        write_basic_png(path)
        return
    width, height = 1000, 580
    image, draw = new_canvas(width, height)
    left, top, right, bottom = 92, 80, 950, 455
    draw_title(draw, "Per-Task Mean Fractional Reward", width)
    draw_percent_axis(draw, left, top, right, bottom)

    group_width = (right - left) / max(len(task_metrics), 1)
    bar_width = min(76, group_width * 0.58)
    for i, metric in enumerate(task_metrics):
        center = left + group_width * (i + 0.5)
        value = metric["mean_reward"]
        y0 = y_pos(value, top, bottom)
        draw.rectangle((center - bar_width / 2, y0, center + bar_width / 2, bottom), fill=COLORS[i % len(COLORS)])
        draw_centered_text(draw, (center, y0 - 18), percent(value), font(13, bold=True), "#343a40")
        draw_centered_text(draw, (center, bottom + 30), short_task_label(metric["task"]), font(14), "#343a40")
    draw.text((left, height - 52), "Fractional reward preserves partial-credit signal from the deterministic verifier.", fill="#495057", font=font(14))
    save_image(image, path)


def plot_reward_distribution(path, rows, task_metrics):
    if Image is None:
        write_basic_png(path)
        return
    width, height = 1050, 620
    image, draw = new_canvas(width, height)
    left, top, right, bottom = 230, 82, 980, 505
    draw_title(draw, "Reward Distribution by Task", width)
    axis_font = font(14)
    draw.line((left, bottom, right, bottom), fill="#343a40", width=2)
    draw.line((left, top, left, bottom), fill="#343a40", width=2)
    for tick in [0.0, 0.25, 0.5, 0.75, 1.0]:
        x = left + tick * (right - left)
        draw.line((x, top, x, bottom + 5), fill="#e9ecef", width=1)
        draw_centered_text(draw, (x, bottom + 28), percent(tick), axis_font, "#495057")

    rows_by_task = defaultdict(list)
    for row in rows:
        rows_by_task[row["task"]].append(row)
    tasks = [metric["task"] for metric in task_metrics]
    band = (bottom - top) / max(len(tasks), 1)
    for i, task in enumerate(tasks):
        y = top + band * (i + 0.5)
        draw.text((28, y - 10), task_label(task), fill="#343a40", font=font(15, bold=True))
        draw.line((left, y, right, y), fill="#dee2e6", width=2)
        task_rows = rows_by_task[task]
        for j, row in enumerate(task_rows):
            x = left + row["reward"] * (right - left)
            jitter = (j - (len(task_rows) - 1) / 2) * 8
            color = COLORS[i % len(COLORS)]
            draw.ellipse((x - 6, y + jitter - 6, x + 6, y + jitter + 6), fill=color, outline="#212529")
    draw.text((left, height - 52), "Each dot is one Harbor trial. Dots at 100% are binary passes.", fill="#495057", font=font(14))
    save_image(image, path)


def plot_difficulty_curve(path, task_metrics):
    if Image is None:
        write_basic_png(path)
        return
    sorted_metrics = sorted(task_metrics, key=lambda metric: metric["mean_reward"])
    width, height = 1000, 580
    image, draw = new_canvas(width, height)
    left, top, right, bottom = 92, 80, 950, 455
    draw_title(draw, "Difficulty Curve Sorted by Mean Reward", width)
    draw_percent_axis(draw, left, top, right, bottom)
    group_width = (right - left) / max(len(sorted_metrics), 1)
    points = []
    for i, metric in enumerate(sorted_metrics):
        center = left + group_width * (i + 0.5)
        value = metric["mean_reward"]
        y = y_pos(value, top, bottom)
        points.append((center, y))
        draw.ellipse((center - 7, y - 7, center + 7, y + 7), fill=COLORS[i % len(COLORS)], outline="#212529")
        draw_centered_text(draw, (center, y - 22), percent(value), font(13, bold=True), "#343a40")
        draw_centered_text(draw, (center, bottom + 30), short_task_label(metric["task"]), font(14), "#343a40")
    if len(points) > 1:
        draw.line(points, fill="#495057", width=3)
    draw.text((left, height - 52), "Lower mean reward indicates higher observed difficulty under the fractional verifier.", fill="#495057", font=font(14))
    save_image(image, path)


def readable_mode(mode):
    return mode.replace("_failure", "").replace("_", " ").title()


def plot_failure_mode_counts(path, annotations):
    if Image is None:
        write_basic_png(path)
        return
    counts = Counter()
    for row in annotations:
        for column in ["primary_failure_mode", "secondary_failure_mode"]:
            mode = row.get(column, "").strip()
            if mode:
                counts[mode] += 1
    modes = [mode for mode, _ in counts.most_common()]
    width, height = 1050, max(520, 120 + len(modes) * 46)
    image, draw = new_canvas(width, height)
    left, top, right = 360, 80, 980
    draw_title(draw, "Failure Mode Counts", width)
    max_count = max(counts.values()) if counts else 1
    for i, mode in enumerate(modes):
        y = top + i * 46
        bar_w = (counts[mode] / max_count) * (right - left)
        draw.text((28, y + 7), readable_mode(mode), fill="#343a40", font=font(15, bold=True))
        draw.rectangle((left, y, left + bar_w, y + 28), fill=COLORS[i % len(COLORS)])
        draw.text((left + bar_w + 10, y + 5), str(counts[mode]), fill="#343a40", font=font(15, bold=True))
    save_image(image, path)


def plot_failure_modes_by_task(path, annotations, task_metrics):
    if Image is None:
        write_basic_png(path)
        return
    task_order = [metric["task"] for metric in task_metrics]
    mode_counts = {task: Counter() for task in task_order}
    present_modes = []
    for row in annotations:
        task = row.get("task", "")
        if task not in mode_counts:
            mode_counts[task] = Counter()
            task_order.append(task)
        for column in ["primary_failure_mode", "secondary_failure_mode"]:
            mode = row.get(column, "").strip()
            if mode:
                mode_counts[task][mode] += 1
                if mode not in present_modes:
                    present_modes.append(mode)

    width, height = 1180, max(620, 160 + len(task_order) * 58)
    image, draw = new_canvas(width, height)
    left, top, right = 260, 120, 1070
    draw_title(draw, "Failure Modes by Task", width)
    draw_legend(draw, [(readable_mode(mode), COLORS[i % len(COLORS)]) for i, mode in enumerate(present_modes[:6])], left, 72)
    max_total = max((sum(mode_counts[task].values()) for task in task_order), default=1) or 1
    for i, task in enumerate(task_order):
        y = top + i * 58
        draw.text((28, y + 8), task_label(task), fill="#343a40", font=font(15, bold=True))
        cursor = left
        for j, mode in enumerate(present_modes):
            count = mode_counts[task][mode]
            if not count:
                continue
            segment = (count / max_total) * (right - left)
            draw.rectangle((cursor, y, cursor + segment, y + 32), fill=COLORS[j % len(COLORS)])
            if segment > 22:
                draw_centered_text(draw, (cursor + segment / 2, y + 16), str(count), font(13, bold=True), "white")
            cursor += segment
        if cursor == left:
            draw.line((left, y + 16, right, y + 16), fill="#dee2e6", width=2)
    save_image(image, path)


def write_plots(figures_dir, rows, task_metrics, aggregate, annotations):
    plot_aggregate_pass(
        figures_dir / "aggregate_pass_at_k_curve.png",
        aggregate["aggregate_pass_at_k"],
        aggregate["target_pass_at_3"],
    )
    plot_grouped_pass_rates(figures_dir / "per_task_pass_rates.png", task_metrics)
    plot_mean_rewards(figures_dir / "per_task_mean_fractional_reward.png", task_metrics)
    plot_reward_distribution(figures_dir / "reward_distribution_by_task.png", rows, task_metrics)
    plot_difficulty_curve(figures_dir / "difficulty_curve_sorted.png", task_metrics)

    if annotations_have_modes(annotations):
        plot_failure_mode_counts(figures_dir / "failure_mode_counts.png", annotations)
        plot_failure_modes_by_task(figures_dir / "failure_modes_by_task.png", annotations, task_metrics)


def analyze(input_dir, output_dir, fallback_trials_per_task=3, target_pass_at_3=0.30):
    metrics_dir, figures_dir = make_dirs(output_dir)
    rows = parse_trials(input_dir, fallback_trials_per_task=fallback_trials_per_task)
    if not rows:
        raise ValueError(f"No Harbor trial folders found under {input_dir}")
    task_metrics = compute_task_metrics(rows)
    aggregate = compute_aggregate_metrics(task_metrics, rows, input_dir, target_pass_at_3)

    write_trial_results(metrics_dir / "trial_results.csv", rows)
    write_task_metrics(metrics_dir / "task_metrics.csv", task_metrics)
    write_json(metrics_dir / "aggregate_metrics.json", aggregate)
    annotations = write_failure_annotations(metrics_dir / "failure_annotations.csv", rows)
    validate_failure_annotations(annotations)
    write_difficulty_profile(output_dir / "difficulty_profile.md", task_metrics, aggregate)
    write_plots(figures_dir, rows, task_metrics, aggregate, annotations)

    return aggregate


def build_parser():
    parser = argparse.ArgumentParser(description="Analyze Harbor FDA-label run results.")
    parser.add_argument("--input", default=Path("logs"), type=Path, help="Harbor logs directory.")
    parser.add_argument("--output", default=Path("report"), type=Path, help="Output report directory.")
    parser.add_argument(
        "--fallback-trials-per-task",
        type=int,
        default=3,
        help="Trials per task when task metadata is absent and chronological fallback grouping is used.",
    )
    parser.add_argument(
        "--target-pass-at-3",
        type=float,
        default=0.30,
        help="Take-home target line for aggregate pass@3.",
    )
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        aggregate = analyze(
            args.input,
            args.output,
            fallback_trials_per_task=args.fallback_trials_per_task,
            target_pass_at_3=args.target_pass_at_3,
        )
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    pass1 = aggregate["aggregate_pass_at_k"]["pass@1"]
    pass3 = aggregate["aggregate_pass_at_k"]["pass@3"]
    print(
        f"Wrote Harbor analysis to {args.output} "
        f"(trials={aggregate['total_trials']}, tasks={aggregate['num_tasks']}, "
        f"aggregate pass@1={percent(pass1)}, pass@3={percent(pass3)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
