#!/usr/bin/env python3
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
