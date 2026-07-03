#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from score_utils import score_answers_file, write_reward_files


def main() -> None:
    result = score_answers_file(
        answers_path=Path("/root/answers.json"),
        gold_path=Path("/tests/gold/gold.json"),
        labels_dir=Path("/root/data/labels"),
    )
    write_reward_files(result, Path("/logs/verifier"))


if __name__ == "__main__":
    main()
