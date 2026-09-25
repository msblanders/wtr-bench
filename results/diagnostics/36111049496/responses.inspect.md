# Known-partner recovery diagnostic

Protocol `known-partner-recovery-v1`; model `claude-sonnet-4-5-20250929`.
Recorded 216/216; usable 215; missing 0; unusable 1.
Data source: recorded API responses. The separate programmed-oracle file is not model evidence.

| Condition | Correct / planned | Usable | Recovered / planned fits |
|---|---:|---:|---:|
| explicit_weight | 72/72 | 72 | 18/18 |
| choice_history | 137/144 | 143 | 24/36 |

Choice-only status: **mixed_or_failed**.
Fits include pooled and separate option orders, each history order and each pass.
They overlap; 54 fits are not 54 independent participants or replications.

| Comparison | Disagree | Complete pairs | Planned pairs |
|---|---:|---:|---:|
| option_order | 6 | 107 | 108 |
| repeat | 4 | 107 | 108 |
| history_order | 4 | 71 | 72 |

Pair comparisons use semantic keep/give choices, not printed letters.

Explanation review: **0/216 reviewed; 216 pending**.
Labels: {"consistent": 0, "incorrect_calculation_or_mapping": 0, "unclear_or_no_checkable_basis": 0, "unsupported_inference": 0, "unusable_or_missing": 0}
Correct choices do not guarantee correct returned calculations or inferences.
History explanations are checked against the supported interval, not the private generating weight.
Do not interpret brief explanations as access to internal reasoning.

## Decision

Inspect errors by arm/profile/order/pass and review the explanations before deciding next steps.
A complete choice pass supports recovery on these constructed controls only.
The social pilot remains paused. This workflow never launches it or repeats the diagnostic.
Do not rerun to select a perfect batch; partial and negative results remain part of the record.

Full counts, fits, pair records and review material are saved beside the response JSONL.
Token use: {"cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "input_tokens": 96408, "output_tokens": 26745}

