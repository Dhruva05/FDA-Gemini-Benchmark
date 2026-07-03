#!/usr/bin/env python3
"""Fractional verifier for FDA hard-label Harbor tasks."""

from __future__ import annotations

import json
import os
import re
import string
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


NOT_FOUND = "Information not found!"
PASS_THRESHOLD = 0.85
WEIGHTS = {
    "schema": 0.05,
    "qid_present": 0.05,
    "answer_content": 0.35,
    "clinical_qualifiers": 0.20,
    "citation_support": 0.25,
    "refusal_behavior": 0.10,
}
REFUSAL_MARKERS = (
    "not found",
    "not present",
    "not provided",
    "not stated",
    "unsupported",
    "insufficient",
    "does not provide",
    "does not state",
    "no supported",
    "cannot determine",
)
FIELD_ALIASES = {
    "route": {
        "oral": {"oral", "orally", "by mouth", "po"},
        "orally": {"oral", "orally", "by mouth", "po"},
        "by mouth": {"oral", "orally", "by mouth", "po"},
        "intravenous": {"intravenous", "iv", "injection"},
        "topical": {"topical", "topically", "apply"},
        "topically": {"topical", "topically", "apply"},
    },
    "frequency": {
        "once daily": {"once daily", "daily", "one time daily"},
        "twice daily": {"twice daily", "two times daily", "bid"},
        "three times daily": {"three times daily", "tid"},
    },
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value).lower().replace("\u00a0", " ")
    text = text.translate(str.maketrans({ch: " " for ch in string.punctuation if ch not in {".", "%"}}))
    return re.sub(r"\s+", " ", text).strip()


def compact_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9.%]+", "", normalize_text(value))


def tokens(value: Any) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:\.[a-z0-9]+)?%?", normalize_text(value))


def token_f1(a: Any, b: Any) -> float:
    a_tokens = tokens(a)
    b_tokens = tokens(b)
    if not a_tokens and not b_tokens:
        return 1.0
    if not a_tokens or not b_tokens:
        return 0.0
    a_counts = Counter(a_tokens)
    b_counts = Counter(b_tokens)
    overlap = sum(min(a_counts[token], b_counts[token]) for token in b_counts)
    if overlap == 0:
        return 0.0
    precision = overlap / len(a_tokens)
    recall = overlap / len(b_tokens)
    return 2 * precision * recall / (precision + recall)


def fuzzy_ratio(a: Any, b: Any) -> float:
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    if not a_norm and not b_norm:
        return 1.0
    if not a_norm or not b_norm:
        return 0.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def similarity(a: Any, b: Any) -> float:
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    if a_norm == b_norm:
        return 1.0
    if a_norm and b_norm and (a_norm in b_norm or b_norm in a_norm):
        return 0.92
    return min(1.0, 0.70 * token_f1(a, b) + 0.30 * fuzzy_ratio(a, b))


def flatten_json(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(f"{key} {flatten_json(val)}" for key, val in value.items())
    if isinstance(value, list):
        return " ".join(flatten_json(item) for item in value)
    return "" if value is None else str(value)


def load_labels(path: Path) -> dict[str, dict[str, Any]]:
    labels: dict[str, dict[str, Any]] = {}
    for row in load_jsonl(path):
        chunks = [str(chunk) for chunk in row.get("chunks", [])]
        passages = {f"PASSAGE_{index:04d}": chunk for index, chunk in enumerate(chunks)}
        labels[str(row.get("set_id", ""))] = {
            "drug_name": row.get("drug_name"),
            "label_raw": row.get("label_raw", ""),
            "chunks": chunks,
            "passages": passages,
            "text": "\n".join([str(row.get("label_raw", ""))] + chunks),
        }
    return labels


def expected_status(gold: dict[str, Any]) -> str:
    if gold.get("status") in {"ANSWERED", "NOT_FOUND"}:
        return str(gold["status"])
    if normalize_text(gold.get("answer")) == normalize_text(NOT_FOUND):
        return "NOT_FOUND"
    return "ANSWERED"


def looks_like_refusal(answer: Any) -> bool:
    text = normalize_text(answer)
    return any(marker in text for marker in REFUSAL_MARKERS)


def expected_set_ids(gold: dict[str, Any]) -> set[str]:
    raw = gold.get("comparison_set_ids") or [gold.get("set_id")]
    return {str(set_id) for set_id in raw if set_id and not str(set_id).startswith("comparison:")}


def expected_evidence_text(gold: dict[str, Any]) -> str:
    parts = [str(gold.get("answer", "")), " ".join(str(term) for term in gold.get("expected_terms") or [])]
    for context in gold.get("context") or []:
        if isinstance(context, dict):
            parts.append(str(context.get("text", "")))
    for citation in gold.get("citations") or []:
        if isinstance(citation, dict):
            parts.append(str(citation.get("supporting_quote", "")))
    return "\n".join(part for part in parts if part)


def quote_in_text(quote: Any, text: Any) -> bool:
    quote_norm = normalize_text(quote)
    text_norm = normalize_text(text)
    if not quote_norm or not text_norm:
        return False
    return quote_norm in text_norm or similarity(quote_norm, text_norm) >= 0.55


def criterion(score: float, reason: str = "") -> dict[str, Any]:
    score = round(max(0.0, min(1.0, score)), 6)
    return {"score": score, "reason": "" if score >= 1.0 else reason}


def validate_answer_schema(answer: Any) -> tuple[float, list[str]]:
    diagnostics: list[str] = []
    if not isinstance(answer, dict):
        return 0.0, ["answer item is not an object"]
    required = {"qid", "status", "answer", "citations", "structured_fields"}
    missing = sorted(required - set(answer))
    if missing:
        diagnostics.append("missing fields: " + ", ".join(missing))
    if "qid" in answer and not isinstance(answer.get("qid"), str):
        diagnostics.append("qid must be a string")
    if "status" in answer and answer.get("status") not in {"ANSWERED", "NOT_FOUND"}:
        diagnostics.append("status must be ANSWERED or NOT_FOUND")
    if "answer" in answer and not isinstance(answer.get("answer"), str):
        diagnostics.append("answer must be a string")
    if "citations" in answer and not isinstance(answer.get("citations"), list):
        diagnostics.append("citations must be a list")
    if "structured_fields" in answer and not isinstance(answer.get("structured_fields"), dict):
        diagnostics.append("structured_fields must be an object")
    for idx, citation in enumerate(answer.get("citations", []) if isinstance(answer.get("citations"), list) else []):
        if not isinstance(citation, dict):
            diagnostics.append(f"citations[{idx}] must be an object")
            continue
        for field in ("set_id", "passage_id", "supporting_quote"):
            if not isinstance(citation.get(field), str):
                diagnostics.append(f"citations[{idx}].{field} must be a string")
        if citation.get("section") is not None and not isinstance(citation.get("section"), str):
            diagnostics.append(f"citations[{idx}].section must be a string or null")
    return (0.0 if diagnostics else 1.0), diagnostics


def value_matches(expected: Any, predicted: Any, answer_text: Any, field: str = "") -> bool:
    expected_norm = normalize_text(expected)
    predicted_norm = normalize_text(predicted)
    answer_norm = normalize_text(answer_text)
    if not expected_norm:
        return True
    if predicted_norm:
        if expected_norm == predicted_norm or expected_norm in predicted_norm or predicted_norm in expected_norm:
            return True
        alias_groups = FIELD_ALIASES.get(field, {})
        expected_aliases = alias_groups.get(expected_norm, {expected_norm})
        predicted_aliases = alias_groups.get(predicted_norm, {predicted_norm})
        if expected_aliases & predicted_aliases:
            return True
        if token_f1(expected_norm, predicted_norm) >= 0.75:
            return True
    return expected_norm in answer_norm


def content_score(answer: dict[str, Any], gold: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    diagnostics: list[str] = []
    critical_errors: list[str] = []
    status = expected_status(gold)
    if status == "NOT_FOUND":
        if answer.get("status") == "NOT_FOUND" and looks_like_refusal(answer.get("answer")):
            return 1.0, diagnostics, critical_errors
        if answer.get("status") == "NOT_FOUND":
            return 0.5, ["NOT_FOUND answer does not clearly explain unsupported information"], critical_errors
        critical_errors.append("hallucinated_answer_for_refusal")
        return 0.0, ["expected NOT_FOUND refusal"], critical_errors

    if answer.get("status") != "ANSWERED":
        return 0.0, ["refused an answerable question"], critical_errors
    if normalize_text(answer.get("answer")) == normalize_text(gold.get("answer")):
        return 1.0, diagnostics, critical_errors

    sim = similarity(answer.get("answer"), gold.get("answer"))
    terms = gold.get("expected_terms") or []
    haystack = normalize_text(f"{answer.get('answer', '')} {flatten_json(answer.get('structured_fields', {}))}")
    term_score = sum(1 for term in terms if normalize_text(term) in haystack) / len(terms) if terms else 1.0
    score = max(sim, 0.30 + 0.70 * term_score)
    if score < 0.72:
        diagnostics.append(f"answer has low semantic overlap with gold; score={score:.3f}")
    return min(1.0, score), diagnostics, critical_errors


def structured_field_score(answer: dict[str, Any], gold: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    diagnostics: list[str] = []
    critical_errors: list[str] = []
    expected_fields = gold.get("structured_fields") or {}
    predicted_fields = answer.get("structured_fields") or {}
    if not expected_fields:
        if similarity(answer.get("answer"), gold.get("answer")) >= 0.90:
            return 1.0, diagnostics, critical_errors
        terms = gold.get("expected_terms") or []
        haystack = normalize_text(answer.get("answer"))
        if not terms:
            return 1.0, diagnostics, critical_errors
        score = sum(1 for term in terms if normalize_text(term) in haystack) / len(terms)
        if score < 0.75:
            diagnostics.append("answer omits expected clinical qualifiers")
        return score, diagnostics, critical_errors

    if "comparison" in expected_fields:
        expected_text = flatten_json(expected_fields["comparison"])
        predicted_text = flatten_json(predicted_fields.get("comparison", predicted_fields))
        score = max(token_f1(expected_text, predicted_text), token_f1(expected_text, answer.get("answer")))
        if score < 0.65:
            diagnostics.append("comparison structured_fields omit expected label-specific qualifiers")
        return min(1.0, score), diagnostics, critical_errors

    scored_fields = [
        field
        for field in ("dose", "unit", "route", "frequency", "population", "max_daily_dose")
        if normalize_text(expected_fields.get(field))
    ]
    if not scored_fields:
        return 1.0, diagnostics, critical_errors

    correct = 0
    for field in scored_fields:
        expected = expected_fields.get(field, "")
        predicted = predicted_fields.get(field, "")
        if value_matches(expected, predicted, answer.get("answer"), field):
            correct += 1
            continue
        diagnostics.append(f"structured field {field} does not match expected value")
        if field in {"dose", "unit", "route", "population"} and predicted:
            critical_errors.append(f"wrong_{field}")
    return correct / len(scored_fields), diagnostics, critical_errors


def qualifier_score(answer: dict[str, Any], gold: dict[str, Any]) -> tuple[float, list[str], list[str]]:
    status = expected_status(gold)
    if status == "NOT_FOUND":
        expected = gold.get("structured_fields", {})
        topics = [expected.get("searched_topic", ""), expected.get("unsupported_topic", "")]
        topics = [topic for topic in topics if topic]
        if not topics:
            return (1.0, [], []) if answer.get("status") == "NOT_FOUND" else (0.0, ["expected NOT_FOUND"], [])
        haystack = normalize_text(f"{answer.get('answer', '')} {flatten_json(answer.get('structured_fields', {}))}")
        score = sum(1 for topic in topics if token_f1(topic, haystack) >= 0.25 or normalize_text(topic) in haystack) / len(topics)
        diagnostics = [] if score >= 1.0 else ["refusal explanation misses searched or unsupported topic"]
        return score, diagnostics, []
    return structured_field_score(answer, gold)


def citation_score(answer: dict[str, Any], gold: dict[str, Any], labels: dict[str, dict[str, Any]]) -> tuple[float, list[str], list[str]]:
    diagnostics: list[str] = []
    critical_errors: list[str] = []
    predicted = answer.get("citations") or []
    status = expected_status(gold)
    allowed_set_ids = expected_set_ids(gold)
    if not predicted:
        if status == "ANSWERED":
            critical_errors.append("missing_citation_for_factual_claim")
            return 0.0, ["missing citations"], critical_errors
        return 0.6, ["refusal lacks searched-section grounding"], critical_errors

    wrong_label_count = 0
    passage_exists_count = 0
    quote_count = 0
    support_count = 0
    expected_pairs = {
        (citation.get("set_id"), citation.get("passage_id"))
        for citation in gold.get("citations") or []
        if isinstance(citation, dict)
    }
    evidence = expected_evidence_text(gold)
    expected_terms = [normalize_text(term) for term in gold.get("expected_terms") or [] if normalize_text(term)]

    for citation in predicted:
        set_id = str(citation.get("set_id", ""))
        passage_id = str(citation.get("passage_id", ""))
        label = labels.get(set_id)
        if set_id not in allowed_set_ids:
            wrong_label_count += 1
            critical_errors.append("citation_from_wrong_label")
            diagnostics.append(f"citation uses wrong set_id: {set_id}")
            continue
        if label is None or passage_id not in label["passages"]:
            diagnostics.append(f"citation passage_id not found: {set_id}/{passage_id}")
            continue
        passage_exists_count += 1
        passage_text = label["passages"][passage_id]
        if quote_in_text(citation.get("supporting_quote", ""), passage_text):
            quote_count += 1
        pair = (set_id, passage_id)
        term_overlap = (
            sum(1 for term in expected_terms if term and term in normalize_text(passage_text)) / len(expected_terms)
            if expected_terms
            else 0.0
        )
        if pair in expected_pairs or token_f1(passage_text, evidence) >= 0.12 or term_overlap >= 0.35:
            support_count += 1

    total = max(1, len(predicted))
    correct_label_score = max(0.0, 1.0 - wrong_label_count / total)
    passage_score = passage_exists_count / total
    quote_score = quote_count / total
    support_score = support_count / total
    score = 0.25 * correct_label_score + 0.25 * passage_score + 0.20 * quote_score + 0.30 * support_score
    if score < 0.95 and "citation uses wrong set_id" not in " ".join(diagnostics):
        diagnostics.append("citations miss expected label, passage, quote, or evidence support")
    return score, diagnostics, sorted(set(critical_errors))


def empty_question_score(gold: dict[str, Any], reason: str, qid_present: float = 0.0) -> dict[str, Any]:
    subscores = {
        "schema": 0.0,
        "qid_present": qid_present,
        "answer_content": 0.0,
        "clinical_qualifiers": 0.0,
        "citation_support": 0.0,
        "refusal_behavior": 0.0,
    }
    score = sum(WEIGHTS[name] * subscores[name] for name in WEIGHTS)
    return {
        "qid": gold["qid"],
        "score": round(score, 6),
        "passed": False,
        "expected_status": expected_status(gold),
        "subscores": subscores,
        "subcriteria": {name: criterion(value, reason) for name, value in subscores.items()},
        "critical_errors": [],
        "diagnostics": [reason],
    }


def score_one(
    answer: dict[str, Any] | None,
    gold: dict[str, Any],
    labels: dict[str, dict[str, Any]],
    qid_set_ok: bool,
) -> dict[str, Any]:
    if answer is None:
        return empty_question_score(gold, "missing answer for qid")

    schema_score, schema_diagnostics = validate_answer_schema(answer)
    if schema_score == 0.0:
        return empty_question_score(gold, "; ".join(schema_diagnostics), qid_present=1.0)

    diagnostics: list[str] = []
    critical_errors: list[str] = []
    content, content_diagnostics, content_critical = content_score(answer, gold)
    qualifiers, qualifier_diagnostics, qualifier_critical = qualifier_score(answer, gold)
    citations, citation_diagnostics, citation_critical = citation_score(answer, gold, labels)
    refusal = 1.0 if answer.get("status") == expected_status(gold) else 0.0
    if refusal == 0.0:
        diagnostics.append("wrong ANSWERED/NOT_FOUND status")
    diagnostics.extend(schema_diagnostics)
    diagnostics.extend(content_diagnostics)
    diagnostics.extend(qualifier_diagnostics)
    diagnostics.extend(citation_diagnostics)
    critical_errors.extend(content_critical)
    critical_errors.extend(qualifier_critical)
    critical_errors.extend(citation_critical)

    subscores = {
        "schema": schema_score,
        "qid_present": 1.0 if qid_set_ok else 0.0,
        "answer_content": content,
        "clinical_qualifiers": qualifiers,
        "citation_support": citations,
        "refusal_behavior": refusal,
    }
    if not qid_set_ok:
        diagnostics.append("missing or extra qids in answer file")
    score = sum(WEIGHTS[name] * subscores[name] for name in WEIGHTS)
    critical_errors = sorted(set(critical_errors))
    return {
        "qid": gold["qid"],
        "score": round(max(0.0, min(1.0, score)), 6),
        "passed": score >= PASS_THRESHOLD and not critical_errors,
        "expected_status": expected_status(gold),
        "subscores": {name: round(value, 6) for name, value in subscores.items()},
        "subcriteria": {
            "schema": criterion(subscores["schema"], "; ".join(schema_diagnostics)),
            "qid_set": criterion(subscores["qid_present"], "missing or extra qids in answer file"),
            "content": criterion(subscores["answer_content"], "; ".join(content_diagnostics)),
            "qualifiers": criterion(subscores["clinical_qualifiers"], "; ".join(qualifier_diagnostics)),
            "citations": criterion(subscores["citation_support"], "; ".join(citation_diagnostics)),
            "refusal": criterion(subscores["refusal_behavior"], "wrong ANSWERED/NOT_FOUND status"),
        },
        "critical_errors": critical_errors,
        "diagnostics": diagnostics,
    }


def score_answers(answers_path: Path, gold_path: Path, labels_path: Path) -> dict[str, Any]:
    gold_rows = load_jsonl(gold_path)
    labels = load_labels(labels_path)
    expected_qids = [str(row["qid"]) for row in gold_rows]
    task_name = os.environ.get("TASK_NAME") or (str(gold_rows[0].get("task", "")) if gold_rows else "")

    def zero_result(error: str, critical: str) -> dict[str, Any]:
        question_scores = [empty_question_score(gold, error) for gold in gold_rows]
        return {
            "fractional_reward": 0.0,
            "aggregate_score": 0.0,
            "overall_fractional_score": 0.0,
            "reward": 0.0,
            "passed": False,
            "binary_pass": False,
            "pass_threshold": PASS_THRESHOLD,
            "critical_errors": [critical],
            "num_questions": len(gold_rows),
            "num_answered": 0,
            "num_missing": len(gold_rows),
            "num_schema_errors": 1,
            "task_name": task_name,
            "schema_errors": [error],
            "question_scores": question_scores,
            "per_question": question_scores,
            "weights": WEIGHTS,
        }

    if not answers_path.exists():
        return zero_result(f"missing required output: {answers_path}", "missing_answers_json")
    try:
        payload = json.loads(answers_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return zero_result(f"invalid JSON: {exc}", "invalid_json_output")

    schema_errors: list[str] = []
    answers = payload.get("answers") if isinstance(payload, dict) else None
    if not isinstance(answers, list):
        schema_errors.append('top-level JSON must contain an "answers" list')
        answers = []

    answers_by_qid: dict[str, dict[str, Any]] = {}
    for idx, answer in enumerate(answers):
        if not isinstance(answer, dict):
            schema_errors.append(f"answers[{idx}] is not an object")
            continue
        qid = answer.get("qid")
        if not isinstance(qid, str):
            schema_errors.append(f"answers[{idx}] has missing or invalid qid")
            continue
        if qid in answers_by_qid:
            schema_errors.append(f"duplicate qid: {qid}")
            continue
        answers_by_qid[qid] = answer

    extra_qids = sorted(set(answers_by_qid) - set(expected_qids))
    missing_qids = sorted(set(expected_qids) - set(answers_by_qid))
    if extra_qids:
        schema_errors.append("unexpected qids: " + ", ".join(extra_qids))
    if missing_qids:
        schema_errors.append("missing qids: " + ", ".join(missing_qids))
    qid_set_ok = not extra_qids and not missing_qids

    question_scores = [score_one(answers_by_qid.get(str(gold["qid"])), gold, labels, qid_set_ok) for gold in gold_rows]
    aggregate = sum(item["score"] for item in question_scores) / len(question_scores) if question_scores else 0.0
    aggregate = round(max(0.0, min(1.0, aggregate)), 6)
    critical_errors = sorted(
        set(
            ["qid_set_mismatch"] if not qid_set_ok else []
        )
        | set(["schema_errors"] if schema_errors else [])
        | {
            error
            for item in question_scores
            for error in item.get("critical_errors", [])
        }
    )
    passed = aggregate >= PASS_THRESHOLD and not critical_errors
    num_schema_errors = len(schema_errors) + sum(1 for item in question_scores if item["subscores"].get("schema", 0.0) < 1.0)
    return {
        "fractional_reward": aggregate,
        "aggregate_score": aggregate,
        "overall_fractional_score": aggregate,
        "reward": aggregate,
        "passed": passed,
        "binary_pass": passed,
        "pass_threshold": PASS_THRESHOLD,
        "critical_errors": critical_errors,
        "num_questions": len(gold_rows),
        "num_answered": len([qid for qid in expected_qids if qid in answers_by_qid]),
        "num_missing": len(missing_qids),
        "num_schema_errors": num_schema_errors,
        "task_name": task_name,
        "schema_errors": schema_errors,
        "question_scores": question_scores,
        "per_question": question_scores,
        "weights": WEIGHTS,
    }


def format_reward(value: float) -> str:
    value = float(value)
    if value == 0.0 or value == 1.0:
        return f"{value:.1f}"
    return f"{value:.6f}".rstrip("0").rstrip(".")


def main() -> None:
    answers_path = Path(os.environ.get("ANSWERS_PATH", "/workspace/answers.json"))
    gold_path = Path(os.environ.get("GOLD_PATH", "/tests/gold.jsonl"))
    labels_path = Path(os.environ.get("LABELS_PATH", "/workspace/data/public/labels.jsonl"))
    logs_dir = Path(os.environ.get("LOGS_DIR", "/logs/verifier"))
    result = score_answers(answers_path, gold_path, labels_path)
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "reward.txt").write_text(format_reward(float(result["fractional_reward"])) + "\n", encoding="utf-8")
    write_json(logs_dir / "reward.json", result)


if __name__ == "__main__":
    main()
