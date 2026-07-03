# Fractional Reward Method

The `fda-hard-*` verifiers now write fractional diagnostic reward to `/logs/verifier/reward.txt`. The value is the aggregate mean of per-question scores on a 0.0 to 1.0 scale, so near-correct failed runs retain useful signal instead of collapsing to binary zero.

Binary pass/fail is still computed in `/logs/verifier/reward.json`:

```text
passed = aggregate_score >= 0.85 and no critical_errors
```

This keeps pass@1 and pass@3 analysis possible while preserving richer reward data for failure analysis. Tools can use either `reward.json["passed"]` or `aggregate_score >= 0.85` with no critical errors.

The scoring rubric is:

- JSON/schema validity: 0.05
- all expected qids present, no extras: 0.05
- answer content correctness: 0.35
- clinical qualifiers included: 0.20
- citation correctness and evidence support: 0.25
- refusal correctness: 0.10

Critical clinical errors force `passed=false` but do not automatically zero fractional reward unless the output is missing or unreadable. Critical errors include invalid JSON, wrong numeric dose/unit/route/population when supplied, hallucinated answers for NOT_FOUND items, citations from the wrong label, missing citations for factual clinical claims, and qid-set mismatches.

The verifier avoids over-strict exact matching by using deterministic normalization, token overlap, token F1, fuzzy string similarity through the standard library, structured numeric checks, and citation evidence checks against public label passages.
