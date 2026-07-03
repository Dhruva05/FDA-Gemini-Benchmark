#!/usr/bin/env python3
"""Profile FDA-label QA JSONL files for Harbor benchmark design."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import string
from collections import Counter
from pathlib import Path
from typing import Any


NOT_FOUND = "Information not found!"
TASK_KEYS = ("task", "question_type", "qfilter_category")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_no}: invalid JSON: {exc}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected JSON object")
            rows.append(row)
    return rows


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [value]


def normalize_task(row: dict[str, Any]) -> str:
    for key in TASK_KEYS:
        value = row.get(key)
        if isinstance(value, str) and value.strip() and value.strip().upper() != "NA":
            return value.strip().lower()
    return "other"


def word_count(value: Any) -> int:
    return len(re.findall(r"[A-Za-z0-9]+", "" if value is None else str(value)))


def distribution(values: list[int]) -> dict[str, Any]:
    counts = Counter(values)
    if not values:
        return {"counts": {}, "min": 0, "p50": 0, "p90": 0, "max": 0, "mean": 0.0}
    ordered = sorted(values)

    def percentile(pct: float) -> int:
        if not ordered:
            return 0
        index = min(len(ordered) - 1, round((len(ordered) - 1) * pct))
        return ordered[index]

    return {
        "counts": {str(key): counts[key] for key in sorted(counts)},
        "min": ordered[0],
        "p50": percentile(0.50),
        "p90": percentile(0.90),
        "max": ordered[-1],
        "mean": round(statistics.fmean(values), 3),
    }


def template_for_question(question: Any, drug_name: Any = "") -> str:
    text = "" if question is None else str(question).lower()
    drug = "" if drug_name is None else str(drug_name).lower().strip()
    if drug:
        text = text.replace(drug, "{drug}")
    text = re.sub(r"\b\d+(?:\.\d+)?\b", "{num}", text)
    text = text.translate(str.maketrans({ch: " " for ch in string.punctuation}))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compact_row(row: dict[str, Any], label_by_set_id: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    contexts = ensure_list(row.get("context"))
    citations = ensure_list(row.get("citations"))
    references = ensure_list(row.get("references"))
    label = (label_by_set_id or {}).get(str(row.get("set_id", "")), {})
    return {
        "qid": row.get("qid"),
        "task": normalize_task(row),
        "question_type": row.get("question_type"),
        "drug_name": row.get("drug_name"),
        "set_id": row.get("set_id"),
        "question": row.get("question"),
        "answer_preview": str(row.get("answer", ""))[:500],
        "context_count": len(contexts),
        "citation_count": len(citations),
        "reference_count": len(references),
        "answer_word_count": word_count(row.get("answer")),
        "label_chunk_count": len(ensure_list(label.get("chunks"))),
    }


def repeated_templates(rows: list[dict[str, Any]], limit: int = 30) -> list[dict[str, Any]]:
    examples_by_template: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        template = template_for_question(row.get("question"), row.get("drug_name"))
        examples_by_template.setdefault(template, []).append(row)
    repeated = []
    for template, grouped in examples_by_template.items():
        if len(grouped) < 2:
            continue
        repeated.append(
            {
                "template": template,
                "count": len(grouped),
                "example_qids": [str(item.get("qid", "")) for item in grouped[:5]],
                "example_questions": [str(item.get("question", "")) for item in grouped[:3]],
            }
        )
    repeated.sort(key=lambda item: (-item["count"], item["template"]))
    return repeated[:limit]


def select_candidate_examples(rows: list[dict[str, Any]], label_by_set_id: dict[str, dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    def is_refusal(row: dict[str, Any]) -> bool:
        return str(row.get("answer", "")).strip().lower() == NOT_FOUND.lower() or normalize_task(row) == "refusal"

    def safetyish(row: dict[str, Any]) -> bool:
        text = f"{row.get('question', '')} {row.get('answer', '')} {row.get('references', '')}".lower()
        return any(term in text for term in ("warning", "precaution", "risk", "adverse", "contraindication", "pregnan", "interaction"))

    def score_hard(row: dict[str, Any]) -> tuple[int, int, int, int]:
        contexts = len(ensure_list(row.get("context")))
        citations = len(ensure_list(row.get("citations"))) + len(ensure_list(row.get("references")))
        chunk_count = len(ensure_list(label_by_set_id.get(str(row.get("set_id", "")), {}).get("chunks")))
        return (contexts + citations, contexts, chunk_count, word_count(row.get("answer")))

    answerable = [row for row in rows if not is_refusal(row)]
    refusals = [row for row in rows if is_refusal(row)]
    many_context = sorted(answerable, key=score_hard, reverse=True)[:20]
    long_label = sorted(answerable, key=lambda row: len(ensure_list(label_by_set_id.get(str(row.get("set_id", "")), {}).get("chunks"))), reverse=True)[:20]
    safety = sorted([row for row in answerable if safetyish(row)], key=score_hard, reverse=True)[:20]
    harder_refusals = sorted(
        refusals,
        key=lambda row: (
            sum(term in str(row.get("question", "")).lower() for term in ("dose", "impairment", "pregnancy", "renal", "hepatic", "contraindication")),
            len(str(row.get("question", ""))),
        ),
        reverse=True,
    )[:20]
    obvious_refusals = sorted(refusals, key=lambda row: len(str(row.get("question", ""))))[:20]
    return {
        "many_citations_or_context": [compact_row(row, label_by_set_id) for row in many_context],
        "long_label_retrieval": [compact_row(row, label_by_set_id) for row in long_label],
        "safety_warning_candidates": [compact_row(row, label_by_set_id) for row in safety],
        "better_hard_refusals": [compact_row(row, label_by_set_id) for row in harder_refusals],
        "easy_or_obvious_refusals": [compact_row(row, label_by_set_id) for row in obvious_refusals],
    }


def profile_data(
    labels_path: Path,
    qa_path: Path,
    qa_toy_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    labels = read_jsonl(labels_path)
    qa_rows = read_jsonl(qa_path)
    qa_toy_rows = read_jsonl(qa_toy_path) if qa_toy_path and qa_toy_path.exists() else []
    label_by_set_id = {str(row.get("set_id", "")): row for row in labels}

    chunk_counts = [len(ensure_list(row.get("chunks"))) for row in labels]
    context_counts = [len(ensure_list(row.get("context"))) for row in qa_rows]
    citation_counts = [len(ensure_list(row.get("citations"))) + len(ensure_list(row.get("references"))) for row in qa_rows]
    answer_lengths = [word_count(row.get("answer")) for row in qa_rows]

    longest_labels = sorted(
        (
            {
                "set_id": row.get("set_id"),
                "drug_name": row.get("drug_name"),
                "drug_id": row.get("drug_id"),
                "chunk_count": len(ensure_list(row.get("chunks"))),
                "label_char_count": len(str(row.get("label_raw", ""))),
            }
            for row in labels
        ),
        key=lambda item: (-int(item["chunk_count"]), str(item["drug_name"])),
    )[:20]

    hardest_rows = sorted(
        qa_rows,
        key=lambda row: (
            len(ensure_list(row.get("context"))) + len(ensure_list(row.get("citations"))) + len(ensure_list(row.get("references"))),
            len(ensure_list(row.get("context"))),
            word_count(row.get("answer")),
        ),
        reverse=True,
    )[:20]

    profile = {
        "label_count": len(labels),
        "qa_row_count": len(qa_rows),
        "qa_files": {
            "qa.jsonl": {"path": str(qa_path), "row_count": len(qa_rows)},
            "qa_toy.jsonl": {"path": str(qa_toy_path) if qa_toy_path else "", "row_count": len(qa_toy_rows)},
        },
        "task_distribution": dict(sorted(Counter(normalize_task(row) for row in qa_rows).items())),
        "chunk_count_distribution": distribution(chunk_counts),
        "context_count_distribution": distribution(context_counts),
        "citation_count_distribution": distribution(citation_counts),
        "answer_length_distribution": distribution(answer_lengths),
        "longest_labels": longest_labels,
        "top_qa_rows_by_context_or_citations": [compact_row(row, label_by_set_id) for row in hardest_rows],
        "repeated_question_templates": repeated_templates(qa_rows),
        "candidate_hard_examples": select_candidate_examples(qa_rows, label_by_set_id),
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        write_json(output_dir / "fda_data_profile.json", profile)
        (output_dir / "fda_data_profile.md").write_text(render_markdown(profile), encoding="utf-8")

    return profile


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")


def row_line(item: dict[str, Any]) -> str:
    return (
        f"- `{item.get('qid', '')}` {item.get('drug_name', '')}: {item.get('question', '')} "
        f"(task={item.get('task', '')}, context={item.get('context_count', 0)}, "
        f"citations={item.get('citation_count', 0)}, label_chunks={item.get('label_chunk_count', 0)})"
    )


def render_markdown(profile: dict[str, Any]) -> str:
    lines = [
        "# FDA Data Profile",
        "",
        f"- Labels: {profile['label_count']}",
        f"- QA rows: {profile['qa_row_count']}",
        f"- Task distribution: `{json.dumps(profile['task_distribution'], sort_keys=True)}`",
        "",
        "## Distributions",
        "",
        f"- Label chunk counts: `{json.dumps(profile['chunk_count_distribution'], sort_keys=True)}`",
        f"- QA context counts: `{json.dumps(profile['context_count_distribution'], sort_keys=True)}`",
        f"- QA citation/reference counts: `{json.dumps(profile['citation_count_distribution'], sort_keys=True)}`",
        f"- Answer word counts: `{json.dumps(profile['answer_length_distribution'], sort_keys=True)}`",
        "",
        "## Top 20 Longest Labels",
        "",
    ]
    for item in profile["longest_labels"]:
        lines.append(f"- {item['drug_name']} (`{item['set_id']}`): {item['chunk_count']} chunks, {item['label_char_count']} chars")
    lines.extend(["", "## Top 20 QA Rows With Many Citations/Context Chunks", ""])
    for item in profile["top_qa_rows_by_context_or_citations"]:
        lines.append(row_line(item))
    lines.extend(["", "## Repeated Question Templates", ""])
    for item in profile["repeated_question_templates"][:20]:
        lines.append(f"- {item['count']}x `{item['template']}`")
    lines.extend(["", "## Easy/Obvious Refusal Questions", ""])
    for item in profile["candidate_hard_examples"]["easy_or_obvious_refusals"][:20]:
        lines.append(row_line(item))
    lines.extend(["", "## Better Hard/Refusal Questions", ""])
    for item in profile["candidate_hard_examples"]["better_hard_refusals"][:20]:
        lines.append(row_line(item))
    lines.extend(["", "## Candidate Hard Examples", ""])
    for bucket, rows in profile["candidate_hard_examples"].items():
        lines.append(f"### {bucket.replace('_', ' ').title()}")
        lines.append("")
        for item in rows[:10]:
            lines.append(row_line(item))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def default_paths() -> tuple[Path, Path, Path, Path]:
    repo_root = Path(__file__).resolve().parents[1]
    data_root = repo_root.parent
    return (
        data_root / "labels.jsonl",
        data_root / "qa.jsonl",
        data_root / "qa_toy.jsonl",
        repo_root / "analysis",
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    labels_path, qa_path, qa_toy_path, output_dir = default_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, default=labels_path)
    parser.add_argument("--qa", type=Path, default=qa_path)
    parser.add_argument("--qa-toy", type=Path, default=qa_toy_path)
    parser.add_argument("--output-dir", type=Path, default=output_dir)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    profile = profile_data(args.labels, args.qa, args.qa_toy, args.output_dir)
    print(f"labels: {profile['label_count']}")
    print(f"qa rows: {profile['qa_row_count']}")
    print("task distribution:", json.dumps(profile["task_distribution"], sort_keys=True))
    print(f"wrote {args.output_dir / 'fda_data_profile.json'}")
    print(f"wrote {args.output_dir / 'fda_data_profile.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
