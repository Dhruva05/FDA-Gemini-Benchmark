# Hard FDA Question Set Summary

## Aggregate Results

- Tasks detected: 7
- Trials detected: 23
- Unscored target-agent attempts skipped: 6
- Aggregate pass@1: 0.130 (3/23)
- Aggregate pass@3: 0.143
- Below 30% pass@3 target: yes
- Mean fractional reward across trials: 0.700

## Task Summary

| task_name | n_trials | rewards | n_pass | pass_at_1 | pass_at_3 | mean_reward | max_reward | min_reward |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Warning citations | 4 | 0.000000;0.760261;0.715990;0.749323 | 0 | 0.000 | 0.000 | 0.556 | 0.760 | 0.000 |
| Long label retrieval | 4 | 0.000000;0.771979;0.741302;0.746250 | 0 | 0.000 | 0.000 | 0.565 | 0.772 | 0.000 |
| Cross-label comparison | 3 | 0.603685;0.573649;0.693216 | 0 | 0.000 | 0.000 | 0.624 | 0.693 | 0.574 |
| Multisection synthesis | 3 | 0.739583;0.721302;0.790625 | 0 | 0.000 | 0.000 | 0.751 | 0.791 | 0.721 |
| Numeric dosage | 3 | 0.786823;0.781354;0.834687 | 0 | 0.000 | 0.000 | 0.801 | 0.835 | 0.781 |
| Mixed batch | 3 | 0.791333;0.791333;0.823042 | 0 | 0.000 | 0.000 | 0.802 | 0.823 | 0.791 |
| Near-miss refusal | 3 | 0.908333;0.891667;0.891667 | 3 | 1.000 | 1.000 | 0.897 | 0.908 | 0.892 |

## Hardest Tasks

- Warning citations: pass@3=0.000, pass@1=0.000, mean reward=0.556
- Long label retrieval: pass@3=0.000, pass@1=0.000, mean reward=0.565
- Cross-label comparison: pass@3=0.000, pass@1=0.000, mean reward=0.624

## Easiest Tasks

- Near-miss refusal: pass@3=1.000, pass@1=1.000, mean reward=0.897
- Mixed batch: pass@3=0.000, pass@1=0.000, mean reward=0.802
- Numeric dosage: pass@3=0.000, pass@1=0.000, mean reward=0.801

## Fractional Near-Misses

- Numeric dosage: max reward=0.835, mean reward=0.801, pass@3=0.000
- Mixed batch: max reward=0.823, mean reward=0.802, pass@3=0.000
- Multisection synthesis: max reward=0.791, mean reward=0.751, pass@3=0.000
- Long label retrieval: max reward=0.772, mean reward=0.565, pass@3=0.000
- Warning citations: max reward=0.760, mean reward=0.556, pass@3=0.000

## Figure Notes

- `figures/hard_pass_rates.png`: grouped pass@1/pass@3 bars by task, with the 30% pass@3 target line.
- `figures/hard_reward_distribution.png`: per-task reward spread with individual trial rewards overlaid.
- `figures/hard_difficulty_curve.png`: hardest-to-easiest task curve using pass rates and mean reward.
- `figures/hard_trial_heatmap.png`: reward values by task and chronological trial number.
- `figures/hard_failure_taxonomy.png`: verifier-derived failure labels aggregated across failed trials.
- `hard_question_set_skipped_trials.csv`: target-agent attempts with no verifier reward, excluded from reward/pass calculations.
