# FDA Label Mixed Batch

Handle factual, multihop, and refusal examples across multiple FDA labels.

Selected label set IDs:
- `211ef2da-2868-4a77-8055-1cb2cd78e24b`
- `4cfeb8bd-143e-4dd7-bc34-b0bcda02460d`
- `52ab8ee9-a04d-4e27-b0f4-eb050f144715`
- `5e5926a7-1de0-4b54-a5c0-286b6200ff82`
- `6e8d8c4f-96eb-4b64-9c8c-4a5448a23a78`
- `af8cdd37-8fd0-4651-ae03-36c7d4863301`
- `d7432a48-1142-431e-997f-8419dc724824`
- `da47ad78-e62c-4bf3-9b53-d8cc246bcfb6`
- `eb368bb6-80e3-4df9-8a85-91df0a2ada6a`
- `ef9977cb-ec91-46d7-b769-d26decfd6fe7`
- `f81dfaeb-46d5-47ce-9ef6-19259f5ac61c`
- `fa952140-c9f6-472d-a04f-96c44fe9bca8`

Selected questions:
- `8deb7244393e0d52` - Gleevec - factual
- `739131cb82d5b99f` - Aripiprazole - factual
- `35831321fd8697bf` - DOJOLVI - factual
- `07ca0b446e87521d` - Saxagliptin - factual
- `cfc17e2708ae22c7` - Nifediac CC - multihop
- `899ed79b8912519b` - ERIVEDGE - multihop
- `1d76aa504be07852` - lamivudine - multihop
- `6acdb9ab4fa3321a` - cevimeline hydrochloride - multihop
- `6765cb9daa9ecf8d` - Guardian Loratadine - refusal
- `dc22aa2ba20c74fa` - Sandimmune - refusal
- `2332e9b9b4f206d5` - Eszopiclone - refusal
- `541f5d9c6e2bd551` - ORLISTAT - refusal

Gold answers, references, citations, and contexts are under `tests/gold/gold.json` for verifier use only.

Source JSONL files:
- `labels.jsonl`: FDA drug-label documents.
- `qa.jsonl`: gold QA examples used to select questions and hidden verifier gold.
- `qa_toy.jsonl`: small debug subset used to validate the source format.
