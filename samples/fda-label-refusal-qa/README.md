# FDA Label Refusal QA

Refuse unsupported questions instead of hallucinating answers.

Selected label set IDs:
- `029fda33-9df4-465d-8f43-40c61b26bb76`
- `7efed863-919d-458e-99e1-ce0cec95537a`
- `90a69a79-5517-0ccf-e053-2995a90a441f`
- `b7ec6ae7-3d76-42aa-9d8a-fc3e187769b5`

Selected questions:
- `9a1008e377adf183` - Thiothixene - refusal
- `a30bda18d698ff91` - METOPROLOL SUCCINATE - refusal
- `b4f0c8a6bd0bee7d` - Phenelzine Sulfate - refusal
- `00d59a871d79c4fb` - Enalapril Maleate - refusal
- `e60e80c91a147d9c` - Thiothixene - refusal
- `86c54ee3c14791ce` - METOPROLOL SUCCINATE - refusal
- `71640d56831c846f` - Phenelzine Sulfate - refusal
- `5dcea4a72b4c1956` - Enalapril Maleate - refusal
- `97ff81304fe4e697` - Thiothixene - refusal
- `9b50f4ba30f22a23` - METOPROLOL SUCCINATE - refusal

Gold answers, references, citations, and contexts are under `tests/gold/gold.json` for verifier use only.

Source JSONL files:
- `labels.jsonl`: FDA drug-label documents.
- `qa.jsonl`: gold QA examples used to select questions and hidden verifier gold.
- `qa_toy.jsonl`: small debug subset used to validate the source format.
