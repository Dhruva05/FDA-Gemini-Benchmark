# FDA Label Refusal QA Run Comparison

## Technical Summary

`fda-label-refusal-qa__G3JUbXQ` passed completely with reward `1.000`. `fda-label-refusal-qa__2Wak4wq` partially passed with reward `0.844`, and `fda-label-refusal-qa__Hxj5VAf` partially passed with reward `0.792`. None of the three runs had schema errors or run-level exceptions.

All three agents correctly inferred that all ten questions were hidden-gold refusals. The score split came from answer phrasing, not from choosing supported answers or fabricating citations. `G3JUbXQ` used one explicit refusal template for every question: the provided FDA label "does not contain any information" about the requested topic. The two partial runs generated customized refusal explanations; some of those custom answers used variants such as "does not mention," "does not specify," or "does not indicate," which are semantically reasonable but not recognized by the verifier's refusal-marker list.

## Run Overview

| Metric | `fda-label-refusal-qa__G3JUbXQ` | `fda-label-refusal-qa__2Wak4wq` | `fda-label-refusal-qa__Hxj5VAf` |
|---|---:|---:|---:|
| Job folder | `logs/2026-07-02__11-26-30` | `logs/2026-07-02__12-04-06` | `logs/2026-07-02__12-57-32` |
| Overall reward | `1.000` | `0.844` | `0.792` |
| Fully passing questions | `10 / 10` | `7 / 10` | `6 / 10` |
| Failed questions | `0` | `3` | `4` |
| Agent episodes | `21` | `13` | `9` |
| Agent execution time | `82.573s` | `62.221s` | `53.844s` |
| Total run wall time | `251.238s` | `82.567s` | `73.953s` |
| Input tokens | `242,135` | `170,292` | `91,716` |
| Cached tokens | `52,729` | `65,168` | `32,603` |
| Output tokens | `7,567` | `7,477` | `7,906` |
| Cost | `$0.3601` | `$0.2348` | `$0.1647` |
| Run-level exception | `None` | `None` | `None` |
| Schema errors | `[]` | `[]` | `[]` |

## Processing Differences

| Area | `G3JUbXQ` | `2Wak4wq` | `Hxj5VAf` | Impact |
|---|---|---|---|---|
| Initial exploration | Listed `/root/data`, listed labels, then read questions and schema. | Listed `/root/data`, read questions and schema, then listed labels. | Listed `/root/data`, listed labels, then read questions and schema. | All three found the same four labels, questions, and output schema. |
| Label review strategy | Used broad keyword searches, then targeted boolean checks per label/question concept. | Wrote a structured keyword-search script that matched each question to a label and printed snippets; reran broader and targeted scripts after truncated output. | Wrote keyword-search and question-check scripts; mapped each drug to a label file and printed found keyword lists for each question. | The partial runs gathered more detailed snippets, but all questions were gold refusals, so final wording mattered more than evidence detail. |
| Refusal decision | Confirmed all ten questions were unsupported after checking missing concepts such as G6PD, D-dimer, QTc, INR, and thyroid terms. | Also confirmed all ten were unsupported, including partial term matches such as pregnancy or hepatic references that did not support the requested combined facts. | Also treated all ten questions as refusals after finding only partial topic overlap and no support for the requested facts. | No substantive decision difference: all three chose `refusal: true` for every question. |
| Answer generation | Generated every answer from one template: `The provided FDA label for {drug} does not contain any information regarding the requested topic.` | Generated per-question custom explanations with `if/elif` branches. | Generated per-question custom explanations with `if/elif` branches. | The uniform template was safest for the scorer. Custom phrasing introduced three failures in `2Wak4wq` and four in `Hxj5VAf`. |
| Validation approach | Tried `jsonschema`; initial package install failed under PEP 668, then installed with `--break-system-packages` and validated successfully. | Used manual schema validation when `jsonschema` was unavailable; no package install needed. | First imported `jsonschema` and hit `ModuleNotFoundError`, then rewrote the script with manual validation. | All final files were structurally valid; validation issues only affected execution path, not schema score. |
| Final output | All answers had `refusal: true`, correct `cited_label`, and blank `cited_section`/`evidence_quote`. | Same structure and labels. | Same structure and labels. | Structural, label, and schema criteria passed across all three runs. |

## Failure Breakdown

The verifier defines refusal recognition with a fixed marker list: `not found`, `not present`, `not provided`, `not available`, `not stated`, `cannot determine`, `insufficient`, `unsupported`, `does not contain`, and `no information`.

For refusal gold items, an answer only counts as a correct refusal if `refusal` is `true` and the answer text contains one of those markers. If that answer criterion fails, the section and evidence criteria also fail as "incorrect refusal behavior," even when `cited_section` and `evidence_quote` are correctly blank.

| Run | Failed question | Drug | Answer phrasing | Score | Failed subcriteria | Why it failed |
|---|---|---|---|---:|---|---|
| `2Wak4wq` | `b4f0c8a6bd0bee7d` | Phenelzine Sulfate | "does not mention or advise any monitoring protocols..." | `0.48` | answer `0.4`, section `0.0`, evidence `0.0` | The phrase lacks an exact scorer marker such as "does not contain" or "not found." |
| `2Wak4wq` | `e60e80c91a147d9c` | Thiothixene | "does not mention or specify a QTc interval cutoff..." | `0.48` | answer `0.4`, section `0.0`, evidence `0.0` | Same marker mismatch: "does not mention" is not in the refusal-marker list. |
| `2Wak4wq` | `5dcea4a72b4c1956` | Enalapril Maleate | "does not indicate or contain information suggesting..." | `0.48` | answer `0.4`, section `0.0`, evidence `0.0` | It has "contain information" but not the contiguous marker "does not contain"; no other marker matched. |
| `Hxj5VAf` | `e60e80c91a147d9c` | Thiothixene | "does not mention a QTc interval cutoff..." | `0.48` | answer `0.4`, section `0.0`, evidence `0.0` | "Does not mention" is not a recognized refusal marker. |
| `Hxj5VAf` | `86c54ee3c14791ce` | METOPROLOL SUCCINATE | "does not specify an INR cutoff..." | `0.48` | answer `0.4`, section `0.0`, evidence `0.0` | "Does not specify" is not a recognized refusal marker. |
| `Hxj5VAf` | `71640d56831c846f` | Phenelzine Sulfate | "does not indicate the need for dose modifications..." | `0.48` | answer `0.4`, section `0.0`, evidence `0.0` | "Does not indicate" is not a recognized refusal marker. |
| `Hxj5VAf` | `5dcea4a72b4c1956` | Enalapril Maleate | "does not indicate that the drug requires dosage alterations..." | `0.48` | answer `0.4`, section `0.0`, evidence `0.0` | Same marker mismatch: no accepted refusal marker appears. |

The arithmetic matches the reported rewards. `2Wak4wq` has seven fully correct questions plus three `0.48` questions: `(7.0 + 3 * 0.48) / 10 = 0.844`. `Hxj5VAf` has six fully correct questions plus four `0.48` questions: `(6.0 + 4 * 0.48) / 10 = 0.792`.

## Per-Question Result Table

| Question ID | Drug | Topic | `G3JUbXQ` | `2Wak4wq` | `Hxj5VAf` | Failure mode |
|---|---|---|---:|---:|---:|---|
| `9a1008e377adf183` | Thiothixene | severe hepatic impairment plus thyroid dysfunction dosage | `1.00` | `1.00` | `1.00` | None |
| `a30bda18d698ff91` | METOPROLOL SUCCINATE | G6PD deficiency plus abnormal thyroid function dose alteration | `1.00` | `1.00` | `1.00` | None |
| `b4f0c8a6bd0bee7d` | Phenelzine Sulfate | D-dimer monitoring protocol in geriatric patients | `1.00` | `0.48` | `1.00` | `2Wak4wq`: missing scorer-recognized refusal marker |
| `00d59a871d79c4fb` | Enalapril Maleate | thyroid dysfunction plus severe hepatic impairment dose modification | `1.00` | `1.00` | `1.00` | None |
| `e60e80c91a147d9c` | Thiothixene | QTc cutoff for commencing therapy in pregnant females | `1.00` | `0.48` | `0.48` | Both partial runs: missing scorer-recognized refusal marker |
| `86c54ee3c14791ce` | METOPROLOL SUCCINATE | INR cutoff for severe hepatic impairment | `1.00` | `1.00` | `0.48` | `Hxj5VAf`: missing scorer-recognized refusal marker |
| `71640d56831c846f` | Phenelzine Sulfate | thyroid dysfunction plus severe hepatic impairment dose modification | `1.00` | `1.00` | `0.48` | `Hxj5VAf`: missing scorer-recognized refusal marker |
| `5dcea4a72b4c1956` | Enalapril Maleate | G6PD deficiency plus thyroid abnormality dosage alteration | `1.00` | `0.48` | `0.48` | Both partial runs: missing scorer-recognized refusal marker |
| `97ff81304fe4e697` | Thiothixene | G6PD deficiency plus thyroid dysfunction dose modification | `1.00` | `1.00` | `1.00` | None |
| `9b50f4ba30f22a23` | METOPROLOL SUCCINATE | thyroid dysfunction plus severe hepatic impairment dose modification | `1.00` | `1.00` | `1.00` | None |

## Execution Issues Observed

| Run | Issue | Recovery | Scoring impact |
|---|---|---|---|
| `G3JUbXQ` | The agent had recovered JSON-response formatting mistakes before answer generation and validation. One validation script response also contained an invalid escaped `\with` line. | It regenerated the script and proceeded. | No verifier penalty; only extra episodes/tokens. |
| `G3JUbXQ` | `pip install jsonschema` failed because the Python environment was externally managed under PEP 668. | It reran installation with `--break-system-packages`; schema validation then succeeded. | No verifier penalty; increased wall time and cost. |
| `2Wak4wq` | One agent response had a JSON parsing issue from unescaped newlines during exploration. | It reran the next command cleanly. | No direct verifier penalty. |
| `2Wak4wq` | Final answer wording used scorer-unrecognized refusal variants for three questions. | Not recovered before submission. | Caused the `0.844` reward. |
| `Hxj5VAf` | The first generation script imported `jsonschema`, which was not installed in the container. | It rewrote the script to use manual validation and completed successfully. | No direct verifier penalty. |
| `Hxj5VAf` | Final answer wording used scorer-unrecognized refusal variants for four questions. | Not recovered before submission. | Caused the `0.792` reward. |

## Recommended Fix

For this task family, use a canonical refusal sentence that contains a verifier-recognized marker, for example:

`The provided FDA label for {drug} does not contain information supporting the requested answer.`

Avoid relying on variants like "does not mention," "does not specify," or "does not indicate" unless they also include an exact marker such as "not found," "not present," "unsupported," "does not contain," or "no information."

## Source Artifacts Reviewed

- `FDA_question_review/logs/2026-07-02__11-26-30/fda-label-refusal-qa__G3JUbXQ/result.json`
- `FDA_question_review/logs/2026-07-02__11-26-30/fda-label-refusal-qa__G3JUbXQ/verifier/reward.json`
- `FDA_question_review/logs/2026-07-02__11-26-30/fda-label-refusal-qa__G3JUbXQ/agent/trajectory.json`
- `FDA_question_review/logs/2026-07-02__11-26-30/fda-label-refusal-qa__G3JUbXQ/agent/terminus_2.pane`
- `FDA_question_review/logs/2026-07-02__12-04-06/fda-label-refusal-qa__2Wak4wq/result.json`
- `FDA_question_review/logs/2026-07-02__12-04-06/fda-label-refusal-qa__2Wak4wq/verifier/reward.json`
- `FDA_question_review/logs/2026-07-02__12-04-06/fda-label-refusal-qa__2Wak4wq/agent/trajectory.json`
- `FDA_question_review/logs/2026-07-02__12-04-06/fda-label-refusal-qa__2Wak4wq/agent/terminus_2.pane`
- `FDA_question_review/logs/2026-07-02__12-57-32/fda-label-refusal-qa__Hxj5VAf/result.json`
- `FDA_question_review/logs/2026-07-02__12-57-32/fda-label-refusal-qa__Hxj5VAf/verifier/reward.json`
- `FDA_question_review/logs/2026-07-02__12-57-32/fda-label-refusal-qa__Hxj5VAf/agent/trajectory.json`
- `FDA_question_review/logs/2026-07-02__12-57-32/fda-label-refusal-qa__Hxj5VAf/agent/terminus_2.pane`
- `FDA_question_review/samples/fda-label-refusal-qa/tests/gold/gold.json`
- `FDA_question_review/samples/fda-label-refusal-qa/tests/score_utils.py`
