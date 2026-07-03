# FDA Label Citation Retrieval

You are given FDA drug label text files and a batch question file. Use only the files in `/root/data`.
Do not use external knowledge, web search, package documentation, or medical assumptions not grounded in the labels.
Read all FDA label files under `/root/data/labels/` that are relevant to the batch, then read `/root/data/questions.json`.

Keep prose answers short; the main objective is retrieving the relevant label, section, and evidence quote.

Files:
- `/root/data/questions.json`: questions to answer.
- `/root/data/labels/*.txt`: FDA label text. Section headings and passage IDs are included in the files.
- `/root/data/output_schema.json`: required JSON structure.
- `/root/data/source_manifest.json`: provenance for the FDA source JSONL files used to generate this task.

Write `/root/answers.json` with this exact shape:

```json
{
  "answers": [
    {
      "question_id": "qid from questions.json",
      "answer": "answer supported by the labels",
      "cited_label": "FDA label or drug name used as evidence",
      "cited_section": "section ID or section title from the cited label",
      "evidence_quote": "short quote copied or closely copied from the cited label",
      "refusal": false
    }
  ]
}
```

Rules:
- Answer every question exactly once.
- Use the `question_id` values from `questions.json`.
- Set `refusal` to `true` only when the label does not support an answer.
- When refusing, set `answer` to a concise explanation that the requested information is not present in the provided label evidence.
- When refusing, set `cited_label` to the relevant label if applicable, and set `cited_section` and `evidence_quote` to `null` or `""`.
- When not refusing, `cited_label` must identify the FDA label or drug name used as evidence.
- When not refusing, `cited_section` must identify the FDA label section that supports the answer.
- Keep `evidence_quote` short and make sure it appears in the cited FDA label file.
- Do not cite every section; cite only the section that supports the answer.
