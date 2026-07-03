# FDA Hard Gemini Flash Run Comparison

## Technical Summary

These seven Harbor jobs used the same agent/model setting, `terminus-2` with `gemini/gemini-3.5-flash`, but the result files show they are not seven repeats of one exact task. The jobs cover seven distinct `fda-hard-*` task instances: long-label retrieval, warning citations, numeric dosage, near-miss refusal, multisection synthesis, cross-label comparison, and mixed batch.

Across the suite, mean reward was `0.766`, with a wide spread from `0.604` to `0.908`. There were no Harbor exceptions and no verifier schema errors. All agents wrote structurally valid answer files. The main weakness was not execution; it was semantic and clinical precision. Agents frequently validated JSON shape and citation formatting, then declared completion, while the verifier later deducted for low answer-content overlap, missing clinical qualifiers, wrong structured fields, or cross-label citation/support errors.

Only one run passed the task-level binary threshold: `fda-hard-near-miss-refusal__xj7Vzvw` at `0.908333`. The clear failure case was `fda-hard-cross-label-comparison__BCVwLMZ` at `0.603685`, with `0/5` questions passing and broad deductions across content, qualifiers, citations, and one answerable question that was incorrectly refused.

Supporting tables:

| Table | Path |
|---|---|
| Run summary | `metrics/fda_hard_gemini_flash_run_summary.csv` |
| Per-question failures | `metrics/fda_hard_gemini_flash_per_question_failures.csv` |

## Key Findings

| Rank | Timestamp | Task | Run id | Reward | Binary pass | Question pass count | Runtime | Cost USD | Main interpretation |
|---:|---|---|---|---:|---|---:|---:|---:|---|
| 1 | `2026-07-02__18-11-52` | near-miss refusal | `fda-hard-near-miss-refusal__xj7Vzvw` | 0.908333 | true | 4/6 | 156s | 0.474258 | Best and only binary pass; refusal status was strong, with remaining losses in refusal explanation and citation support. |
| 2 | `2026-07-02__18-24-59` | mixed batch | `fda-hard-mixed-batch__JiiW8Am` | 0.791333 | false | 3/10 | 284s | 0.708959 | Efficient and low citation loss, but answer content and qualifiers failed on most answered questions. |
| 3 | `2026-07-02__18-07-47` | numeric dosage | `fda-hard-numeric-dosage__iQvWbhA` | 0.786823 | false | 3/8 | 244s | 0.863243 | Good relative score, but verifier logged critical errors for wrong dose, population, and unit. |
| 4 | `2026-07-02__17-56-14` | long-label retrieval | `fda-hard-long-label-retrieval__FVTUPup` | 0.771979 | false | 2/8 | 480s | 1.393919 | Heaviest successful retrieval run; found material but omitted qualifiers and had content mismatch on every question. |
| 5 | `2026-07-02__18-04-16` | warning citations | `fda-hard-warning-citations__Aqhe6nF` | 0.760261 | false | 1/8 | 210s | 0.649141 | Citation support held up, but all questions lost content credit and 7/8 lost qualifier credit. |
| 6 | `2026-07-02__18-14-29` | multisection synthesis | `fda-hard-multisection-synthesis__eHwzmkS` | 0.739583 | false | 1/8 | 365s | 1.588516 | Most expensive run and most agent steps, but extra verification did not improve semantic/qualifier accuracy. |
| 7 | `2026-07-02__18-20-36` | cross-label comparison | `fda-hard-cross-label-comparison__BCVwLMZ` | 0.603685 | false | 0/5 | 262s | 0.894666 | Worst run; cross-label comparison caused content, qualifier, citation, and refusal-status failures. |

## Failure Criteria

The verifier used a per-question pass threshold of `0.85`. A question can lose partial subcriterion credit and still pass if its final score remains above threshold. The deduction counts below therefore describe observed weakness, not necessarily hard question failure.

| Criterion | Meaning in these rewards | Suite-level pattern |
|---|---|---|
| `content` | Answer content had low semantic overlap with the gold answer. | Most common deduction. Every non-refusal factual/synthesis run lost content credit on every question. |
| `qualifiers` | Clinical qualifiers or structured fields were missing or wrong. | Second main weakness. Numeric dosage and cross-label tasks were especially sensitive to exact dose/unit/population fields. |
| `citations` | Citation missed expected label, passage, quote, or support. | Concentrated in cross-label comparison and a few long-label/synthesis questions. |
| `refusal` | Wrong `ANSWERED`/`NOT_FOUND` status. | Only appeared in cross-label comparison, where one answerable question was refused. |
| `schema` | Output schema issues. | No schema deductions or schema errors were recorded for these seven runs. |

## Run-Level Deductions

| Task | Agent steps | Tool commands | Helper script writes | Content deductions | Qualifier deductions | Citation deductions | Refusal deductions | Critical errors |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| long-label retrieval | 71 | 68 | 5 | 8 | 7 | 2 | 0 | None |
| warning citations | 36 | 30 | 6 | 8 | 7 | 0 | 0 | None |
| numeric dosage | 47 | 39 | 18 | 8 | 5 | 1 | 0 | `wrong_dose`, `wrong_population`, `wrong_unit` |
| near-miss refusal | 24 | 28 | 18 | 0 | 4 | 2 | 0 | None |
| multisection synthesis | 79 | 51 | 7 | 8 | 7 | 2 | 0 | None |
| cross-label comparison | 45 | 47 | 29 | 5 | 5 | 4 | 1 | None |
| mixed batch | 36 | 37 | 1 | 8 | 8 | 1 | 0 | None |

## How The Agents Processed The Runs Differently

**Near-miss refusal was the best fit for this agent/model pair.** The agent used a shorter trace than most runs and did not lose content or refusal-status credit. The remaining deductions were for explanation quality and citations, not for answering when it should refuse. This is the only run whose aggregate score cleared the binary pass threshold.

**Cross-label comparison exposed the biggest reasoning gap.** The agent built the most helper scripts, including many label and dosage inspection scripts, but still failed every question. The run mixed facts across labels poorly enough to trigger 4 citation deductions and 5 qualifier deductions, and it refused one question that the verifier expected to be answered.

**More exploration did not guarantee higher reward.** Multisection synthesis used the most agent steps and the highest cost, yet scored below the less expensive warning-citations and mixed-batch runs. Long-label retrieval was also expensive and slow. In both cases, the agent's internal validation focused on JSON shape, qid coverage, passage IDs, and citation formatting, while the verifier deducted semantic content and clinical qualifier accuracy.

**Numeric dosage looked competitive by reward but had serious precision defects.** It ranked third by score, but the verifier logged `wrong_dose`, `wrong_population`, and `wrong_unit` as critical errors. That matters because a moderately high aggregate score can hide clinically important structured-field mistakes.

**Mixed batch was efficient but still not robust.** The mixed-batch run used one main generation script and had only one citation deduction, making it relatively efficient. Its remaining losses were content and qualifier deductions on 8 of 10 questions, so the weak point was answer exactness, not output production.

## Task-Specific Evaluation

| Task | What worked | What failed |
|---|---|---|
| long-label retrieval | Agent successfully navigated a large Paxlovid label and wrote valid output for all 8 questions. | All 8 questions lost content credit; 7 lost qualifier credit; 2 lost citation support. |
| warning citations | Citation support passed across all 8 questions. | The answers were still too broad or misaligned with gold; content failed on all 8 and qualifiers failed on 7. |
| numeric dosage | Three questions passed, and the run was faster than long-label/multisection. | Exact structured dosage extraction was unreliable, with wrong dose, unit, and population critical errors. |
| near-miss refusal | Correct high-level refusal behavior; no content or refusal-status deductions. | Refusal explanations did not always identify the searched unsupported topic, and two citations missed expected support. |
| multisection synthesis | Output was valid and all questions were answered. | Extra search/validation did not solve synthesis precision; all 8 content deductions and 7 qualifier deductions remained. |
| cross-label comparison | Output was structurally valid and all qids were present. | Lowest reward, no passing questions, high citation/qualifier loss, and one incorrect refusal. |
| mixed batch | Efficient process, no schema errors, only one citation deduction. | Most answered items still missed content and structured clinical qualifiers. |

## Recommended Next Steps

1. Add a hidden-quality proxy before finalization: after schema validation, force a second pass that checks whether each answer includes the expected dose/unit/population/frequency or refusal topic from the public question's `required_output_fields`.
2. For dosage and cross-label tasks, require structured-field extraction from cited passages first, then generate prose from those fields. Do not let prose be the source of truth.
3. For cross-label comparison, validate each label independently before composing the comparison, including separate set IDs, passage IDs, and label-specific qualifiers.
4. For refusal tasks, require the refusal explanation to name both the searched topic and the label section searched, because explanation quality caused most remaining deductions.
5. Treat aggregate reward cautiously for safety-sensitive tasks. The numeric-dosage run scored `0.786823` but still had critical errors in dose, population, and unit.

## Limitations

This analysis uses local Harbor artifacts: `result.json`, `verifier/reward.json`, agent trajectories, and locally available question metadata. The hidden gold answers are not directly available, so content mismatch is interpreted through verifier diagnostics such as "low semantic overlap" and structured-field failure reasons.
