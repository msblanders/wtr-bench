# Payoff presentation diagnostic

Protocol `payoff-presentation-v1`; model `claude-sonnet-4-5-20250929`.
Recorded 288/288; usable 288; missing 0; unusable 0.
Data source: recorded API responses. The programmed-oracle check is software verification only.

| Presentation | Correct / planned | Usable | Recovered / planned fits | Choice status |
|---|---:|---:|---:|---|
| original | 138/144 | 144 | 24/36 | mixed_or_failed |
| explicit_payoffs | 139/144 | 144 | 28/36 | mixed_or_failed |

## Matched presentation comparison

Complete 144/144; incomplete 0.
Both correct: 133; explicit-payoffs only correct: 6; original only correct: 5; both incorrect: 0.
Positive differences favor explicit payoffs. Missing/unusable responses remain in planned denominators.
Accuracy difference among complete pairs: 0.006944444444444444
Correct-fraction difference across planned pairs: 0.006944444444444444

| Presentation | Comparison | Disagree | Complete / planned pairs |
|---|---|---:|---:|
| original | option_order | 6 | 72/72 |
| original | history_order | 4 | 72/72 |
| original | repeat | 2 | 72/72 |
| explicit_payoffs | option_order | 5 | 72/72 |
| explicit_payoffs | history_order | 5 | 72/72 |
| explicit_payoffs | repeat | 1 | 72/72 |

Pair comparisons use semantic choices, not printed letters.
Fits overlap and repeats are not independent participants; these are descriptive fixed-set results.

## Separate explanation review

**0/288 reviewed; 288 pending.**
Labels: {"consistent": 0, "incorrect_calculation_or_mapping": 0, "unclear_or_no_checkable_basis": 0, "unsupported_inference": 0, "unusable_or_missing": 0}
original: 0/144 reviewed; {"consistent": 0, "incorrect_calculation_or_mapping": 0, "unclear_or_no_checkable_basis": 0, "unsupported_inference": 0, "unusable_or_missing": 0}
explicit_payoffs: 0/144 reviewed; {"consistent": 0, "incorrect_calculation_or_mapping": 0, "unclear_or_no_checkable_basis": 0, "unsupported_inference": 0, "unusable_or_missing": 0}

Correct final answers do not guarantee correct explanations.
Review history inferences against feasible intervals, not a uniquely known private weight.
Returned explanations are not evidence of internal reasoning. Disclose who coded them.

## Decision

Assess errors, changed intervals, all reversals/repeats and explanations before a decision.
Improvement on this fixed set is not full social-measure validation; do not select a preferred order or pass.
The presentation package changes layout and explicit zero payoffs together; it does not isolate either factor.
Both social pilots remain paused. This workflow never launches them or repeats itself.
Do not rerun until perfect. Any further collection needs a separately documented purpose and fixed plan.
Token use: {"cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "input_tokens": 149040, "output_tokens": 40484}
