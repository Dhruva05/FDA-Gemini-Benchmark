# FDA Label Factual QA

Answer factual questions from a small set of FDA labels with grounded citations.

Selected label set IDs:
- `03880372-2c68-45c6-a53a-f420c49541d6`
- `8daa5562-824e-476c-9652-26ceef3d4b0e`
- `eaa14195-1b9c-423c-9412-d2fe0857e39d`

Selected questions:
- `737e4762b27ce680` - Milnacipran HCl - factual
- `a4649bc06e063dc2` - EDURANT - factual
- `90eb1b66d90719f8` - Wakix - factual
- `0ed77e51576671d1` - Milnacipran HCl - factual
- `fa2723bf33d48ed3` - EDURANT - factual
- `bf541398e84eb4b1` - Wakix - factual
- `6217f72118af6d67` - Milnacipran HCl - factual
- `bf310eb9af209d12` - EDURANT - factual
- `4fca227a924f7940` - Wakix - factual
- `c8e8afd47cbee25e` - Milnacipran HCl - factual

Gold answers, references, citations, and contexts are under `tests/gold/gold.json` for verifier use only.

Source JSONL files:
- `labels.jsonl`: FDA drug-label documents.
- `qa.jsonl`: gold QA examples used to select questions and hidden verifier gold.
- `qa_toy.jsonl`: small debug subset used to validate the source format.
