# FDA Label Citation Retrieval

Retrieve relevant FDA label sections and short evidence quotes for each question.

Selected label set IDs:
- `302ae804-37db-44fd-ac2f-3dbdeda9aa4b`
- `a96f5194-ad2a-4783-a9a9-22a288caff25`
- `ab6f3cb3-34a8-4492-a5d7-fb6b055a2d6b`

Selected questions:
- `4c661df7d431bd3c` - SHAROBEL - multihop
- `8547c32761488413` - ERLOTINIB HYDROCHLORIDE - factual
- `a2356cd29e77ae23` - SYMDEKO - factual
- `f1a6997222fd3656` - SHAROBEL - factual
- `86e6f9c97badb426` - ERLOTINIB HYDROCHLORIDE - factual
- `13c273472daead37` - SYMDEKO - factual
- `190721bf5636800a` - SHAROBEL - factual
- `017775054c56f02f` - ERLOTINIB HYDROCHLORIDE - factual
- `7d2efbc4667c7c41` - SYMDEKO - factual
- `c764f432912d70f8` - SHAROBEL - factual

Gold answers, references, citations, and contexts are under `tests/gold/gold.json` for verifier use only.

Source JSONL files:
- `labels.jsonl`: FDA drug-label documents.
- `qa.jsonl`: gold QA examples used to select questions and hidden verifier gold.
- `qa_toy.jsonl`: small debug subset used to validate the source format.
