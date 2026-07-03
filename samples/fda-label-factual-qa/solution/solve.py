#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

NOT_FOUND = 'Information not found!'
REFUSAL_ANSWER = "The requested information is not present in the provided label evidence."


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [value]


def clean_string_list(value):
    cleaned = []
    for item in ensure_list(value):
        if item is None:
            continue
        text = str(item).strip()
        if text and text.lower() != "none":
            cleaned.append(text)
    return cleaned


def oracle_citation_sections(item):
    return clean_string_list(item.get("citations")) or clean_string_list(item.get("references"))


def oracle_cited_section(item):
    sections = oracle_citation_sections(item)
    if sections:
        return "; ".join(sections)
    for context in ensure_list(item.get("context")):
        if isinstance(context, dict):
            return str(context.get("section_title") or context.get("section_label") or "").strip()
    return ""


def first_evidence(contexts):
    for context in ensure_list(contexts):
        if isinstance(context, dict) and context.get("text"):
            text = " ".join(str(context["text"]).split())
            return text[:500]
    return ""


def main() -> None:
    gold_path = Path("/solution/gold.json")
    with gold_path.open(encoding="utf-8") as f:
        gold = json.load(f)
    answers = []
    for item in gold["questions"]:
        is_refusal = str(item.get("answer", "")).strip().lower() == NOT_FOUND.lower()
        if is_refusal:
            answers.append(
                {
                    "question_id": item["question_id"],
                    "answer": REFUSAL_ANSWER,
                    "cited_label": str(item.get("drug_name") or item.get("set_id") or ""),
                    "cited_section": "",
                    "evidence_quote": "",
                    "refusal": True,
                }
            )
        else:
            answers.append(
                {
                    "question_id": item["question_id"],
                    "answer": str(item.get("answer", "")),
                    "cited_label": str(item.get("drug_name") or item.get("set_id") or ""),
                    "cited_section": oracle_cited_section(item),
                    "evidence_quote": first_evidence(item.get("context")),
                    "refusal": False,
                }
            )
    with Path("/root/answers.json").open("w", encoding="utf-8") as f:
        json.dump({"answers": answers}, f, indent=2, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    main()
