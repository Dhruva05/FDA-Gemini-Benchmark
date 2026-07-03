from __future__ import annotations

import json
import math
import re
import string
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

try:  # pragma: no cover - exercised when rapidfuzz is installed in Harbor image.
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - fallback is covered by tests.
    fuzz = None


SCHEMA_FIELDS = {"question_id", "answer", "cited_label", "cited_section", "evidence_quote", "refusal"}
SUBCRITERIA = ("schema", "label", "answer", "section", "evidence")
WEIGHTS = {name: 0.20 for name in SUBCRITERIA}
NOT_FOUND = "Information not found!"
REFUSAL_MARKERS = (
    "not found",
    "not present",
    "not provided",
    "not available",
    "not stated",
    "cannot determine",
    "insufficient",
    "unsupported",
    "does not contain",
    "no information",
)


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.lower().replace("\u00a0", " ")
    text = text.translate(str.maketrans({ch: " " for ch in string.punctuation if ch != "."}))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def compact_normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9.]+", "", normalize_text(value))


def tokens(value: Any) -> list[str]:
    return re.findall(r"[a-z0-9]+(?:\.[a-z0-9]+)?", normalize_text(value))


def token_f1(predicted: Any, gold: Any) -> float:
    pred_tokens = tokens(predicted)
    gold_tokens = tokens(gold)
    if not pred_tokens and not gold_tokens:
        return 1.0
    if not pred_tokens or not gold_tokens:
        return 0.0
    pred_counts: dict[str, int] = {}
    gold_counts: dict[str, int] = {}
    for token in pred_tokens:
        pred_counts[token] = pred_counts.get(token, 0) + 1
    for token in gold_tokens:
        gold_counts[token] = gold_counts.get(token, 0) + 1
    overlap = sum(min(pred_counts.get(token, 0), gold_counts.get(token, 0)) for token in gold_counts)
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred_tokens)
    recall = overlap / len(gold_tokens)
    return 2 * precision * recall / (precision + recall)


def fuzzy_ratio(a: Any, b: Any) -> float:
    a_norm = normalize_text(a)
    b_norm = normalize_text(b)
    if not a_norm and not b_norm:
        return 1.0
    if not a_norm or not b_norm:
        return 0.0
    if fuzz is not None:
        return max(fuzz.ratio(a_norm, b_norm), fuzz.token_set_ratio(a_norm, b_norm)) / 100.0
    return SequenceMatcher(None, a_norm, b_norm).ratio()


def answer_similarity(predicted: Any, gold: Any) -> float:
    gold_norm = normalize_text(gold)
    predicted_norm = normalize_text(predicted)
    if gold_norm == predicted_norm:
        return 1.0
    if gold_norm and (gold_norm in predicted_norm or predicted_norm in gold_norm):
        return 0.92
    return min(1.0, 0.65 * token_f1(predicted_norm, gold_norm) + 0.35 * fuzzy_ratio(predicted_norm, gold_norm))


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [value]


def text_or_empty(value: Any) -> str:
    return "" if value is None else str(value).strip()


def is_blank(value: Any) -> bool:
    return text_or_empty(value) == ""


def is_refusal_gold(item: dict[str, Any]) -> bool:
    return normalize_text(item.get("answer")) == normalize_text(NOT_FOUND)


def looks_like_refusal_answer(value: Any) -> bool:
    text = normalize_text(value)
    if not text:
        return False
    if text == normalize_text(NOT_FOUND):
        return True
    return any(marker in text for marker in REFUSAL_MARKERS)


def extract_section_label(value: Any) -> str:
    text = normalize_text(value)
    match = re.match(r"^(\d+(?:\.\d+)*)\b", text)
    return match.group(1) if match else ""


def section_aliases_from_gold(item: dict[str, Any]) -> list[set[str]]:
    aliases_by_key: dict[str, set[str]] = {}

    def add_alias(raw_value: Any, section_label: str = "") -> None:
        if raw_value is None:
            return
        raw = str(raw_value).strip()
        if not raw:
            return
        label = section_label or extract_section_label(raw)
        key = label or compact_normalize(raw)
        aliases = aliases_by_key.setdefault(key, set())
        aliases.add(compact_normalize(raw))
        if label:
            aliases.add(compact_normalize(label))
            title_without_label = re.sub(r"^\s*" + re.escape(label) + r"\b\s*", "", raw, flags=re.I).strip()
            if title_without_label:
                aliases.add(compact_normalize(title_without_label))
                aliases.add(compact_normalize(f"{label} {title_without_label}"))

    for citation in ensure_list(item.get("citations")):
        add_alias(citation)
    for reference in ensure_list(item.get("references")):
        add_alias(reference)
    for context in ensure_list(item.get("context")):
        if isinstance(context, dict):
            label = str(context.get("section_label") or "").strip()
            add_alias(label, label)
            add_alias(context.get("section_title"), label)

    return [aliases for aliases in aliases_by_key.values() if any(aliases)]


def section_matches(prediction: Any, gold_aliases: set[str]) -> bool:
    pred_norm = compact_normalize(prediction)
    if not pred_norm:
        return False
    if pred_norm in gold_aliases:
        return True
    pred_label = extract_section_label(prediction)
    for alias in gold_aliases:
        alias_label = extract_section_label(alias)
        if pred_label and alias_label and pred_label == alias_label:
            return True
        if len(alias) >= 4 and (alias in pred_norm or pred_norm in alias):
            return True
        if fuzzy_ratio(pred_norm, alias) >= 0.88:
            return True
    return False


def parse_label_metadata(path: Path, text: str) -> dict[str, Any]:
    drug_name = ""
    set_id = ""
    for line in text.splitlines()[:20]:
        if line.startswith("DRUG NAME:"):
            drug_name = line.split(":", 1)[1].strip()
        elif line.startswith("SET ID:"):
            set_id = line.split(":", 1)[1].strip()
    aliases = {path.name, path.stem, path.stem.split("__", 1)[0].replace("_", " ")}
    if drug_name:
        aliases.add(drug_name)
    if set_id:
        aliases.add(set_id)
    return {
        "path": path,
        "text": text,
        "drug_name": drug_name,
        "set_id": set_id,
        "aliases": {compact_normalize(alias) for alias in aliases if str(alias).strip()},
    }


def read_label_files(labels_dir: Path) -> list[dict[str, Any]]:
    if not labels_dir.exists():
        return []
    labels = []
    for path in sorted(labels_dir.glob("*.txt")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        labels.append(parse_label_metadata(path, text))
    return labels


def expected_label_aliases(item: dict[str, Any], label_files: list[dict[str, Any]]) -> set[str]:
    aliases = {
        compact_normalize(item.get("drug_name")),
        compact_normalize(item.get("set_id")),
    }
    set_id = compact_normalize(item.get("set_id"))
    for label in label_files:
        if set_id and compact_normalize(label.get("set_id")) == set_id:
            aliases.update(label["aliases"])
    return {alias for alias in aliases if alias}


def expected_label_files(item: dict[str, Any], label_files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    set_id = compact_normalize(item.get("set_id"))
    matches = [label for label in label_files if set_id and compact_normalize(label.get("set_id")) == set_id]
    return matches or label_files


def find_label_for_prediction(predicted_label: Any, label_files: list[dict[str, Any]]) -> dict[str, Any] | None:
    pred = compact_normalize(predicted_label)
    if not pred:
        return None
    best_label = None
    best_score = 0.0
    for label in label_files:
        for alias in label["aliases"]:
            if pred == alias or (len(alias) >= 4 and (alias in pred or pred in alias)):
                return label
            score = fuzzy_ratio(pred, alias)
            if score > best_score:
                best_score = score
                best_label = label
    return best_label if best_score >= 0.88 else None


def label_match_score(answer: dict[str, Any], item: dict[str, Any], label_files: list[dict[str, Any]]) -> tuple[float, str]:
    predicted = answer.get("cited_label")
    pred = compact_normalize(predicted)
    if not pred:
        return 0.0, "cited_label is empty"
    aliases = expected_label_aliases(item, label_files)
    if not aliases:
        return 0.0, "no expected label metadata available"
    for alias in aliases:
        if pred == alias or (len(alias) >= 4 and (alias in pred or pred in alias)):
            return 1.0, ""
        if fuzzy_ratio(pred, alias) >= 0.88:
            return 1.0, ""
    return 0.0, "cited_label does not match the expected FDA label"


def best_window_similarity(quote: str, source: str) -> float:
    quote_tokens = tokens(quote)
    source_tokens = tokens(source)
    if not quote_tokens or not source_tokens:
        return 0.0
    if len(quote_tokens) <= 4:
        return 1.0 if normalize_text(quote) in normalize_text(source) else 0.0
    window_len = len(quote_tokens)
    stride = max(1, window_len // 3)
    best = 0.0
    for start in range(0, max(1, len(source_tokens) - window_len + 1), stride):
        window = " ".join(source_tokens[start : start + window_len + 5])
        best = max(best, fuzzy_ratio(quote, window), token_f1(quote, window))
        if best >= 0.98:
            return 1.0
    return best


def quote_in_text(quote: str, source: str) -> bool:
    quote_norm = normalize_text(quote)
    source_norm = normalize_text(source)
    if not quote_norm or not source_norm:
        return False
    if quote_norm in source_norm:
        return True
    return best_window_similarity(quote, source) >= 0.85


def gold_evidence_text(item: dict[str, Any]) -> str:
    texts = []
    for context in ensure_list(item.get("context")):
        if isinstance(context, dict) and context.get("text"):
            texts.append(str(context["text"]))
    return "\n".join(texts)


def quote_supports_gold(quote: str, item: dict[str, Any]) -> bool:
    evidence = gold_evidence_text(item)
    if evidence:
        if quote_in_text(quote, evidence):
            return True
        if token_f1(quote, evidence) >= 0.20:
            return True
        if best_window_similarity(quote, evidence) >= 0.65:
            return True
    return token_f1(quote, item.get("answer")) >= 0.35


def schema_validation(
    payload: Any,
    gold_questions: list[dict[str, Any]],
    load_error: str | None = None,
) -> tuple[dict[str, dict[str, Any]], dict[str, tuple[float, str]], list[str]]:
    expected_qids = [str(item["question_id"]) for item in gold_questions]
    per_qid = {qid: (0.0, "missing answer for question_id") for qid in expected_qids}
    answers_by_qid: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    if load_error:
        errors.append(load_error)
        return answers_by_qid, per_qid, errors
    if not isinstance(payload, dict):
        errors.append("top-level JSON must be an object")
        return answers_by_qid, per_qid, errors
    answers = payload.get("answers")
    if not isinstance(answers, list):
        errors.append('top-level JSON must contain an "answers" list')
        return answers_by_qid, per_qid, errors

    expected = set(expected_qids)
    seen: set[str] = set()
    for idx, answer in enumerate(answers):
        if not isinstance(answer, dict):
            errors.append(f"answers[{idx}] is not an object")
            continue
        qid = str(answer.get("question_id", ""))
        if not qid:
            errors.append(f"answers[{idx}] missing question_id")
            continue
        if qid in seen:
            errors.append(f"duplicate answer for {qid}")
            if qid in per_qid:
                per_qid[qid] = (0.0, "duplicate answer for question_id")
            continue
        seen.add(qid)
        if qid not in expected:
            errors.append(f"unexpected answer for {qid}")
            continue

        item_errors = []
        missing = sorted(SCHEMA_FIELDS - set(answer))
        if missing:
            item_errors.append("missing fields: " + ", ".join(missing))
        if "question_id" in answer and not isinstance(answer.get("question_id"), str):
            item_errors.append("question_id must be a string")
        if "answer" in answer and not isinstance(answer.get("answer"), str):
            item_errors.append("answer must be a string")
        if "refusal" in answer and not isinstance(answer.get("refusal"), bool):
            item_errors.append("refusal must be a boolean")
        for field in ("cited_label", "cited_section", "evidence_quote"):
            if field in answer and answer.get(field) is not None and not isinstance(answer.get(field), str):
                item_errors.append(f"{field} must be a string or null")

        if item_errors:
            reason = "; ".join(item_errors)
            per_qid[qid] = (0.0, reason)
            errors.append(f"{qid}: {reason}")
            continue
        answers_by_qid[qid] = answer
        per_qid[qid] = (1.0, "")

    missing_qids = sorted(expected - set(answers_by_qid) - {qid for qid, (score, _) in per_qid.items() if score == 0.0})
    for qid in missing_qids:
        errors.append(f"missing answer for {qid}")
    return answers_by_qid, per_qid, errors


def criterion(score: float, reason: str = "") -> dict[str, Any]:
    score = round(max(0.0, min(1.0, score)), 6)
    return {"score": score, "passed": score >= 1.0, "reason": reason if score < 1.0 else ""}


def score_answer_criterion(answer: dict[str, Any], item: dict[str, Any]) -> tuple[float, str]:
    if is_refusal_gold(item):
        if answer.get("refusal") is True and looks_like_refusal_answer(answer.get("answer")):
            return 1.0, ""
        if answer.get("refusal") is True:
            return 0.4, "refusal answer does not clearly say the information is unsupported"
        return 0.0, "expected a refusal but refusal was false"

    if answer.get("refusal") is True:
        return 0.0, "refused a supported question"
    similarity = answer_similarity(answer.get("answer"), item.get("answer"))
    if similarity >= 0.72:
        return 1.0, ""
    if similarity >= 0.50:
        return similarity, f"answer only partially matches gold answer; similarity={similarity:.3f}"
    return 0.0, f"answer does not match gold answer; similarity={similarity:.3f}"


def score_section_criterion(answer: dict[str, Any], item: dict[str, Any], correct_refusal: bool) -> tuple[float, str]:
    predicted = answer.get("cited_section")
    if is_refusal_gold(item):
        if correct_refusal and is_blank(predicted):
            return 1.0, ""
        if correct_refusal:
            return 0.0, "refusal fabricated a cited_section"
        return 0.0, "incorrect refusal behavior"

    if is_blank(predicted):
        return 0.0, "cited_section is empty"
    aliases = section_aliases_from_gold(item)
    if not aliases:
        return 1.0, ""
    if any(section_matches(predicted, alias_group) for alias_group in aliases):
        return 1.0, ""
    return 0.0, "cited_section does not match expected FDA label section"


def score_evidence_criterion(
    answer: dict[str, Any],
    item: dict[str, Any],
    label_files: list[dict[str, Any]],
    correct_refusal: bool,
) -> tuple[float, str]:
    quote = text_or_empty(answer.get("evidence_quote"))
    if is_refusal_gold(item):
        if correct_refusal and not quote:
            return 1.0, ""
        if correct_refusal:
            return 0.0, "refusal fabricated evidence_quote"
        return 0.0, "incorrect refusal behavior"

    if not quote:
        return 0.0, "evidence_quote is empty"

    cited_label = find_label_for_prediction(answer.get("cited_label"), label_files)
    candidate_labels = [cited_label] if cited_label is not None else expected_label_files(item, label_files)
    if not any(quote_in_text(quote, label["text"]) for label in candidate_labels):
        return 0.0, "evidence_quote is not found in the cited FDA label text"
    if not quote_supports_gold(quote, item):
        return 0.0, "evidence_quote does not overlap the gold supporting evidence"
    return 1.0, ""


def empty_subcriteria(schema_score: float, schema_reason: str) -> dict[str, dict[str, Any]]:
    return {
        "schema": criterion(schema_score, schema_reason),
        "label": criterion(0.0, "no valid answer object to score"),
        "answer": criterion(0.0, "no valid answer object to score"),
        "section": criterion(0.0, "no valid answer object to score"),
        "evidence": criterion(0.0, "no valid answer object to score"),
    }


def score_submission(
    payload: Any,
    gold: dict[str, Any],
    labels_dir: Path,
    load_error: str | None = None,
) -> dict[str, Any]:
    gold_questions = list(gold.get("questions", []))
    label_files = read_label_files(labels_dir)

    if not gold_questions:
        return {
            "overall_reward": 0.0,
            "reward": 0.0,
            "per_question": [],
            "schema_errors": ["gold file contains no questions"],
            "weights": WEIGHTS,
        }

    answers_by_qid, schema_by_qid, schema_errors = schema_validation(payload, gold_questions, load_error=load_error)
    per_question = []

    for item in gold_questions:
        qid = str(item["question_id"])
        schema_score, schema_reason = schema_by_qid.get(qid, (0.0, "missing answer for question_id"))
        answer = answers_by_qid.get(qid)
        if answer is None:
            subcriteria = empty_subcriteria(schema_score, schema_reason)
        else:
            label_score, label_reason = label_match_score(answer, item, label_files)
            answer_score, answer_reason = score_answer_criterion(answer, item)
            correct_refusal = is_refusal_gold(item) and answer_score >= 1.0 and answer.get("refusal") is True
            section_score, section_reason = score_section_criterion(answer, item, correct_refusal)
            evidence_score, evidence_reason = score_evidence_criterion(answer, item, label_files, correct_refusal)
            subcriteria = {
                "schema": criterion(schema_score, schema_reason),
                "label": criterion(label_score, label_reason),
                "answer": criterion(answer_score, answer_reason),
                "section": criterion(section_score, section_reason),
                "evidence": criterion(evidence_score, evidence_reason),
            }

        score = sum(WEIGHTS[name] * subcriteria[name]["score"] for name in SUBCRITERIA)
        per_question.append(
            {
                "question_id": qid,
                "score": round(score, 6),
                "gold_refusal": is_refusal_gold(item),
                "subcriteria": subcriteria,
            }
        )

    overall = sum(item["score"] for item in per_question) / len(per_question)
    if math.isnan(overall):
        overall = 0.0
    overall = round(max(0.0, min(1.0, overall)), 6)
    return {
        "overall_reward": overall,
        "reward": overall,
        "per_question": per_question,
        "schema_errors": schema_errors,
        "weights": WEIGHTS,
    }


def score_answers_file(answers_path: Path, gold_path: Path, labels_dir: Path) -> dict[str, Any]:
    gold = load_json(gold_path)
    try:
        payload = load_json(answers_path)
    except FileNotFoundError:
        return score_submission(None, gold, labels_dir, load_error=f"missing required output: {answers_path}")
    except json.JSONDecodeError as exc:
        return score_submission(None, gold, labels_dir, load_error=f"invalid JSON: {exc}")
    return score_submission(payload, gold, labels_dir)


def write_reward_files(result: dict[str, Any], logs_dir: Path = Path("/logs/verifier")) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "reward.txt").write_text(str(float(result["overall_reward"])), encoding="utf-8")
    write_json(logs_dir / "reward.json", result)
