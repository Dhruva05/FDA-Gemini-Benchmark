# FDA Hard Gemini Flash Trajectory Failure Analysis

## Technical Summary

I reviewed the trajectories for all 21 jobs in the pasted Harbor output: three batches of the seven `fda-hard-*` tasks run with `terminus-2` and `gemini/gemini-3.5-flash`.

The failures mostly occur after the agent has already found relevant label material. The recurring failure point is the transition from retrieved evidence to `/workspace/answers.json`: agents generated schema-valid JSON, then ran local validation scripts that checked qid coverage, JSON shape, passage IDs, and quote existence, but did not validate semantic answer overlap, exact dose/unit/population fields, clinical qualifiers, or whether a selected citation was the expected supporting passage.

Across 159 scored questions, only 41 passed. There were no schema deductions. The dominant verifier deductions were `content` and `qualifiers`, which map to final answer synthesis and structured-field extraction, not file production. Cross-label comparison is the exception: it also failed during label-specific extraction and citation selection, with 0/15 questions passing across the three runs.

Supporting trajectory tables:

| Table | Path |
|---|---|
| 21-run trajectory summary | `metrics/fda_hard_gemini_flash_trajectory_summary_21_runs.csv` |
| Failure events by run and criterion | `metrics/fda_hard_gemini_flash_trajectory_failure_events_21_runs.csv` |
| Per-question failure-to-step mapping | `metrics/fda_hard_gemini_flash_trajectory_question_failures_21_runs.csv` |

## Scope And Step Definitions

The review covers these timestamp ranges from the attachment:

| Batch | Timestamps |
|---:|---|
| 1 | `2026-07-02__17-56-14` through `2026-07-02__18-24-59` |
| 2 | `2026-07-02__19-19-02` through `2026-07-02__19-43-51` |
| 3 | `2026-07-02__19-50-34` through `2026-07-02__20-30-20` |

Step locations in this report refer to `agent/trajectory.json` step IDs:

| Term | Meaning |
|---|---|
| Retrieval range | Steps where the agent inspected questions, labels, chunks, passages, or generated search/extraction scripts before final answer writing. |
| Generation steps | Steps whose commands wrote, generated, or directly inspected `/workspace/answers.json`. |
| Post-generation validation steps | Steps after answer generation that checked JSON, qids, citations, quotes, required fields, or schema-like properties. |
| Response parse errors | Harness-level invalid JSON responses from the agent, usually from unescaped newlines/control characters in its command-batch response. |
| Terminal errors | Observable command/runtime errors such as `Traceback` or `SyntaxError`. |

## The Main Failure Is A Validation Gap After Answer Generation

The agents usually performed a reasonable command-line workflow: inspect `questions.jsonl`, inspect or search `labels.jsonl`, write helper scripts, generate `/workspace/answers.json`, then validate the file. The weakness is that their validation was local and structural. It did not test the hidden verifier's core requirements.

Suite-level deductions across 21 trajectories:

| Verifier criterion | Total deductions | Where it occurs in the trajectory |
|---|---:|---|
| `content` | 135 | Final answer synthesis/generation. Agents compressed label text into broad prose that did not match expected answer content. |
| `qualifiers` | 133 | Structured fields and clinical qualifier extraction. Failures were encoded when writing `answers.json`, then missed by local validators. |
| `citations` | 33 | Citation selection during retrieval and final generation. Validators often checked that citations existed, not that they were the expected support. |
| `refusal` | 2 | Final `ANSWERED`/`NOT_FOUND` status assignment in cross-label comparison. |
| `schema` | 0 | Output production was structurally successful across all 21 jobs. |

This is why many trajectories ended with agent messages saying the answer file was valid, fully checked, or complete, while verifier rewards still failed.

## Task-Level Failure Locations

| Task | Avg reward | Question passes | Main trajectory failure location | Evidence from trajectory/reward |
|---|---:|---:|---|---|
| `fda-hard-long-label-retrieval` | 0.753177 | 4/24 | Late answer compression after long retrieval. | 24 content and 21 qualifier deductions; generation happened late in each run after many Paxlovid passage searches. |
| `fda-hard-warning-citations` | 0.741858 | 4/24 | Answer wording and qualifier synthesis, not citation discovery. | 24 content and 21 qualifier deductions; only 2 citation deductions across three runs. |
| `fda-hard-numeric-dosage` | 0.800955 | 7/24 | Structured dosage extraction during answer generation. | Every run had `wrong_dose`, `wrong_population`, and `wrong_unit` critical errors despite valid JSON. |
| `fda-hard-near-miss-refusal` | 0.897222 | 12/18 | Refusal explanation/citation support, not status selection. | No content or refusal-status deductions; 14 qualifier and 6 citation deductions. |
| `fda-hard-multisection-synthesis` | 0.750503 | 4/24 | Multi-section synthesis into answer text and qualifiers. | 24 content and 21 qualifier deductions; extra validation did not catch semantic mismatch. |
| `fda-hard-cross-label-comparison` | 0.623517 | 0/15 | Label-specific extraction and final comparison assembly. | 15 content, 15 qualifier, 11 citation, and 2 refusal deductions; worst task family. |
| `fda-hard-mixed-batch` | 0.801903 | 10/30 | Mixed answerable-item synthesis and qualifiers. | 24 content and 24 qualifier deductions; low citation loss shows evidence IDs were less of the problem. |

## Per-Run Step Map

| Batch | Task | Timestamp | Run id | Reward | Q pass | Generation steps | Post-gen validation | Parse errors | Terminal errors | Where the failure occurs |
|---:|---|---|---|---:|---:|---|---|---:|---:|---|
| 1 | long-label retrieval | `17-56-14` | `FVTUPup` | 0.771979 | 2/8 | `61,63,69,71` | `61-71` | 23 | 3 | Answer generation fixed quote formatting but still produced broad Paxlovid answers missing qualifiers. |
| 1 | warning citations | `18-04-16` | `Aqhe6nF` | 0.760261 | 1/8 | `33,34,35` | `33-35` | 9 | 1 | Retrieval found warning passages; final summaries missed expected content/qualifier exactness. |
| 1 | numeric dosage | `18-07-47` | `iQvWbhA` | 0.786823 | 3/8 | `45,46` | `45,46` | 11 | 2 | Structured dosage fields were assembled incorrectly; validator did not check dose/unit/population correctness. |
| 1 | near-miss refusal | `18-11-52` | `xj7Vzvw` | 0.908333 | 4/6 | `20,21,22` | `20-23` | 0 | 2 | Status decisions were mostly correct; losses came from refusal explanation and citation support. |
| 1 | multisection synthesis | `18-14-29` | `eHwzmkS` | 0.739583 | 1/8 | `74,76,78` | `74-78` | 30 | 2 | Long exploration and quote validation did not solve synthesis/qualifier mismatch. |
| 1 | cross-label comparison | `18-20-36` | `BCVwLMZ` | 0.603685 | 0/5 | `42,43,44` | `42-44` | 1 | 1 | Label-specific comparison facts and citations were wrong; one answerable question was refused. |
| 1 | mixed batch | `18-24-59` | `JiiW8Am` | 0.791333 | 3/10 | `34,35` | `34,35` | 3 | 1 | Efficient final generation, but answerable items still missed content and qualifiers. |
| 2 | long-label retrieval | `19-19-02` | `4DjA8ii` | 0.741302 | 1/8 | `36,37,38` | `36-38` | 1 | 2 | Faster generation than batch 1, but same content/qualifier failure pattern. |
| 2 | warning citations | `19-22-17` | `hqyTKGf` | 0.715990 | 1/8 | `37,44,46,48,49,51,53` | `37-53` | 17 | 3 | Repeated regeneration/validation still failed answer content and qualifiers. |
| 2 | numeric dosage | `19-25-58` | `LiXMXER` | 0.781354 | 2/8 | `56,57,58,60` | `57-61` | 21 | 17 | Many command/runtime corrections preceded final output; final structured fields still had wrong dose/unit/population. |
| 2 | near-miss refusal | `19-31-29` | `m5Usye5` | 0.891667 | 4/6 | `27,28,29` | `27-29` | 0 | 2 | Refusal status held; explanation qualifiers and citations lost credit. |
| 2 | multisection synthesis | `19-34-12` | `LYGG2eU` | 0.721302 | 1/8 | `44,47,48,49` | `44-49` | 0 | 2 | Output generation and repair occurred, but semantic synthesis stayed weak. |
| 2 | cross-label comparison | `19-39-12` | `Bx9w5TV` | 0.573649 | 0/5 | `44,45,46,48,49` | `44-49` | 14 | 1 | Worst cross-label run; final comparison included missing citation support and one wrong status decision. |
| 2 | mixed batch | `19-43-51` | `9YYwSZw` | 0.791333 | 3/10 | `32,33,34` | `32-34` | 0 | 2 | Same mixed-batch pattern: schema-valid output, content/qualifier misses on answerable questions. |
| 3 | long-label retrieval | `19-50-34` | `yima5xz` | 0.746250 | 1/8 | `50,52,55,57` | `50-57` | 24 | 2 | Multiple final answer rewrites fixed structure but not hidden answer/qualifier criteria. |
| 3 | warning citations | `19-56-28` | `UBgAL8V` | 0.749323 | 2/8 | `30,31,32,33,34,35` | `30,32-35` | 0 | 2 | Faster trace with fewer parser errors; still failed content/qualifier exactness and added citation loss. |
| 3 | numeric dosage | `19-59-41` | `XNTfrCD` | 0.834687 | 2/8 | `45,51,53,55` | `45-56` | 22 | 2 | Best numeric run by reward, but critical structured-field errors persisted. |
| 3 | near-miss refusal | `20-04-55` | `8omc965` | 0.891667 | 4/6 | `20,21,22,24` | `20-23` | 2 | 2 | Refusal logic remained strong; explanation/citation quality capped the score. |
| 3 | multisection synthesis | `20-07-41` | `KinvK49` | 0.790625 | 2/8 | `54,56,58` | `54-58` | 23 | 0 | Best synthesis run; citation support improved, but content/qualifier misses remained universal. |
| 3 | cross-label comparison | `20-12-21` | `upmmwVs` | 0.693216 | 0/5 | `13,62,63,64,65,66,67` | `62-67` | 9 | 1 | Better cross-label reward, but no question passed; errors remained in comparison content, qualifiers, and citations. |
| 3 | mixed batch | `20-30-20` | `crQahni` | 0.823042 | 4/10 | `29,30,31` | `29-31` | 1 | 0 | Best mixed run; generation was compact, but content/qualifier deductions still hit 8 answerable items. |

## Failure Patterns From The Trajectories

**1. The agents repeatedly over-trusted local validation.** Validation scripts were useful for JSON shape and citation existence, but the verifier failures were about whether the answer and structured fields were clinically exact. This gap appears in every task except schema, where there were no deductions.

**2. Content failures usually appeared at final synthesis, not initial retrieval.** Long-label, warning, multisection, and mixed-batch trajectories show extensive label inspection before answer generation. The failure is that the final prose omitted expected terms or qualifiers, so the verifier recorded low semantic overlap.

**3. Numeric dosage failures were clinically material.** All three numeric-dosage runs had critical errors for `wrong_dose`, `wrong_population`, and `wrong_unit`. These occur at the structured-field construction step, after the agent had inspected dosage passages.

**4. Cross-label comparison failed earlier and more broadly.** Unlike warning citations, where citations mostly passed, cross-label runs failed citation support on 11/15 questions and never passed a question. This points to a retrieval/extraction problem before final writing: the agent did not preserve label-specific facts and support tightly enough when comparing two products.

**5. Response parse errors wasted steps but were not the primary scoring failure.** Some low-scoring runs had many invalid JSON response errors, especially long-label, numeric, and multisection trajectories. But near-miss refusal scored highest with few parse errors, and mixed batch scored relatively well with compact generation. The protocol errors increased noise and runtime, but the main reward losses were semantic.

## Recommended Fixes

1. Add a post-generation verifier proxy that checks answer content against extracted required facts, not just schema. For FDA hard tasks, the validator should inspect dose, unit, frequency, population, max daily dose, unsupported topic, and label-specific comparison fields.
2. Force structured extraction before prose. For dosage and cross-label tasks, build `structured_fields` from cited passage snippets first, then generate the natural-language answer from those fields.
3. For cross-label comparison, validate each product independently before comparison: set_id, passage_id, dose/strength, route, frequency, population, max daily dose, and quote support.
4. For refusal tasks, require the answer to name the searched unsupported topic and cite the passage/section searched. The status was usually correct; the explanation was not specific enough.
5. Penalize or retry local validations that only prove the answer file is syntactically valid. The agent's "all checks passed" state should require semantic checks aligned to task-specific fields.

## Limitations

This review uses observable trajectory artifacts: commands, generated scripts, terminal observations, and verifier rewards. It does not assume access to hidden gold answers beyond verifier diagnostics. Step locations identify where the bad answer, citation, or status was likely introduced in the trajectory; they are not proof of the agent's internal intent.
