# Figure captions for report

**Figure 1 — Difficulty profile by task.** Mean fractional reward across three Gemini 3.5 Flash runs per task. Lower reward indicates more headroom. Error bars show the observed min-max range across the three runs.

**Figure 2 — Headroom check.** Strict pass@1 and pass@3 are computed using full verifier success only (`reward == 1.0`). Both are below the benchmark headroom ceiling of 30% pass@3.

**Figure 3 — Difficulty curve.** Tasks sorted from hardest to easiest by mean fractional reward. Cross-label comparison is the hardest task family; near-miss refusal is the easiest.

**Figure 4 — Question-level pass rate.** Exact question-level pass rate across all questions and all three runs for each task. This separates partial task progress from full task success.

**Figure 5 — Dominant failure criteria.** Aggregated verifier deductions from the trajectory failure-events file. Content/semantic mismatches and missing clinical qualifiers dominate the failures.

**Figure 6 — Trajectory failure phase.** Counts of likely failure phases assigned during trajectory analysis. The dominant phases are answer synthesis/semantic compression and structured clinical qualifier extraction.

**Figure 7 — Run-to-run variability.** Reward distribution across three runs per task, showing that the difficulty profile is stable across repeated Gemini attempts.

**Figure 8 — Runtime by task.** Average runtime per run. This is optional appendix material for explaining evaluation cost and scale-up planning.
