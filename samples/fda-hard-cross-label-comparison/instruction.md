        # FDA Hard Cross-Label Comparison

        You are given public FDA label data and public questions. Use only `/workspace/data/public`.
        Do not use external medical knowledge, web search, package documentation, hidden tests, or assumptions not grounded in the labels.

        Files:
        - `/workspace/data/public/labels.jsonl`: full FDA labels with `label_raw`, `chunks`, `set_id`, and `drug_name`.
        - `/workspace/data/public/questions.jsonl`: 5 public questions. This file intentionally does not contain answers, references, citations, context, or gold passage text.
        - `/workspace/data/public/README.md`: short data description.

        Task:
        Compare dosing and safety facts across labels without transferring facts between products.

        Write `/workspace/answers.json` with exactly this schema:

        ```json
        {
  "answers": [
    {
      "qid": "string",
      "status": "ANSWERED|NOT_FOUND",
      "answer": "string",
      "citations": [
        {
          "set_id": "string",
          "passage_id": "string",
          "section": "string or null",
          "supporting_quote": "short quote from label"
        }
      ],
      "structured_fields": {
        "...": "task-specific fields"
      }
    }
  ]
}
        ```

        Rules:
        - Answer every `qid` exactly once, with no extra qids.
        - For answerable questions, set `status` to `ANSWERED`.
        - For refusal questions, set `status` to `NOT_FOUND` when the requested information is unsupported by the label.
        - Every factual claim must have at least one citation.
        - Each citation must use a `set_id` from the relevant label and a real `PASSAGE_####` passage ID from that same label.
        - `supporting_quote` must be a short quote copied from the cited passage.
        - Do not cite a passage from the wrong label.
        - Use `structured_fields` for the fields named in each public question's `required_output_fields`.
        - Output must be valid JSON and must be written to `/workspace/answers.json`.
