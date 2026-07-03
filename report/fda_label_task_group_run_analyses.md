# FDA Label Task Group Run Analyses

## Technical Summary

The 12 timestamped runs group cleanly into four Harbor tasks: factual QA, multihop QA, citation retrieval, and mixed batch. Every run produced at least one scored failure, so every run has binary pass `0`.

The main pattern is consistent across tasks: agents usually found the right label and often found relevant evidence, but lost points because the final answer wording did not match the hidden gold answer closely enough or because the cited section name did not match the verifier's expected section. The only hard execution failure was `fda-label-multihop-qa__tx4YRVL`, which timed out and never wrote `/root/answers.json`.

Best run by group:

| Group | Best run | Reward | Primary reason it led the group |
|---|---:|---:|---|
| Factual QA | `fda-label-factual-qa__xwxopjU` | 0.780000 | Fewer non-answer failures than the other two factual runs |
| Multihop QA | `fda-label-multihop-qa__LHBbWVZ` | 0.772841 | Completed successfully and had fewer low-score section failures than `yAeMerG` |
| Citation retrieval | `fda-label-citation-retrieval__QJdbptj` | 0.780579 | Improved the Erlotinib evidence/section handling relative to the other citation runs |
| Mixed batch | `fda-label-mixed-batch__FiDaXmj` | 0.845550 | Preserved all refusal passes and improved several supported-answer items |

Detailed row-level score and failure tables are in:

| Group | CSV table |
|---|---|
| Factual QA | `metrics/fda_label_factual_qa_run_comparison.csv` |
| Multihop QA | `metrics/fda_label_multihop_qa_run_comparison.csv` |
| Citation retrieval | `metrics/fda_label_citation_retrieval_run_comparison.csv` |
| Mixed batch | `metrics/fda_label_mixed_batch_run_comparison.csv` |

## Grouping Verification

| Requested timestamp | Harbor task | Run id | Reward | Binary pass |
|---|---|---|---:|---:|
| `2026-07-02__11-18-37` | Factual QA | `fda-label-factual-qa__xwxopjU` | 0.780000 | 0 |
| `2026-07-02__11-38-43` | Factual QA | `fda-label-factual-qa__8VE3Qyb` | 0.740000 | 0 |
| `2026-07-02__12-42-34` | Factual QA | `fda-label-factual-qa__AyCAFYK` | 0.740000 | 0 |
| `2026-07-02__11-22-45` | Multihop QA | `fda-label-multihop-qa__LHBbWVZ` | 0.772841 | 0 |
| `2026-07-02__11-44-03` | Multihop QA | `fda-label-multihop-qa__tx4YRVL` | 0.000000 | 0 |
| `2026-07-02__12-51-33` | Multihop QA | `fda-label-multihop-qa__yAeMerG` | 0.732630 | 0 |
| `2026-07-02__11-30-43` | Citation retrieval | `fda-label-citation-retrieval__BxJYFj3` | 0.711195 | 0 |
| `2026-07-02__12-05-31` | Citation retrieval | `fda-label-citation-retrieval__eYpzv8F` | 0.760000 | 0 |
| `2026-07-02__12-58-48` | Citation retrieval | `fda-label-citation-retrieval__QJdbptj` | 0.780579 | 0 |
| `2026-07-02__11-34-14` | Mixed batch | `fda-label-mixed-batch__tHZeDwC` | 0.800214 | 0 |
| `2026-07-02__12-34-08` | Mixed batch | `fda-label-mixed-batch__FiDaXmj` | 0.845550 | 0 |
| `2026-07-02__13-02-48` | Mixed batch | `fda-label-mixed-batch__txmvp9M` | 0.812594 | 0 |

## Methodology

For each timestamp, I mapped the run folder to its Harbor task through `trial_results.csv`, then inspected the run's `reward.json`, `gold.json`, and available agent trace artifacts. The score comparisons below use the verifier's five 0.2-point criteria: label, answer, evidence quote, cited section, and refusal behavior when applicable.

The report focuses on the same questions as the verifier. A "failure" below means at least one verifier criterion failed for that question, not necessarily that the answer was wholly wrong.

## Group 1: Factual QA

### Run Overview

| Timestamp | Run id | Reward | Failed questions | Episodes | Agent time sec | Cost USD | Run-level issue |
|---|---|---:|---:|---:|---:|---:|---|
| `2026-07-02__11-18-37` | `fda-label-factual-qa__xwxopjU` | 0.780000 | 10/10 | 51 | 226.185 | 0.8800 | None |
| `2026-07-02__11-38-43` | `fda-label-factual-qa__8VE3Qyb` | 0.740000 | 10/10 | 76 | 297.799 | 1.3390 | None |
| `2026-07-02__12-42-34` | `fda-label-factual-qa__AyCAFYK` | 0.740000 | 10/10 | 54 | 516.436 | 0.8717 | None |

### Processing Differences

| Run id | How the agent processed the task differently | Failure pattern |
|---|---|---|
| `xwxopjU` | Shortest successful factual run. It parsed label structure, built local search helpers, searched sections, and self-checked final answers against evidence. | All 10 answers failed hidden answer matching. It had fewer section/evidence misses than the other two runs, so it scored best. |
| `8VE3Qyb` | Most expensive factual run by cost and episode count. It used more repeated section inspection and had repeated response-format issues during the process. | All 10 answers failed hidden answer matching. The Wakix interaction item also failed evidence and section, dropping that item to 0.4. |
| `AyCAFYK` | Longest factual run by wall time. It generated valid final JSON and inspected its final answer file, but did not materially improve answer exactness. | All 10 answers failed hidden answer matching. It repeated the Wakix interaction evidence/section miss seen in `8VE3Qyb`. |

### Question Score Matrix

| Question id | Drug | `xwxopjU` | `8VE3Qyb` | `AyCAFYK` | Main failure |
|---|---|---:|---:|---:|---|
| `737e4762b27ce680` | Prograf | 0.600 | 0.600 | 0.600 | Answer and section mismatch |
| `fbe55c64b1a891ec` | Colchicine | 0.800 | 0.800 | 0.800 | Answer mismatch |
| `4fca227a924f7940` | Wakix | 0.800 | 0.400 | 0.400 | Answer mismatch; two runs also missed evidence and section |
| `827fe57db493d89c` | Rivastigmine | 0.800 | 0.800 | 0.800 | Answer mismatch |
| `9d89461f1c9ba74a` | Rivastigmine | 0.800 | 0.800 | 0.800 | Answer mismatch |
| `233c4e692f66f693` | Motrin | 0.800 | 0.800 | 0.800 | Answer mismatch |
| `c8c33e3d63807e82` | Pioglitazone | 0.800 | 0.800 | 0.800 | Answer mismatch |
| `a80e89057fe3f584` | Metronidazole | 0.800 | 0.800 | 0.800 | Answer mismatch |
| `29e9a9ac25320e11` | Metronidazole | 0.800 | 0.800 | 0.800 | Answer mismatch |
| `caef464ffb09c712` | Atorvastatin | 0.800 | 0.800 | 0.800 | Answer mismatch |

### Factual QA Takeaway

The agents were structurally compliant and mostly evidence-oriented, but the hidden verifier was strict on exact answer content. `xwxopjU` is the strongest run because it avoided the additional Wakix evidence/section failures that hurt `8VE3Qyb` and `AyCAFYK`.

## Group 2: Multihop QA

### Run Overview

| Timestamp | Run id | Reward | Failed questions | Episodes | Agent time sec | Cost USD | Run-level issue |
|---|---|---:|---:|---:|---:|---:|---|
| `2026-07-02__11-22-45` | `fda-label-multihop-qa__LHBbWVZ` | 0.772841 | 8/8 | 43 | 202.973 | 0.7615 | None |
| `2026-07-02__11-44-03` | `fda-label-multihop-qa__tx4YRVL` | 0.000000 | 8/8 | 42 | 1180.395 | 0.5385 | Timed out; missing `/root/answers.json` |
| `2026-07-02__12-51-33` | `fda-label-multihop-qa__yAeMerG` | 0.732630 | 8/8 | 51 | 337.478 | 0.8358 | None |

### Processing Differences

| Run id | How the agent processed the task differently | Failure pattern |
|---|---|---|
| `LHBbWVZ` | Completed with a relatively compact search/synthesis loop. It found relevant label material but often cited a section that did not match the expected verifier section. | All 8 questions failed at least one criterion. Losses were mostly partial answer similarity and cited-section mismatches. |
| `tx4YRVL` | Spent a long time in execution and timed out before producing the required answer file. | All 8 questions scored 0 because `/root/answers.json` was missing. This is an execution failure, not a semantic-answer failure. |
| `yAeMerG` | Completed and searched labels more extensively than `LHBbWVZ`, but with lower average score. | All 8 questions failed. It had more low 0.6 scores where answer and section mismatches combined. |

### Question Score Matrix

| Question id | Drug | `LHBbWVZ` | `tx4YRVL` | `yAeMerG` | Main failure |
|---|---|---:|---:|---:|---|
| `1d9af657d20284f8` | Pradaxa | 0.703 | 0.000 | 0.706 | Partial answer match plus section mismatch; timeout run missing output |
| `3caa0c02ffad01ba` | Atacand | 0.708 | 0.000 | 0.709 | Partial answer match plus section mismatch; timeout run missing output |
| `b5f4f56815d6c9ec` | Adalimumab | 0.702 | 0.000 | 0.600 | Partial answer/section failure; timeout run missing output |
| `a587db96e2628cb3` | Sulfamethoxazole and Trimethoprim | 0.926 | 0.000 | 0.922 | Partial answer match; timeout run missing output |
| `acb0b0fd5389fc4a` | Pantoprazole | 0.714 | 0.000 | 0.600 | Partial answer/section failure; timeout run missing output |
| `7eaa7cc42b20ba07` | Pantoprazole | 0.710 | 0.000 | 0.600 | Partial answer/section failure; timeout run missing output |
| `58bf95572a9ff715` | Nifedipine | 0.800 | 0.000 | 0.800 | Answer mismatch; timeout run missing output |
| `3fe8d41d8a3f7cfe` | Nifedipine | 0.919 | 0.000 | 0.924 | Partial answer match; timeout run missing output |

### Multihop QA Takeaway

`tx4YRVL` should be treated separately because it failed operationally. Among completed runs, `LHBbWVZ` had the best balance: it still missed exact answer/section criteria, but avoided several of the lower 0.6 outcomes that hurt `yAeMerG`.

## Group 3: Citation Retrieval

### Run Overview

| Timestamp | Run id | Reward | Failed questions | Episodes | Agent time sec | Cost USD | Run-level issue |
|---|---|---:|---:|---:|---:|---:|---|
| `2026-07-02__11-30-43` | `fda-label-citation-retrieval__BxJYFj3` | 0.711195 | 10/10 | 45 | 188.712 | 0.7986 | None |
| `2026-07-02__12-05-31` | `fda-label-citation-retrieval__eYpzv8F` | 0.760000 | 10/10 | 36 | 1695.837 | 0.7027 | None |
| `2026-07-02__12-58-48` | `fda-label-citation-retrieval__QJdbptj` | 0.780579 | 10/10 | 47 | 217.861 | 0.8257 | None |

### Processing Differences

| Run id | How the agent processed the task differently | Failure pattern |
|---|---|---|
| `BxJYFj3` | Completed quickly and produced valid output, but its evidence/section selection was weaker for several Erlotinib items. | All 10 questions failed. Two Erlotinib questions failed answer, evidence, and section, pulling the average down. |
| `eYpzv8F` | Had the fewest episodes but extremely long wall time. It avoided some evidence misses from `BxJYFj3`, but still had broad answer wording and section mismatches. | All 10 questions failed. Most failures were answer mismatches, with recurring section mismatches on SHAROBEL-style items. |
| `QJdbptj` | Recovered the most citation credit on Erlotinib questions and had the best final score. | All 10 questions still failed at least one criterion. Remaining losses were answer exactness and section naming. |

### Question Score Matrix

| Question id | Drug | `BxJYFj3` | `eYpzv8F` | `QJdbptj` | Main failure |
|---|---|---:|---:|---:|---|
| `4c661df7d431bd3c` | SHAROBEL | 0.600 | 0.600 | 0.600 | Answer and section mismatch |
| `8547c32761488413` | Erlotinib | 0.501 | 0.800 | 0.902 | `QJdbptj` fixed most citation loss; all still had some answer mismatch |
| `a2356cd29e77ae23` | Sapropterin | 0.800 | 0.800 | 0.800 | Answer mismatch |
| `f1a6997222fd3656` | Fosphenytoin | 0.800 | 0.800 | 0.800 | Section mismatch |
| `86e6f9c97badb426` | Erlotinib | 0.506 | 0.800 | 0.904 | `QJdbptj` fixed most citation loss; all still had some answer mismatch |
| `13c273472daead37` | Tadalafil | 0.800 | 0.800 | 0.800 | Answer mismatch |
| `190721bf5636800a` | Hydrocodone Polistirex and Chlorpheniramine Polistirex | 0.800 | 0.800 | 0.800 | Section mismatch |
| `017775054c56f02f` | Penicillamine | 0.800 | 0.800 | 0.800 | Answer mismatch |
| `7d2efbc4667c7c41` | Tacrolimus | 0.800 | 0.800 | 0.800 | Answer mismatch |
| `c764f432912d70f8` | SHAROBEL | 0.705 | 0.600 | 0.600 | Answer and section mismatch |

### Citation Retrieval Takeaway

`QJdbptj` is the best citation-retrieval run because it materially improved the Erlotinib items. The group still failed every question because the verifier required stricter answer wording and exact section alignment than the agents consistently produced.

## Group 4: Mixed Batch

### Run Overview

| Timestamp | Run id | Reward | Failed questions | Episodes | Agent time sec | Cost USD | Run-level issue |
|---|---|---:|---:|---:|---:|---:|---|
| `2026-07-02__11-34-14` | `fda-label-mixed-batch__tHZeDwC` | 0.800214 | 8/12 | 54 | 216.253 | 0.8390 | None |
| `2026-07-02__12-34-08` | `fda-label-mixed-batch__FiDaXmj` | 0.845550 | 7/12 | 43 | 214.268 | 0.9840 | None |
| `2026-07-02__13-02-48` | `fda-label-mixed-batch__txmvp9M` | 0.812594 | 7/12 | 36 | 183.576 | 0.6007 | None |

### Processing Differences

| Run id | How the agent processed the task differently | Failure pattern |
|---|---|---|
| `tHZeDwC` | More exhaustive than the other mixed runs and inspected final answers, but over-selected or misaligned evidence/sections on several supported questions. | Passed all refusal questions. Lost more points on Gleevec, Aripiprazole, Nifediac, ERIVEDGE, and Cevimeline. |
| `FiDaXmj` | Best balance of refusal handling and supported-answer precision. It fully recovered the DOJOLVI item and improved several supported items. | Passed all refusal questions. Remaining losses were mostly answer wording and section alignment on supported factual/multihop questions. |
| `txmvp9M` | Fastest and cheapest mixed run. It matched `FiDaXmj` on the number of failed questions but had more severe misses on Nifediac and Gleevec. | Passed all refusal questions. Supported-answer losses were concentrated in section/evidence alignment and answer exactness. |

### Question Score Matrix

| Question id | Drug | Type | `tHZeDwC` | `FiDaXmj` | `txmvp9M` | Main failure |
|---|---|---|---:|---:|---:|---|
| `676501b8c591ce64` | Guardian Loratadine | refusal | 1.000 | 1.000 | 1.000 | None |
| `dc227e54867c06b2` | Sandimmune | refusal | 1.000 | 1.000 | 1.000 | None |
| `2332e89fd83b96ce` | Eszopiclone | refusal | 1.000 | 1.000 | 1.000 | None |
| `541f3c2395ad44d5` | ORLISTAT | refusal | 1.000 | 1.000 | 1.000 | None |
| `3583ae962c61ec1a` | DOJOLVI | citation_retrieval | 0.940 | 1.000 | 1.000 | `tHZeDwC` had partial answer match |
| `8deb89c814e1220d` | Gleevec | factual | 0.600 | 0.800 | 0.600 | Answer mismatch; two runs also missed section |
| `739c3c13cccd09a7` | Aripiprazole | factual | 0.400 | 0.705 | 0.600 | Answer/section mismatch; `tHZeDwC` also missed evidence |
| `07ca4413bcf4d892` | Saxagliptin | factual | 0.800 | 0.800 | 0.800 | Answer mismatch |
| `cfcf0d2bc4afae07` | Nifediac | multihop | 0.724 | 0.600 | 0.400 | Answer/section mismatch; `txmvp9M` also missed evidence |
| `89984a62b99d411c` | ERIVEDGE | multihop | 0.503 | 0.501 | 0.503 | Partial answer plus evidence and section mismatch |
| `1d764888bf6f95f8` | Lamivudine | multihop | 0.923 | 0.940 | 0.921 | Partial answer match |
| `6acd32d7390830a4` | Cevimeline | citation_retrieval | 0.705 | 0.800 | 0.927 | Answer/section mismatch varied by run |

### Mixed Batch Takeaway

All mixed-batch agents handled refusal correctly. The differentiator was supported-answer precision. `FiDaXmj` is the best overall mixed run because it combined perfect refusal handling with better recovery on DOJOLVI, Gleevec, Aripiprazole, and Cevimeline.

## Cross-Group Failure Themes

| Theme | Where it appeared | Impact |
|---|---|---|
| Hidden answer exactness | All four groups | The most common loss. Agents often gave medically plausible answers supported by the label, but did not match the expected answer string closely enough. |
| Section-name mismatch | Factual, multihop, citation, mixed | Agents often cited a nearby or broader section instead of the verifier's expected section label. |
| Evidence quote mismatch | Less frequent; notable in citation and mixed | Exact evidence overlap failures were concentrated in specific questions, especially Erlotinib citation items for `BxJYFj3` and supported mixed questions for `tHZeDwC`/`txmvp9M`. |
| Operational timeout | Multihop only | `tx4YRVL` failed because the required output file was missing after timeout. |
| Refusal handling | Mixed only | All refusal examples passed in all mixed runs; refusal behavior was not the weak point. |

## Recommended Next Steps

1. Add a final answer-normalization pass that forces concise, gold-like wording instead of broad prose.
2. Require agents to choose `cited_section` from a parsed list of exact section headers rather than free-form section names.
3. Add pre-submit validation for `/root/answers.json` existence and schema validity, especially for long multihop runs.
4. Track evidence overlap separately from semantic answer quality, because several runs found the right label but lost on exact quote boundaries.

## Limitations

This analysis uses the local run artifacts and verifier output available in the workspace. It can identify verifier-visible failure criteria and broad trace-level process differences, but it cannot prove the hidden gold answer wording beyond the similarity and failure messages recorded in `reward.json`.
