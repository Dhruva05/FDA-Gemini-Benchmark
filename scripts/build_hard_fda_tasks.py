#!/usr/bin/env python3
"""Build harder FDA-label Harbor tasks with public questions and hidden gold."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import stat
import string
import textwrap
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


NOT_FOUND = "Information not found!"
BASE_OUTPUT_FIELDS = ["qid", "status", "answer", "citations", "structured_fields"]
FORBIDDEN_PUBLIC_FIELDS = {"answer", "references", "citations", "context", "gold_passages", "expected_terms"}
PASSAGE_RE = re.compile(r"\|\|PASSAGE_(\d{4})\|\|")
STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "also",
    "and",
    "are",
    "associated",
    "before",
    "been",
    "being",
    "between",
    "can",
    "could",
    "does",
    "dose",
    "drug",
    "during",
    "each",
    "from",
    "have",
    "how",
    "into",
    "label",
    "may",
    "not",
    "patients",
    "provided",
    "should",
    "stated",
    "that",
    "the",
    "their",
    "there",
    "this",
    "use",
    "used",
    "what",
    "when",
    "where",
    "which",
    "with",
}


class Family:
    def __init__(
        self,
        slug: str,
        title: str,
        task_type: str,
        default_count: int,
        description: str,
        required_fields: list[str],
    ) -> None:
        self.slug = slug
        self.title = title
        self.task_type = task_type
        self.default_count = default_count
        self.description = description
        self.required_fields = required_fields


FAMILIES = [
    Family(
        "fda-hard-long-label-retrieval",
        "FDA Hard Long-Label Retrieval",
        "factual",
        8,
        "Find facts buried in long FDA labels and cite exact passage IDs.",
        BASE_OUTPUT_FIELDS,
    ),
    Family(
        "fda-hard-warning-citations",
        "FDA Hard Citation-Grounded Warning Extraction",
        "factual",
        8,
        "Extract clinically relevant warnings, precautions, risks, and safety qualifiers with multiple citations.",
        BASE_OUTPUT_FIELDS,
    ),
    Family(
        "fda-hard-numeric-dosage",
        "FDA Hard Numeric Dosage Precision",
        "numeric",
        8,
        "Recover precise dosage, unit, route, frequency, population, and max-dose facts without mixing labels.",
        BASE_OUTPUT_FIELDS
        + [
            "structured_fields.dose",
            "structured_fields.unit",
            "structured_fields.route",
            "structured_fields.frequency",
            "structured_fields.population",
            "structured_fields.max_daily_dose",
            "structured_fields.citation_passages",
        ],
    ),
    Family(
        "fda-hard-near-miss-refusal",
        "FDA Hard Near-Miss Refusal",
        "refusal",
        6,
        "Refuse adjacent but unsupported dose or safety claims while citing the relevant searched section.",
        BASE_OUTPUT_FIELDS + ["structured_fields.searched_topic", "structured_fields.unsupported_topic"],
    ),
    Family(
        "fda-hard-multisection-synthesis",
        "FDA Hard Multi-Section Synthesis",
        "multihop",
        8,
        "Synthesize claims across two or more FDA label sections, with each claim grounded in citations.",
        BASE_OUTPUT_FIELDS,
    ),
    Family(
        "fda-hard-cross-label-comparison",
        "FDA Hard Cross-Label Comparison",
        "mixed",
        5,
        "Compare dosing and safety facts across labels without transferring facts between products.",
        BASE_OUTPUT_FIELDS + ["structured_fields.comparison"],
    ),
    Family(
        "fda-hard-mixed-batch",
        "FDA Hard Mixed Batch",
        "mixed",
        10,
        "Handle factual, multihop, refusal, numeric, citation, and comparison questions in one answer file.",
        BASE_OUTPUT_FIELDS,
    ),
]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(row)
    return rows


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
        fh.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            json.dump(row, fh, sort_keys=True)
            fh.write("\n")


def ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [value]


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value).lower().replace("\u00a0", " ")
    text = text.translate(str.maketrans({ch: " " for ch in string.punctuation if ch not in {".", "%"}}))
    return re.sub(r"\s+", " ", text).strip()


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


def stable_id(*parts: Any, prefix: str = "qid") -> str:
    digest = hashlib.sha1("||".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:14]
    return f"{prefix}-{digest}"


def task_kind(row: dict[str, Any]) -> str:
    for key in ("task", "question_type", "qfilter_category"):
        value = row.get(key)
        if isinstance(value, str) and value.strip() and value.strip().upper() != "NA":
            return value.strip().lower()
    return "other"


def is_refusal(row: dict[str, Any]) -> bool:
    return task_kind(row) == "refusal" or normalize_text(row.get("answer")) == normalize_text(NOT_FOUND)


def is_numericish(row: dict[str, Any]) -> bool:
    text = f"{row.get('question', '')} {row.get('answer', '')} {row.get('references', '')}".lower()
    if task_kind(row) == "numeric":
        return True
    return bool(re.search(r"\b\d+(?:\.\d+)?\s*(mg|mcg|g|ml|units?|tablets?|capsules?)\b", text)) and any(
        term in text for term in ("dose", "dosage", "administer", "take", "daily", "hour", "oral", "intravenous", "topical")
    )


def is_safetyish(row: dict[str, Any]) -> bool:
    text = f"{row.get('question', '')} {row.get('answer', '')} {row.get('references', '')}".lower()
    return any(term in text for term in ("warning", "precaution", "risk", "adverse", "contraindication", "pregnan", "lactation", "interaction", "impairment"))


def label_chunk_count(row: dict[str, Any], label_by_set_id: dict[str, dict[str, Any]]) -> int:
    return len(ensure_list(label_by_set_id.get(str(row.get("set_id", "")), {}).get("chunks")))


def passage_id(index: int) -> str:
    return f"PASSAGE_{index:04d}"


def passage_section(context: dict[str, Any] | None, fallback_text: str = "") -> str | None:
    if context:
        label = str(context.get("section_label") or "").strip()
        title = str(context.get("section_title") or "").strip()
        if label and title:
            return f"{label} {title}"
        if label:
            return label
        if title:
            return title
    first_line = next((line.strip() for line in fallback_text.splitlines() if line.strip()), "")
    return first_line[:80] if first_line else None


def short_quote(text: Any, max_words: int = 45) -> str:
    words = re.findall(r"\S+", "" if text is None else str(text).replace("\n", " "))
    return " ".join(words[:max_words])


def best_chunk_index(needle: str, chunks: list[str]) -> int:
    if not chunks:
        return 0
    best_index = 0
    best_score = -1.0
    for index, chunk in enumerate(chunks):
        score = token_f1(needle, chunk)
        if normalize_text(needle) and normalize_text(needle) in normalize_text(chunk):
            score += 0.5
        if score > best_score:
            best_index = index
            best_score = score
    return best_index


def citation_from_chunk(label: dict[str, Any], index: int, context: dict[str, Any] | None = None) -> dict[str, Any]:
    chunks = [str(chunk) for chunk in ensure_list(label.get("chunks"))]
    text = chunks[index] if 0 <= index < len(chunks) else str(label.get("label_raw", ""))
    return {
        "set_id": str(label.get("set_id", "")),
        "passage_id": passage_id(index),
        "section": passage_section(context, text),
        "supporting_quote": short_quote(text),
    }


def citations_for_row(row: dict[str, Any], label: dict[str, Any]) -> list[dict[str, Any]]:
    chunks = [str(chunk) for chunk in ensure_list(label.get("chunks"))]
    citations: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for context in ensure_list(row.get("context")):
        if not isinstance(context, dict):
            continue
        index_value = context.get("doc_chunk_index")
        if isinstance(index_value, int) and 0 <= index_value < len(chunks):
            index = index_value
        else:
            index = best_chunk_index(str(context.get("text", "")), chunks)
        citation = citation_from_chunk(label, index, context)
        key = (citation["set_id"], citation["passage_id"])
        if key not in seen:
            citations.append(citation)
            seen.add(key)
    if not citations and chunks:
        index = best_chunk_index(f"{row.get('question', '')} {row.get('answer', '')}", chunks)
        citations.append(citation_from_chunk(label, index))
    return citations


def extract_expected_terms(answer: Any, context_rows: list[Any], limit: int = 12) -> list[str]:
    source = f"{answer} " + " ".join(str(item.get("text", "")) for item in context_rows if isinstance(item, dict))
    counts = Counter(token for token in tokens(source) if len(token) > 3 and token not in STOPWORDS)
    return [token for token, _ in counts.most_common(limit)]


def dosage_structured_fields(text: Any) -> dict[str, Any]:
    value = "" if text is None else str(text)
    lower = value.lower()
    dose_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|units?|tablet(?:s)?|capsule(?:s)?)\b", lower)
    max_match = re.search(r"(?:do not exceed|not exceed|maximum daily dose is|maximum(?: of)?)[^.;,\n]*?(\d+(?:\.\d+)?)\s*(mg|mcg|g|ml|units?|tablet(?:s)?|capsule(?:s)?)", lower)
    frequency_match = re.search(r"\b(every\s+\d+\s+hours?|once daily|twice daily|three times daily|daily|bid|tid|qid)\b", lower)
    route_terms = ["orally", "oral", "by mouth", "intravenous", "subcutaneous", "topically", "topical", "injection", "inhalation"]
    population_terms = ["adults", "adult", "children", "pediatric", "patients", "elderly", "renal impairment", "hepatic impairment"]
    return {
        "dose": dose_match.group(1) if dose_match else "",
        "unit": dose_match.group(2) if dose_match else "",
        "route": next((term for term in route_terms if term in lower), ""),
        "frequency": frequency_match.group(1) if frequency_match else "",
        "population": next((term for term in population_terms if term in lower), ""),
        "max_daily_dose": max_match.group(0) if max_match else "",
        "citation_passages": [],
    }


def public_question(gold: dict[str, Any]) -> dict[str, Any]:
    item = {
        "qid": gold["qid"],
        "set_id": gold["set_id"],
        "drug_name": gold["drug_name"],
        "task_type": gold["task_type"],
        "question": gold["question"],
        "required_output_fields": gold["required_output_fields"],
    }
    if "comparison_set_ids" in gold:
        item["comparison_set_ids"] = gold["comparison_set_ids"]
    leaked = FORBIDDEN_PUBLIC_FIELDS.intersection(item)
    if leaked:
        raise ValueError(f"public question leaks hidden fields: {sorted(leaked)}")
    return item


def gold_from_qa(row: dict[str, Any], family: Family, label_by_set_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    label = label_by_set_id[str(row["set_id"])]
    contexts = ensure_list(row.get("context"))
    citations = citations_for_row(row, label)
    structured_fields = dosage_structured_fields(row.get("answer")) if family.task_type == "numeric" or is_numericish(row) else {}
    if structured_fields:
        structured_fields["citation_passages"] = [citation["passage_id"] for citation in citations]
    status = "NOT_FOUND" if is_refusal(row) else "ANSWERED"
    return {
        "qid": str(row.get("qid") or stable_id(row.get("set_id"), row.get("question"))),
        "set_id": str(row.get("set_id", "")),
        "drug_name": str(row.get("drug_name") or label.get("drug_name") or ""),
        "task_type": family.task_type if family.task_type != "mixed" else task_kind(row),
        "task": family.slug,
        "question": str(row.get("question", "")),
        "answer": str(row.get("answer", "")),
        "status": status,
        "citations": citations if status == "ANSWERED" else [],
        "references": ensure_list(row.get("references")),
        "context": contexts,
        "required_output_fields": family.required_fields,
        "expected_terms": extract_expected_terms(row.get("answer"), contexts),
        "structured_fields": structured_fields,
    }


def build_near_miss_refusals(labels: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    patterns = [
        ("renal impairment", "severe hepatic impairment", "renal impairment dose adjustment"),
        ("pregnancy", "breastfeeding dose adjustment", "pregnancy safety information"),
        ("warnings", "pharmacogenomic testing requirement", "warnings and precautions"),
        ("contraindications", "dose adjustment after bariatric surgery", "contraindications"),
        ("adverse reactions", "therapeutic drug monitoring target range", "adverse reactions"),
        ("pediatric", "geriatric maximum cumulative lifetime dose", "pediatric use"),
    ]
    rows: list[dict[str, Any]] = []
    for label in labels:
        chunks = [str(chunk) for chunk in ensure_list(label.get("chunks"))]
        combined = normalize_text(" ".join(chunks))
        for anchor, unsupported, searched_topic in patterns:
            if anchor not in combined or unsupported in combined:
                continue
            index = best_chunk_index(anchor, chunks)
            citation = citation_from_chunk(label, index)
            drug = str(label.get("drug_name") or label.get("drug_id") or label.get("set_id"))
            qid = stable_id(label.get("set_id"), anchor, unsupported, prefix="near-miss")
            rows.append(
                {
                    "qid": qid,
                    "set_id": str(label.get("set_id", "")),
                    "drug_name": drug,
                    "task_type": "refusal",
                    "task": "fda-hard-near-miss-refusal",
                    "question": (
                        f"The {drug} label discusses {anchor}. Does it provide a supported recommendation for "
                        f"{unsupported}? Answer NOT_FOUND if the label does not support it, and cite the section you searched."
                    ),
                    "answer": NOT_FOUND,
                    "status": "NOT_FOUND",
                    "citations": [citation],
                    "references": [],
                    "context": [
                        {
                            "section_title": citation["section"],
                            "text": citation["supporting_quote"],
                            "doc_chunk_index": index,
                            "has_answer": False,
                        }
                    ],
                    "required_output_fields": FAMILIES[3].required_fields,
                    "expected_terms": [token for token in tokens(f"{searched_topic} {unsupported}") if token not in STOPWORDS][:10],
                    "structured_fields": {
                        "searched_topic": searched_topic,
                        "unsupported_topic": unsupported,
                    },
                }
            )
            if len(rows) >= count:
                return rows
    return rows


def dosage_chunk(label: dict[str, Any]) -> tuple[int, str] | None:
    chunks = [str(chunk) for chunk in ensure_list(label.get("chunks"))]
    ranked = []
    for index, chunk in enumerate(chunks):
        lower = chunk.lower()
        if any(term in lower for term in ("dosage", "recommended", "take", "administer", "apply")) and re.search(
            r"\b\d+(?:\.\d+)?\s*(mg|mcg|g|ml|units?|tablet|capsule)", lower
        ):
            ranked.append((index, chunk))
    if ranked:
        return ranked[0]
    return None


def build_cross_label_questions(labels: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    candidates = [(label, dosage_chunk(label)) for label in labels]
    candidates = [(label, chunk) for label, chunk in candidates if chunk is not None]
    rows: list[dict[str, Any]] = []
    for i in range(0, max(0, len(candidates) - 1), 2):
        label_a, chunk_a = candidates[i]
        label_b, chunk_b = candidates[i + 1]
        index_a, text_a = chunk_a
        index_b, text_b = chunk_b
        drug_a = str(label_a.get("drug_name") or label_a.get("drug_id") or label_a.get("set_id"))
        drug_b = str(label_b.get("drug_name") or label_b.get("drug_id") or label_b.get("set_id"))
        set_ids = [str(label_a.get("set_id", "")), str(label_b.get("set_id", ""))]
        qid = stable_id("cross", *set_ids, i, prefix="cross")
        citations = [citation_from_chunk(label_a, index_a), citation_from_chunk(label_b, index_b)]
        rows.append(
            {
                "qid": qid,
                "set_id": "comparison:" + ":".join(set_ids),
                "comparison_set_ids": set_ids,
                "drug_name": f"{drug_a} vs {drug_b}",
                "task_type": "mixed",
                "task": "fda-hard-cross-label-comparison",
                "question": (
                    f"Compare the dosing instructions for {drug_a} and {drug_b}. For each label, report dose or strength, "
                    "route, frequency, population, and maximum daily dose if stated. Cite one passage from each label."
                ),
                "answer": f"{drug_a}: {short_quote(text_a, 60)} {drug_b}: {short_quote(text_b, 60)}",
                "status": "ANSWERED",
                "citations": citations,
                "references": [],
                "context": [
                    {"section_title": citations[0]["section"], "text": text_a, "doc_chunk_index": index_a, "has_answer": True},
                    {"section_title": citations[1]["section"], "text": text_b, "doc_chunk_index": index_b, "has_answer": True},
                ],
                "required_output_fields": FAMILIES[5].required_fields,
                "expected_terms": extract_expected_terms(f"{text_a} {text_b}", [], limit=16),
                "structured_fields": {"comparison": {drug_a: dosage_structured_fields(text_a), drug_b: dosage_structured_fields(text_b)}},
            }
        )
        if len(rows) >= count:
            return rows
    return rows


def unique_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for row in rows:
        qid = str(row.get("qid") or stable_id(row.get("set_id"), row.get("question")))
        if qid in seen:
            continue
        seen.add(qid)
        unique.append(row)
    return unique


def take_rows(rows: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    rows = unique_rows(rows)
    if len(rows) >= count:
        return rows[:count]
    if not rows:
        return []
    expanded = list(rows)
    index = 0
    while len(expanded) < count:
        copy = dict(rows[index % len(rows)])
        copy["qid"] = f"{copy.get('qid', stable_id(copy.get('question')))}-repeat-{len(expanded)}"
        expanded.append(copy)
        index += 1
    return expanded


def rank_by_hardness(row: dict[str, Any], label_by_set_id: dict[str, dict[str, Any]]) -> tuple[int, int, int, int]:
    contexts = len(ensure_list(row.get("context")))
    citations = len(ensure_list(row.get("citations"))) + len(ensure_list(row.get("references")))
    return (contexts + citations, contexts, label_chunk_count(row, label_by_set_id), len(tokens(row.get("answer"))))


def select_qa_rows(
    labels: list[dict[str, Any]],
    qa_rows: list[dict[str, Any]],
    family: Family,
    count: int,
    label_by_set_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    answerable = [row for row in qa_rows if not is_refusal(row) and str(row.get("set_id", "")) in label_by_set_id]
    if family.slug == "fda-hard-long-label-retrieval":
        rows = sorted(answerable, key=lambda row: (label_chunk_count(row, label_by_set_id), rank_by_hardness(row, label_by_set_id)), reverse=True)
    elif family.slug == "fda-hard-warning-citations":
        rows = sorted([row for row in answerable if is_safetyish(row)], key=lambda row: rank_by_hardness(row, label_by_set_id), reverse=True)
    elif family.slug == "fda-hard-numeric-dosage":
        rows = sorted([row for row in answerable if is_numericish(row)], key=lambda row: rank_by_hardness(row, label_by_set_id), reverse=True)
    elif family.slug == "fda-hard-multisection-synthesis":
        rows = sorted(
            [row for row in answerable if task_kind(row) == "multihop" or len(ensure_list(row.get("context"))) >= 2],
            key=lambda row: rank_by_hardness(row, label_by_set_id),
            reverse=True,
        )
    else:
        rows = sorted(answerable, key=lambda row: rank_by_hardness(row, label_by_set_id), reverse=True)
    if len(rows) < count:
        rows.extend(row for row in answerable if row not in rows)
    return take_rows(rows, count)


def fallback_refusal_rows(
    qa_rows: list[dict[str, Any]],
    count: int,
    family: Family,
    label_by_set_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = [row for row in qa_rows if is_refusal(row) and str(row.get("set_id", "")) in label_by_set_id]
    rows = take_rows(rows, count)
    return [gold_from_qa(row, family, label_by_set_id) for row in rows]


def selected_labels_for_gold(gold_rows: list[dict[str, Any]], label_by_set_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    set_ids: list[str] = []
    for row in gold_rows:
        if "comparison_set_ids" in row:
            set_ids.extend(str(item) for item in row["comparison_set_ids"])
        elif str(row.get("set_id", "")).startswith("comparison:"):
            continue
        else:
            set_ids.append(str(row.get("set_id", "")))
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for set_id in set_ids:
        if set_id in seen or set_id not in label_by_set_id:
            continue
        seen.add(set_id)
        unique.append(label_by_set_id[set_id])
    return unique


def clear_task_dir(path: Path, overwrite: bool) -> None:
    if path.exists() and overwrite:
        if not path.name.startswith("fda-hard-"):
            raise ValueError(f"refusing to overwrite non-generated task directory: {path}")
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def render_instruction(family: Family, public_count: int) -> str:
    schema = {
        "answers": [
            {
                "qid": "string",
                "status": "ANSWERED|NOT_FOUND",
                "answer": "string",
                "citations": [
                    {
                        "set_id": "string",
                        "passage_id": "string",
                        "section": "string or null",
                        "supporting_quote": "short quote from label",
                    }
                ],
                "structured_fields": {"...": "task-specific fields"},
            }
        ]
    }
    return textwrap.dedent(
        f"""\
        # {family.title}

        You are given public FDA label data and public questions. Use only `/workspace/data/public`.
        Do not use external medical knowledge, web search, package documentation, hidden tests, or assumptions not grounded in the labels.

        Files:
        - `/workspace/data/public/labels.jsonl`: full FDA labels with `label_raw`, `chunks`, `set_id`, and `drug_name`.
        - `/workspace/data/public/questions.jsonl`: {public_count} public questions. This file intentionally does not contain answers, references, citations, context, or gold passage text.
        - `/workspace/data/public/README.md`: short data description.

        Task:
        {family.description}

        Write `/workspace/answers.json` with exactly this schema:

        ```json
        {json.dumps(schema, indent=2)}
        ```

        Rules:
        - Answer every `qid` exactly once, with no extra qids.
        - For answerable questions, set `status` to `ANSWERED`.
        - For refusal questions, set `status` to `NOT_FOUND` when the requested information is unsupported by the label.
        - Every factual claim must have at least one citation.
        - Each citation must use a `set_id` from the relevant label and a real `PASSAGE_####` passage ID from that same label.
        - `supporting_quote` must be a short quote copied from the cited passage.
        - Do not cite a passage from the wrong label.
        - Use `structured_fields` for the fields named in each public question's `required_output_fields`.
        - Output must be valid JSON and must be written to `/workspace/answers.json`.
        """
    )


def render_task_toml(family: Family) -> str:
    return textwrap.dedent(
        f"""\
        version = "1.0"

        [task]
        name = "abundant/{family.slug}"
        description = "{family.description}"
        keywords = ["fda", "drug-labels", "rag", "long-context", "citations", "refusal", "clinical", "heterogeneous-data"]

        [[task.authors]]
        name = "Abundant"
        email = ""

        [metadata]
        author_name = "Abundant"
        author_email = ""
        difficulty = "hard"
        category = "clinical-regulatory-rag"
        tags = ["fda", "drug-labels", "rag", "long-context", "citations", "refusal", "clinical", "heterogeneous-data"]

        [verifier]
        timeout_sec = 900.0

        [agent]
        timeout_sec = 900.0

        [environment]
        build_timeout_sec = 600.0
        cpus = 1
        memory_mb = 4096
        storage_mb = 10240

        [environment.env]
        GEMINI_CLI_TRUST_WORKSPACE = "true"
        """
    )


DOCKERFILE = """\
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \\
    python3 \\
    python3-pip \\
    python3-venv \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY data /workspace/data
"""


TEST_SH = """\
#!/bin/bash
set -e

mkdir -p /logs/verifier
python3 /tests/verify.py
exit 0
"""


SOLVE_SH = """\
#!/bin/bash
set -e

python3 /solution/solve.py
"""


SOLVE_PY = r'''#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


def load_jsonl(path: Path):
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def main() -> None:
    gold_path = Path(os.environ.get("GOLD_PATH", "/solution/gold.jsonl"))
    answers_path = Path(os.environ.get("ANSWERS_PATH", "/workspace/answers.json"))
    answers_path.parent.mkdir(parents=True, exist_ok=True)
    answers = []
    for item in load_jsonl(gold_path):
        answers.append(
            {
                "qid": item["qid"],
                "status": item.get("status", "ANSWERED"),
                "answer": item.get("answer", ""),
                "citations": item.get("citations", []),
                "structured_fields": item.get("structured_fields", {}),
            }
        )
    with answers_path.open("w", encoding="utf-8") as fh:
        json.dump({"answers": answers}, fh, indent=2, sort_keys=True)
        fh.write("\n")


if __name__ == "__main__":
    main()
'''


def verifier_template_text() -> str:
    shared_path = Path(__file__).resolve().parent / "fda_fractional_verifier.py"
    return shared_path.read_text(encoding="utf-8")


def write_text(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def render_public_readme(family: Family, labels: list[dict[str, Any]], question_count: int) -> str:
    label_lines = "\n".join(f"- {label.get('drug_name')} (`{label.get('set_id')}`)" for label in labels)
    return textwrap.dedent(
        f"""\
        # Public FDA Label Data

        This directory contains only public task inputs for `{family.slug}`.

        - `labels.jsonl` has full FDA label rows with `label_raw` and `chunks`.
        - `questions.jsonl` has {question_count} public questions.
        - Gold answers, references, citations, and curated context are not included here.

        Labels included:
        {label_lines}
        """
    )


def build_family_task(
    family: Family,
    gold_rows: list[dict[str, Any]],
    output_root: Path,
    label_by_set_id: dict[str, dict[str, Any]],
    overwrite: bool,
) -> Path:
    task_dir = output_root / family.slug
    clear_task_dir(task_dir, overwrite)
    public_rows = [public_question(row) for row in gold_rows]
    labels = selected_labels_for_gold(gold_rows, label_by_set_id)

    write_text(task_dir / "instruction.md", render_instruction(family, len(public_rows)))
    write_text(task_dir / "task.toml", render_task_toml(family))
    write_text(task_dir / "environment" / "Dockerfile", DOCKERFILE)
    write_jsonl(task_dir / "data" / "public" / "labels.jsonl", labels)
    write_jsonl(task_dir / "data" / "public" / "questions.jsonl", public_rows)
    write_text(task_dir / "data" / "public" / "README.md", render_public_readme(family, labels, len(public_rows)))
    write_jsonl(task_dir / "environment" / "data" / "public" / "labels.jsonl", labels)
    write_jsonl(task_dir / "environment" / "data" / "public" / "questions.jsonl", public_rows)
    write_text(
        task_dir / "environment" / "data" / "public" / "README.md",
        render_public_readme(family, labels, len(public_rows)),
    )
    write_jsonl(task_dir / "tests" / "gold.jsonl", gold_rows)
    write_text(task_dir / "tests" / "verify.py", verifier_template_text(), executable=True)
    write_text(task_dir / "tests" / "test.sh", TEST_SH, executable=True)
    write_jsonl(task_dir / "solution" / "gold.jsonl", gold_rows)
    write_text(task_dir / "solution" / "solve.py", SOLVE_PY, executable=True)
    write_text(task_dir / "solution" / "solve.sh", SOLVE_SH, executable=True)
    return task_dir


def build_tasks(
    labels_path: Path,
    qa_path: Path,
    output_root: Path,
    questions_per_task: int | None = None,
    overwrite: bool = False,
) -> list[Path]:
    labels = read_jsonl(labels_path)
    qa_rows = read_jsonl(qa_path)
    label_by_set_id = {str(label.get("set_id", "")): label for label in labels}
    output_root.mkdir(parents=True, exist_ok=True)

    gold_by_family: dict[str, list[dict[str, Any]]] = {}
    for family in FAMILIES:
        count = questions_per_task if questions_per_task is not None else family.default_count
        if family.slug == "fda-hard-near-miss-refusal":
            rows = build_near_miss_refusals(labels, count)
            if len(rows) < count:
                rows.extend(fallback_refusal_rows(qa_rows, count - len(rows), family, label_by_set_id))
            gold_by_family[family.slug] = take_rows(rows, count)
        elif family.slug == "fda-hard-cross-label-comparison":
            rows = build_cross_label_questions(labels, count)
            gold_by_family[family.slug] = take_rows(rows, count)
        elif family.slug == "fda-hard-mixed-batch":
            continue
        else:
            selected = select_qa_rows(labels, qa_rows, family, count, label_by_set_id)
            gold_by_family[family.slug] = [gold_from_qa(row, family, label_by_set_id) for row in selected]

    mixed_count = questions_per_task if questions_per_task is not None else FAMILIES[-1].default_count
    mixed_candidates: list[dict[str, Any]] = []
    for family in FAMILIES[:-1]:
        mixed_candidates.extend(gold_by_family.get(family.slug, [])[:2])
    mixed_rows = []
    seen: set[str] = set()
    for row in mixed_candidates:
        qid = str(row["qid"])
        if qid in seen:
            row = dict(row)
            row["qid"] = stable_id("mixed", qid, len(mixed_rows), prefix="mixed")
        seen.add(str(row["qid"]))
        row = dict(row)
        row["task"] = "fda-hard-mixed-batch"
        if "required_output_fields" not in row:
            row["required_output_fields"] = FAMILIES[-1].required_fields
        mixed_rows.append(row)
        if len(mixed_rows) >= mixed_count:
            break
    gold_by_family["fda-hard-mixed-batch"] = take_rows(mixed_rows, mixed_count)

    task_dirs: list[Path] = []
    for family in FAMILIES:
        rows = gold_by_family.get(family.slug, [])
        if not rows:
            raise ValueError(f"could not build any questions for {family.slug}")
        task_dirs.append(build_family_task(family, rows, output_root, label_by_set_id, overwrite))
    return task_dirs


def default_paths() -> tuple[Path, Path, Path]:
    repo_root = Path(__file__).resolve().parents[1]
    data_root = repo_root.parent
    return data_root / "labels.jsonl", data_root / "qa.jsonl", repo_root / "samples"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    labels_path, qa_path, output_root = default_paths()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--labels", type=Path, default=labels_path)
    parser.add_argument("--qa", type=Path, default=qa_path)
    parser.add_argument("--output-root", type=Path, default=output_root)
    parser.add_argument("--questions-per-task", type=int, default=None)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    task_dirs = build_tasks(
        labels_path=args.labels,
        qa_path=args.qa,
        output_root=args.output_root,
        questions_per_task=args.questions_per_task,
        overwrite=args.overwrite,
    )
    for task_dir in task_dirs:
        print(task_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
