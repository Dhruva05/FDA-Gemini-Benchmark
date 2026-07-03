# FDA Label Multihop QA

Answer questions that require combining evidence from at least two FDA label sections.

Selected label set IDs:
- `323351d8-de18-4cd6-9497-c2d5e8666414`
- `8c2340e4-2b42-45dc-8fac-9960e8172547`
- `90d09714-a8b1-4696-8ada-f99dc54d0721`

Selected questions:
- `1d735c9c9780ebea` - LAMPIT - multihop
- `3cdf0b5cec5c6d24` - Gastrografin - multihop
- `b5e7075815e89dc0` - Afeditab - multihop
- `a5827467adc0fc81` - LAMPIT - multihop
- `acb65491fd5ede93` - Gastrografin - multihop
- `7e378745d57dacec` - Afeditab - multihop
- `58b99352bb4d2c8c` - LAMPIT - multihop
- `3f905c7ce3d6b057` - Afeditab - multihop

Gold answers, references, citations, and contexts are under `tests/gold/gold.json` for verifier use only.

Source JSONL files:
- `labels.jsonl`: FDA drug-label documents.
- `qa.jsonl`: gold QA examples used to select questions and hidden verifier gold.
- `qa_toy.jsonl`: small debug subset used to validate the source format.
