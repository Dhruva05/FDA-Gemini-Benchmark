#!/usr/bin/env python3
"""Analyze Gemini 3.5 Flash Harbor runs for the hard FDA question set.

The script is intentionally filesystem-driven: it scans jobs/ and logs/ for
Harbor artifacts, prefers verifier reward files over result.json, filters to
terminus-2 + gemini/gemini-3.5-flash, and writes report-ready tables/figures.
"""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = Path(tempfile.gettempdir()) / "fda_hard_question_set_matplotlib_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(CACHE_DIR / "matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(CACHE_DIR))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPORT_DIR = PROJECT_ROOT / "report"
FIGURE_DIR = REPORT_DIR / "figures"
SEARCH_ROOTS = [PROJECT_ROOT / "jobs", PROJECT_ROOT / "logs"]

MODEL_UNDER_TEST = "gemini-3.5-flash"
AGENT_UNDER_TEST = "terminus-2"
PASS_THRESHOLD = 1.0
HEADROOM_THRESHOLD = 0.30

TASK_RE = re.compile(r"(fda-hard-[A-Za-z0-9-]+)")
TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}__\d{2}-\d{2}-\d{2}")

TASK_DISPLAY = {
    "fda-hard-long-label-retrieval": "Long label retrieval",
    "fda-hard-warning-citations": "Warning citations",
    "fda-hard-numeric-dosage": "Numeric dosage",
    "fda-hard-near-miss-refusal": "Near-miss refusal",
    "fda-hard-multisection-synthesis": "Multisection synthesis",
    "fda-hard-cross-label-comparison": "Cross-label comparison",
    "fda-hard-mixed-batch": "Mixed batch",
}

TOKENS = {
    "surface": "#FCFCFD",
    "panel": "#FFFFFF",
    "ink": "#1F2430",
    "muted": "#6F768A",
    "grid": "#E6E8F0",
    "axis": "#D7DBE7",
}
BLUE = {"base": "#A3BEFA", "mid": "#5477C4", "dark": "#2E4780", "xlight": "#EAF1FE"}
GOLD = {"base": "#FFE15B", "mid": "#B8A037", "dark": "#736422", "xlight": "#FFF4C2"}
ORANGE = {"base": "#F0986E", "mid": "#CC6F47", "dark": "#804126", "xlight": "#FFEDDE"}
OLIVE = {"base": "#A3D576", "mid": "#71B436", "dark": "#386411", "xlight": "#D8ECBD"}
PINK = {"base": "#F390CA", "mid": "#BD569B", "dark": "#8A3A6F", "xlight": "#FCDAD6"}


@dataclass(frozen=True)
class Trial:
    trial_dir: Path
    job_timestamp: str
    run_id: str
    task_name: str
    agent: str
    model: str
    reward: float
    reward_source: str
    passed: bool
    explicit_pass: bool
    started_at: str
    finished_at: str
    n_questions: int | None
    schema_error_count: int
    critical_errors: str
    failure_categories: tuple[str, ...]


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
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


def infer_timestamp(path: Path) -> str:
    for part in path.parts:
        match = TIMESTAMP_RE.fullmatch(part)
        if match:
            return part
    for part in path.parts:
        match = TIMESTAMP_RE.search(part)
        if match:
            return match.group(0)
    return ""


def normalize_task_name(*values: Any) -> str | None:
    for value in values:
        if value is None:
            continue
        match = TASK_RE.search(str(value))
        if match:
            return match.group(1)
    return None


def reward_from_result_json(data: Any) -> float | None:
    if not isinstance(data, dict):
        return None
    for path in [
        ("verifier_result", "rewards", "reward"),
        ("verifier_result", "reward"),
        ("reward",),
        ("overall_reward",),
        ("score",),
    ]:
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


def reward_from_reward_json(data: Any) -> float | None:
    if not isinstance(data, dict):
        return None
    for key in [
        "reward",
        "fractional_reward",
        "aggregate_score",
        "overall_fractional_score",
        "overall_reward",
        "score",
    ]:
        value = as_float(data.get(key))
        if value is not None:
            return value
    return None


def reward_from_text(path: Path) -> float | None:
    try:
        return as_float(path.read_text(encoding="utf-8").strip())
    except OSError:
        return None


def bool_true(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "pass", "passed"}
    if isinstance(value, (int, float)):
        return value == 1
    return False


def explicit_pass_from_reward(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    for key in ("passed", "pass", "binary_pass"):
        if bool_true(data.get(key)):
            return True
    return False


def metadata_from_result(result_data: Any) -> tuple[str, str, str | None]:
    if not isinstance(result_data, dict):
        return "", "", None
    agent = (
        nested_get(result_data, ("agent_info", "name"))
        or nested_get(result_data, ("config", "agent", "name"))
        or ""
    )
    model = (
        nested_get(result_data, ("config", "agent", "model_name"))
        or nested_get(result_data, ("agent_info", "model_info", "name"))
        or ""
    )
    task = normalize_task_name(
        result_data.get("task_name"),
        nested_get(result_data, ("config", "task", "path")),
        nested_get(result_data, ("task_id", "path")),
        result_data.get("trial_name"),
    )
    return str(agent or ""), str(model or ""), task


def is_target_model(agent: str, model: str) -> bool:
    agent_ok = agent == AGENT_UNDER_TEST
    model_text = model.lower()
    model_ok = MODEL_UNDER_TEST in model_text or f"gemini/{MODEL_UNDER_TEST}" in model_text
    return agent_ok and model_ok


def candidate_trial_dirs() -> list[Path]:
    candidates: set[Path] = set()
    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("verifier/reward.json"):
            if normalize_task_name(path):
                candidates.add(path.parent.parent)
        for path in root.rglob("verifier/reward.txt"):
            if normalize_task_name(path):
                candidates.add(path.parent.parent)
        for path in root.rglob("result.json"):
            if normalize_task_name(path):
                # Include scored and unscored hard-task trial directories. The
                # parser will later skip unscored exception attempts without
                # inventing rewards.
                candidates.add(path.parent)
    return sorted(candidates, key=lambda p: (infer_timestamp(p), str(p)))


def classify_failure_text(text: str, task_name: str) -> str:
    lower = text.lower()
    if any(token in lower for token in ("wrong label", "wrong drug", "wrong set_id", "wrong set id")):
        return "wrong_drug_or_label"
    if any(token in lower for token in ("citation", "passage", "quote", "support", "section")):
        return "missed_section_or_citation"
    if any(token in lower for token in ("wrong_dose", "wrong_unit", "wrong_population", "dose", "unit", "frequency", "dosage")):
        return "numeric_dosage_error"
    if any(token in lower for token in ("refusal", "not_found", "not found", "overrefusal", "answered/not_found")):
        return "near_miss_refusal_or_overrefusal"
    if any(token in lower for token in ("schema", "format", "json", "missing required", "missing qid")):
        return "formatting_or_schema_error"
    if any(token in lower for token in ("timeout", "exception", "environment", "verifier")):
        return "verifier_or_environment_issue"
    if task_name == "fda-hard-multisection-synthesis" and any(
        token in lower for token in ("semantic", "answer", "qualifier", "content")
    ):
        return "incomplete_multisection_synthesis"
    return "unknown"


def categories_from_reward_json(data: Any, task_name: str) -> tuple[str, ...]:
    if not isinstance(data, dict):
        return ("unknown",)
    categories: list[str] = []
    for error in data.get("critical_errors") or []:
        categories.append(classify_failure_text(str(error), task_name))
    for schema_error in data.get("schema_errors") or []:
        categories.append(classify_failure_text(str(schema_error), task_name))
    for item in data.get("per_question") or data.get("question_scores") or []:
        if not isinstance(item, dict):
            continue
        for error in item.get("critical_errors") or []:
            categories.append(classify_failure_text(str(error), task_name))
        for diagnostic in item.get("diagnostics") or []:
            categories.append(classify_failure_text(str(diagnostic), task_name))
        for criterion, detail in (item.get("subcriteria") or {}).items():
            if not isinstance(detail, dict):
                continue
            score = as_float(detail.get("score"))
            passed = bool_true(detail.get("passed")) if "passed" in detail else (score is not None and score >= 0.999999)
            if passed:
                continue
            reason = detail.get("reason") or criterion
            categories.append(classify_failure_text(f"{criterion}: {reason}", task_name))
    categories = [category for category in categories if category]
    return tuple(categories or ["unknown"])


def parse_trial(trial_dir: Path) -> Trial | None:
    result_data = read_json(trial_dir / "result.json")
    if not isinstance(result_data, dict):
        # Some layouts only have the timestamp-level result.json.
        timestamp_result = trial_dir.parent / "result.json"
        result_data = read_json(timestamp_result)
    reward_data = read_json(trial_dir / "verifier" / "reward.json")

    agent, model, result_task = metadata_from_result(result_data)
    task_name = (
        normalize_task_name(
            result_task,
            reward_data.get("task_name") if isinstance(reward_data, dict) else None,
            trial_dir.name,
            str(trial_dir),
        )
        or ""
    )
    if not task_name:
        return None
    if not is_target_model(agent, model):
        return None

    reward = None
    reward_source = ""
    if isinstance(reward_data, dict):
        reward = reward_from_reward_json(reward_data)
        if reward is not None:
            reward_source = str(trial_dir / "verifier" / "reward.json")
    if reward is None:
        reward = reward_from_text(trial_dir / "verifier" / "reward.txt")
        if reward is not None:
            reward_source = str(trial_dir / "verifier" / "reward.txt")
    if reward is None:
        reward = reward_from_result_json(result_data)
        if reward is not None:
            reward_source = str(trial_dir / "result.json")
    if reward is None:
        return None

    explicit_pass = explicit_pass_from_reward(reward_data)
    passed = explicit_pass or reward >= PASS_THRESHOLD
    timestamp = infer_timestamp(trial_dir)
    run_id = trial_dir.name
    if "__" in run_id:
        run_id = run_id.split("__", 1)[1]
    n_questions = None
    schema_error_count = 0
    critical_errors = ""
    categories = ("unknown",) if not passed else tuple()
    if isinstance(reward_data, dict):
        n_questions_raw = reward_data.get("num_questions")
        if isinstance(n_questions_raw, int):
            n_questions = n_questions_raw
        elif isinstance(reward_data.get("per_question"), list):
            n_questions = len(reward_data["per_question"])
        schema_error_count = len(reward_data.get("schema_errors") or [])
        critical_errors = ";".join(str(x) for x in (reward_data.get("critical_errors") or []))
        if not passed:
            categories = categories_from_reward_json(reward_data, task_name)

    return Trial(
        trial_dir=trial_dir,
        job_timestamp=timestamp,
        run_id=run_id,
        task_name=task_name,
        agent=agent,
        model=model,
        reward=float(reward),
        reward_source=reward_source,
        passed=passed,
        explicit_pass=explicit_pass,
        started_at=str(result_data.get("started_at", "") if isinstance(result_data, dict) else ""),
        finished_at=str(result_data.get("finished_at", "") if isinstance(result_data, dict) else ""),
        n_questions=n_questions,
        schema_error_count=schema_error_count,
        critical_errors=critical_errors,
        failure_categories=categories,
    )


def dedupe_trials(trials: list[Trial]) -> list[Trial]:
    """Deduplicate copied runs by timestamp, task, and run id."""
    by_key: dict[tuple[str, str, str], Trial] = {}
    for trial in trials:
        key = (trial.job_timestamp, trial.task_name, trial.run_id)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = trial
            continue
        # Prefer richer verifier-sourced records.
        if "reward.json" in trial.reward_source and "reward.json" not in existing.reward_source:
            by_key[key] = trial
    return sorted(by_key.values(), key=lambda t: (t.task_name, t.job_timestamp, t.run_id))


def skipped_target_row(trial_dir: Path) -> dict[str, Any] | None:
    result_data = read_json(trial_dir / "result.json")
    if not isinstance(result_data, dict):
        return None
    agent, model, result_task = metadata_from_result(result_data)
    task_name = normalize_task_name(result_task, trial_dir.name, str(trial_dir))
    if not task_name or not is_target_model(agent, model):
        return None
    exception_info = result_data.get("exception_info") if isinstance(result_data.get("exception_info"), dict) else {}
    run_id = trial_dir.name.split("__", 1)[1] if "__" in trial_dir.name else trial_dir.name
    return {
        "task_name": task_name,
        "job_timestamp": infer_timestamp(trial_dir),
        "run_id": run_id,
        "trial_path": str(trial_dir.relative_to(PROJECT_ROOT)),
        "agent": agent,
        "model": model,
        "skip_reason": "no verifier reward found",
        "exception_type": str(exception_info.get("exception_type", "")),
        "exception_message": str(exception_info.get("exception_message", ""))[:500],
    }


def collect_trials() -> tuple[list[Trial], list[dict[str, Any]], list[Path]]:
    searched = [root for root in SEARCH_ROOTS]
    trials: list[Trial] = []
    skipped: list[dict[str, Any]] = []
    for path in candidate_trial_dirs():
        trial = parse_trial(path)
        if trial is not None:
            trials.append(trial)
        else:
            row = skipped_target_row(path)
            if row is not None:
                skipped.append(row)
    return dedupe_trials(trials), skipped, searched


def task_label(task_name: str) -> str:
    return TASK_DISPLAY.get(task_name, task_name.replace("fda-hard-", "").replace("-", " ").title())


def build_dataframes(trials: list[Trial]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    trial_rows = []
    for trial in trials:
        trial_rows.append(
            {
                "task_name": trial.task_name,
                "task_label": task_label(trial.task_name),
                "job_timestamp": trial.job_timestamp,
                "run_id": trial.run_id,
                "trial_path": str(trial.trial_dir.relative_to(PROJECT_ROOT)),
                "agent": trial.agent,
                "model": trial.model,
                "reward": trial.reward,
                "pass": int(trial.passed),
                "explicit_pass": int(trial.explicit_pass),
                "reward_source": str(Path(trial.reward_source).relative_to(PROJECT_ROOT))
                if trial.reward_source.startswith(str(PROJECT_ROOT))
                else trial.reward_source,
                "started_at": trial.started_at,
                "finished_at": trial.finished_at,
                "num_questions": trial.n_questions,
                "schema_error_count": trial.schema_error_count,
                "critical_errors": trial.critical_errors,
                "failure_categories": ";".join(trial.failure_categories),
            }
        )
    trial_df = pd.DataFrame(trial_rows)
    if trial_df.empty:
        return trial_df, pd.DataFrame(), pd.DataFrame()

    trial_df = trial_df.sort_values(["task_name", "job_timestamp", "run_id"]).reset_index(drop=True)
    trial_df["trial_number"] = trial_df.groupby("task_name").cumcount() + 1

    summary_rows = []
    for task_name, task_df in trial_df.groupby("task_name", sort=False):
        task_df = task_df.sort_values(["job_timestamp", "run_id"])
        first_three = task_df.head(3)
        rewards = task_df["reward"].astype(float).tolist()
        n_trials = len(task_df)
        n_pass = int(task_df["pass"].sum())
        pass_at_1 = n_pass / n_trials if n_trials else 0.0
        pass_at_3 = 1.0 if int(first_three["pass"].sum()) > 0 else 0.0
        summary_rows.append(
            {
                "task_name": task_name,
                "n_trials": n_trials,
                "rewards": ";".join(f"{reward:.6f}" for reward in rewards),
                "n_pass": n_pass,
                "pass_at_1": pass_at_1,
                "pass_at_3": pass_at_3,
                "mean_reward": float(np.mean(rewards)),
                "max_reward": float(np.max(rewards)),
                "min_reward": float(np.min(rewards)),
            }
        )
    summary_df = pd.DataFrame(summary_rows)
    summary_df = summary_df.sort_values(
        ["pass_at_3", "pass_at_1", "mean_reward", "task_name"],
        ascending=[True, True, True, True],
    ).reset_index(drop=True)

    taxonomy_rows = []
    for _, row in trial_df[trial_df["pass"] == 0].iterrows():
        categories = [c for c in str(row["failure_categories"]).split(";") if c]
        for category in categories or ["unknown"]:
            taxonomy_rows.append(
                {
                    "task_name": row["task_name"],
                    "job_timestamp": row["job_timestamp"],
                    "run_id": row["run_id"],
                    "reward": row["reward"],
                    "failure_category": category,
                }
            )
    taxonomy_df = pd.DataFrame(taxonomy_rows)
    return trial_df, summary_df, taxonomy_df


def configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": TOKENS["surface"],
            "axes.facecolor": TOKENS["panel"],
            "axes.edgecolor": TOKENS["axis"],
            "axes.labelcolor": TOKENS["ink"],
            "xtick.color": TOKENS["muted"],
            "ytick.color": TOKENS["muted"],
            "text.color": TOKENS["ink"],
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 13,
            "axes.titleweight": "bold",
            "axes.grid": True,
            "grid.color": TOKENS["grid"],
            "grid.linewidth": 0.8,
            "grid.alpha": 1.0,
        }
    )


def add_header(fig: plt.Figure, title: str, subtitle: str) -> None:
    fig.text(0.01, 0.985, title, ha="left", va="top", fontsize=14, fontweight="bold", color=TOKENS["ink"])
    fig.text(0.01, 0.945, subtitle, ha="left", va="top", fontsize=10, color=TOKENS["muted"])


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def plot_pass_rates(summary_df: pd.DataFrame, path: Path) -> None:
    ordered = summary_df.copy()
    labels = [task_label(t) for t in ordered["task_name"]]
    x = np.arange(len(ordered))
    width = 0.36
    fig, ax = plt.subplots(figsize=(11, 6.2))
    add_header(
        fig,
        "Hard FDA pass rates by task",
        "Pass@1 is passing trials / trials; pass@3 is whether any of the first three Gemini trials passed.",
    )
    ax.bar(x - width / 2, ordered["pass_at_1"], width, label="pass@1", color=BLUE["base"], edgecolor=BLUE["dark"])
    ax.bar(x + width / 2, ordered["pass_at_3"], width, label="pass@3", color=GOLD["base"], edgecolor=GOLD["dark"])
    ax.axhline(HEADROOM_THRESHOLD, color=ORANGE["dark"], linestyle="--", linewidth=1.4, label="30% pass@3 target")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Pass rate")
    ax.legend(loc="upper left", bbox_to_anchor=(0, 1.03), ncols=3, frameon=False)
    ax.yaxis.grid(True)
    ax.xaxis.grid(False)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    save_figure(fig, path)


def plot_reward_distribution(trial_df: pd.DataFrame, summary_df: pd.DataFrame, path: Path) -> None:
    order = summary_df["task_name"].tolist()
    labels = [task_label(t) for t in order]
    grouped = [trial_df.loc[trial_df["task_name"] == task, "reward"].astype(float).values for task in order]
    fig, ax = plt.subplots(figsize=(11, 6.4))
    add_header(
        fig,
        "Fractional rewards show partial-credit near misses",
        "Boxplots summarize spread; points show every Gemini Flash trial reward.",
    )
    ax.boxplot(
        grouped,
        patch_artist=True,
        tick_labels=labels,
        medianprops={"color": TOKENS["ink"], "linewidth": 1.4},
        boxprops={"facecolor": BLUE["xlight"], "edgecolor": BLUE["dark"]},
        whiskerprops={"color": BLUE["dark"]},
        capprops={"color": BLUE["dark"]},
        flierprops={"marker": "o", "markerfacecolor": ORANGE["base"], "markeredgecolor": ORANGE["dark"], "alpha": 0.6},
    )
    for i, values in enumerate(grouped, start=1):
        if len(values) == 0:
            continue
        jitter = np.linspace(-0.12, 0.12, len(values)) if len(values) > 1 else np.array([0.0])
        ax.scatter(
            np.full(len(values), i) + jitter,
            values,
            color=ORANGE["mid"],
            edgecolor=ORANGE["dark"],
            s=28,
            zorder=3,
            alpha=0.9,
        )
    ax.set_ylabel("Fractional reward")
    ax.set_ylim(0, 1.05)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.yaxis.grid(True)
    ax.xaxis.grid(False)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    save_figure(fig, path)


def plot_difficulty_curve(summary_df: pd.DataFrame, path: Path) -> None:
    ordered = summary_df.copy()
    labels = [task_label(t) for t in ordered["task_name"]]
    x = np.arange(len(ordered))
    fig, ax = plt.subplots(figsize=(11, 5.8))
    add_header(
        fig,
        "Difficulty curve from hardest to easiest",
        "Tasks are sorted by pass@3, then pass@1; mean reward separates near-misses from fully failed tasks.",
    )
    ax.plot(x, ordered["pass_at_3"], marker="o", color=GOLD["dark"], label="pass@3", linewidth=2)
    ax.plot(x, ordered["pass_at_1"], marker="o", color=BLUE["dark"], label="pass@1", linewidth=2)
    ax.scatter(x, ordered["mean_reward"], color=OLIVE["mid"], edgecolor=OLIVE["dark"], label="mean reward", zorder=4)
    for xi, reward in zip(x, ordered["mean_reward"]):
        ax.text(xi, reward + 0.035, f"{reward:.2f}", ha="center", va="bottom", fontsize=8, color=TOKENS["muted"])
    ax.axhline(HEADROOM_THRESHOLD, color=ORANGE["dark"], linestyle="--", linewidth=1.2, label="30% pass@3 target")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right")
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Rate / reward")
    ax.legend(loc="upper left", bbox_to_anchor=(0, 1.04), ncols=4, frameon=False)
    ax.yaxis.grid(True)
    ax.xaxis.grid(False)
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    save_figure(fig, path)


def plot_trial_heatmap(trial_df: pd.DataFrame, summary_df: pd.DataFrame, path: Path) -> None:
    order = summary_df["task_name"].tolist()
    max_trial = int(trial_df["trial_number"].max())
    matrix = np.full((len(order), max_trial), np.nan)
    for row_i, task in enumerate(order):
        rows = trial_df[trial_df["task_name"] == task].sort_values("trial_number")
        for _, row in rows.iterrows():
            matrix[row_i, int(row["trial_number"]) - 1] = float(row["reward"])

    fig, ax = plt.subplots(figsize=(max(10, max_trial * 0.55), 6.2))
    add_header(
        fig,
        "Trial-level rewards by task",
        "Rows are hard FDA tasks; columns are chronological Gemini Flash trials. Blank cells mean no trial.",
    )
    cmap = plt.cm.YlGnBu.copy()
    cmap.set_bad("#F4F5F7")
    im = ax.imshow(matrix, aspect="auto", cmap=cmap, vmin=0, vmax=1)
    ax.set_yticks(np.arange(len(order)))
    ax.set_yticklabels([task_label(t) for t in order])
    ax.set_xticks(np.arange(max_trial))
    ax.set_xticklabels([f"T{i}" for i in range(1, max_trial + 1)])
    ax.set_xlabel("Trial number")
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            value = matrix[i, j]
            if np.isnan(value):
                continue
            color = TOKENS["ink"] if value < 0.72 else "#FFFFFF"
            ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=8, color=color)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Reward")
    ax.grid(False)
    fig.tight_layout(rect=[0, 0, 1, 0.90])
    save_figure(fig, path)


def plot_failure_taxonomy(taxonomy_df: pd.DataFrame, path: Path) -> bool:
    if taxonomy_df.empty:
        return False
    counts = taxonomy_df["failure_category"].value_counts().sort_values(ascending=True)
    if counts.empty or (counts.index == "unknown").all():
        return False
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    add_header(
        fig,
        "Verifier-derived failure taxonomy",
        "Counts come from explicit verifier diagnostics, subcriteria, schema errors, and critical errors.",
    )
    colors = [PINK["base"] if idx == "unknown" else BLUE["base"] for idx in counts.index]
    bars = ax.barh(counts.index, counts.values, color=colors, edgecolor=BLUE["dark"])
    ax.set_xlabel("Failure-label count")
    ax.xaxis.grid(True)
    ax.yaxis.grid(False)
    for bar in bars:
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2, f"{int(bar.get_width())}", va="center", fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    save_figure(fig, path)
    return True


def write_csv_outputs(
    trial_df: pd.DataFrame,
    summary_df: pd.DataFrame,
    taxonomy_df: pd.DataFrame,
    skipped_rows: list[dict[str, Any]],
) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    summary_df.to_csv(REPORT_DIR / "hard_question_set_summary.csv", index=False, float_format="%.6f")
    trial_df.to_csv(REPORT_DIR / "hard_question_set_trials.csv", index=False, float_format="%.6f")
    if skipped_rows:
        pd.DataFrame(skipped_rows).to_csv(REPORT_DIR / "hard_question_set_skipped_trials.csv", index=False)
    if taxonomy_df.empty:
        taxonomy_template = pd.DataFrame(
            columns=["task_name", "job_timestamp", "run_id", "reward", "failure_category", "manual_label_notes"]
        )
        taxonomy_template.to_csv(REPORT_DIR / "hard_failure_taxonomy_template.csv", index=False)
    else:
        taxonomy_df.to_csv(REPORT_DIR / "hard_failure_taxonomy.csv", index=False, float_format="%.6f")


def markdown_table(df: pd.DataFrame, columns: list[str]) -> list[str]:
    rows = []
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    rows.extend([header, separator])
    for _, row in df.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float):
                value = f"{value:.3f}"
            values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return rows


def write_markdown_summary(
    summary_df: pd.DataFrame,
    trial_df: pd.DataFrame,
    taxonomy_df: pd.DataFrame,
    taxonomy_png_created: bool,
    skipped_rows: list[dict[str, Any]],
) -> None:
    total_trials = int(summary_df["n_trials"].sum())
    total_passes = int(summary_df["n_pass"].sum())
    aggregate_pass_at_1 = total_passes / total_trials if total_trials else 0.0
    aggregate_pass_at_3 = float(summary_df["pass_at_3"].mean()) if not summary_df.empty else 0.0
    below_target = aggregate_pass_at_3 < HEADROOM_THRESHOLD

    hardest = summary_df.sort_values(["pass_at_3", "pass_at_1", "mean_reward", "max_reward"]).head(3)
    easiest = summary_df.sort_values(["pass_at_3", "pass_at_1", "mean_reward"], ascending=[False, False, False]).head(3)
    near_misses = summary_df[(summary_df["n_pass"] == 0) & (summary_df["max_reward"] >= 0.75)].copy()

    display_summary = summary_df.copy()
    display_summary["task_name"] = display_summary["task_name"].map(task_label)
    display_summary["pass_at_1"] = display_summary["pass_at_1"].map(lambda x: f"{x:.3f}")
    display_summary["pass_at_3"] = display_summary["pass_at_3"].map(lambda x: f"{x:.3f}")
    display_summary["mean_reward"] = display_summary["mean_reward"].map(lambda x: f"{x:.3f}")
    display_summary["max_reward"] = display_summary["max_reward"].map(lambda x: f"{x:.3f}")
    display_summary["min_reward"] = display_summary["min_reward"].map(lambda x: f"{x:.3f}")

    lines = [
        "# Hard FDA Question Set Summary",
        "",
        "## Aggregate Results",
        "",
        f"- Tasks detected: {summary_df['task_name'].nunique()}",
        f"- Trials detected: {total_trials}",
        f"- Unscored target-agent attempts skipped: {len(skipped_rows)}",
        f"- Aggregate pass@1: {aggregate_pass_at_1:.3f} ({total_passes}/{total_trials})",
        f"- Aggregate pass@3: {aggregate_pass_at_3:.3f}",
        f"- Below 30% pass@3 target: {'yes' if below_target else 'no'}",
        f"- Mean fractional reward across trials: {trial_df['reward'].mean():.3f}",
        "",
        "## Task Summary",
        "",
    ]
    lines.extend(
        markdown_table(
            display_summary,
            ["task_name", "n_trials", "rewards", "n_pass", "pass_at_1", "pass_at_3", "mean_reward", "max_reward", "min_reward"],
        )
    )
    lines.extend(["", "## Hardest Tasks", ""])
    lines.extend(
        f"- {task_label(row.task_name)}: pass@3={row.pass_at_3:.3f}, pass@1={row.pass_at_1:.3f}, mean reward={row.mean_reward:.3f}"
        for row in hardest.itertuples()
    )
    lines.extend(["", "## Easiest Tasks", ""])
    lines.extend(
        f"- {task_label(row.task_name)}: pass@3={row.pass_at_3:.3f}, pass@1={row.pass_at_1:.3f}, mean reward={row.mean_reward:.3f}"
        for row in easiest.itertuples()
    )
    lines.extend(["", "## Fractional Near-Misses", ""])
    if near_misses.empty:
        lines.append("- No no-pass task reached a max reward of 0.75.")
    else:
        lines.extend(
            f"- {task_label(row.task_name)}: max reward={row.max_reward:.3f}, mean reward={row.mean_reward:.3f}, pass@3={row.pass_at_3:.3f}"
            for row in near_misses.sort_values("max_reward", ascending=False).itertuples()
        )
    lines.extend(
        [
            "",
            "## Figure Notes",
            "",
            "- `figures/hard_pass_rates.png`: grouped pass@1/pass@3 bars by task, with the 30% pass@3 target line.",
            "- `figures/hard_reward_distribution.png`: per-task reward spread with individual trial rewards overlaid.",
            "- `figures/hard_difficulty_curve.png`: hardest-to-easiest task curve using pass rates and mean reward.",
            "- `figures/hard_trial_heatmap.png`: reward values by task and chronological trial number.",
        ]
    )
    if taxonomy_png_created:
        lines.append("- `figures/hard_failure_taxonomy.png`: verifier-derived failure labels aggregated across failed trials.")
    elif taxonomy_df.empty:
        lines.append("- `hard_failure_taxonomy_template.csv`: manual taxonomy template was created because no verifier labels were available.")
    else:
        lines.append("- `hard_failure_taxonomy.csv`: verifier labels were exported; figure omitted because labels were not informative enough.")
    if skipped_rows:
        lines.append("- `hard_question_set_skipped_trials.csv`: target-agent attempts with no verifier reward, excluded from reward/pass calculations.")

    (REPORT_DIR / "hard_question_set_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def fail_no_runs(searched: list[Path]) -> None:
    searched_text = "\n".join(f"- {path}" for path in searched)
    raise SystemExit(
        "No valid Gemini 3.5 Flash hard FDA Harbor runs were found.\n"
        "Searched these roots:\n"
        f"{searched_text}\n"
        "Expected artifacts such as jobs/**/result.json, jobs/**/verifier/reward.json, "
        "logs/**/result.json, or logs/**/verifier/reward.json."
    )


def main() -> None:
    configure_matplotlib()
    trials, skipped_rows, searched = collect_trials()
    if not trials:
        fail_no_runs(searched)

    trial_df, summary_df, taxonomy_df = build_dataframes(trials)
    if trial_df.empty or summary_df.empty:
        fail_no_runs(searched)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    write_csv_outputs(trial_df, summary_df, taxonomy_df, skipped_rows)

    plot_pass_rates(summary_df, FIGURE_DIR / "hard_pass_rates.png")
    plot_reward_distribution(trial_df, summary_df, FIGURE_DIR / "hard_reward_distribution.png")
    plot_difficulty_curve(summary_df, FIGURE_DIR / "hard_difficulty_curve.png")
    plot_trial_heatmap(trial_df, summary_df, FIGURE_DIR / "hard_trial_heatmap.png")
    taxonomy_png_created = plot_failure_taxonomy(taxonomy_df, FIGURE_DIR / "hard_failure_taxonomy.png")

    write_markdown_summary(summary_df, trial_df, taxonomy_df, taxonomy_png_created, skipped_rows)

    total_trials = int(summary_df["n_trials"].sum())
    total_passes = int(summary_df["n_pass"].sum())
    aggregate_pass_at_1 = total_passes / total_trials if total_trials else 0.0
    aggregate_pass_at_3 = float(summary_df["pass_at_3"].mean()) if not summary_df.empty else 0.0

    print("Hard FDA Gemini 3.5 Flash analysis complete")
    print(f"Tasks detected: {summary_df['task_name'].nunique()}")
    print(f"Trials detected: {total_trials}")
    print(f"Unscored target-agent attempts skipped: {len(skipped_rows)}")
    print(f"Aggregate pass@1: {aggregate_pass_at_1:.3f} ({total_passes}/{total_trials})")
    print(f"Aggregate pass@3: {aggregate_pass_at_3:.3f}")
    print(f"Below 30% pass@3 target: {'yes' if aggregate_pass_at_3 < HEADROOM_THRESHOLD else 'no'}")
    print(f"Wrote: {REPORT_DIR / 'hard_question_set_summary.csv'}")
    print(f"Wrote: {REPORT_DIR / 'hard_question_set_summary.md'}")
    print(f"Wrote figures to: {FIGURE_DIR}")


if __name__ == "__main__":
    main()
