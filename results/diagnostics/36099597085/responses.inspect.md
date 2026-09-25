# Fixed measurement diagnostic

Protocol `measurement-diagnostic-v1`; model `claude-sonnet-4-5-20250929`; hash `a23f46bf6a51a8c8`.
Recorded 156/156. Pilot remains paused; no automatic approval.
Explanations are generated outputs, not access to internal reasoning.

Stop reasons: {'end_turn': 156}; usage: {'input_tokens': 62848, 'output_tokens': 11239, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0}

## Collection

| Block | Usable/planned | Missing | Unusable |
|---|---:|---:|---:|
| control/original | 24/24 | 0 | 0 |
| control/fraction_control | 8/8 | 0 | 0 |
| valuation/extended | 48/48 | 0 | 0 |
| valuation/original | 48/48 | 0 | 0 |
| valuation/decimal_anchor | 12/12 | 0 | 0 |
| binary/original | 8/8 | 0 | 0 |
| binary/clarified | 8/8 | 0 | 0 |

## Controls

Final accuracy and stated calculations are separate.
Calculations require manual review, including correct final answers.

| Variant | Correct/planned | Option disagreements/complete/planned |
|---|---:|---:|
| original | 24/24 | 0/12/12 |
| fraction_control | 8/8 | 0/4/4 |

Full prompts, expected values and bases: control-review.jsonl.

## Range ladders

K = Sam keeps; G = gives to you; — = missing/unusable.
Decimal spelling anchors and all controls are excluded from fits.
Bounds are threshold fits, not confidence intervals; tied fits remain unidentified.
Each pattern is keyed-A/keyed-B. Full fits by displayed order are in the JSON.

| Cell | Rungs | Disagree/complete/planned | Decreases A/B | Bounds | Status | Violations | Missing |
|---|---|---:|---:|---|---|---:|---:|
| boxes/unable | 0.01:G/G 0.05:G/G 0.1:G/G 0.2:G/G 0.5:G/G 2:K/G 4:K/K 8:G/K | 2/8/8 | 1/0 | 0.5 to 4.0 | unidentified | 2 | 0 |
| boxes/unwilling | 0.01:K/K 0.05:K/K 0.1:K/K 0.2:K/K 0.5:K/K 2:K/K 4:K/K 8:K/K | 0/8/8 | 0/0 | unbounded to 0.01 | left | 0 | 0 |
| debug/high/t2/original | 0.01:K/K 0.05:K/K 0.1:K/K 0.2:K/K 0.5:K/K 2:K/K 4:K/K 8:K/K | 0/8/8 | 0/0 | unbounded to 0.01 | left | 0 | 0 |
| debug/high/t2/swapped | 0.01:K/K 0.05:K/K 0.1:K/K 0.2:K/K 0.5:K/K 2:K/K 4:K/K 8:K/K | 0/8/8 | 0/0 | unbounded to 0.01 | left | 0 | 0 |
| debug/low/t2/original | 0.01:K/K 0.05:K/K 0.1:K/K 0.2:K/G 0.5:K/K 2:K/K 4:K/K 8:K/K | 1/8/8 | 0/1 | unbounded to 0.01 | left | 1 | 0 |
| debug/low/t2/swapped | 0.01:K/K 0.05:K/K 0.1:G/K 0.2:G/K 0.5:K/K 2:K/K 4:K/K 8:K/K | 2/8/8 | 1/0 | unbounded to 0.01 | left | 2 | 0 |

## Matched comparisons

Disagree/complete/planned; a wording change is sensitivity, not itself an error.

- 1 versus 1.0 notation: 1/12/12
- Original versus clarified binary: 2/8/8
- Evidence order (ladder): 3/32/32
- Evidence order (decimal_anchor): 0/4/4
- Exact requests versus run 36095971330 (control): 0/24/24
- Exact requests versus run 36095971330 (valuation): 1/48/48
- Exact requests versus run 36095971330 (binary): 0/8/8
Previous responses are compared only; they never enter current fits.

## Conditional probes

Yes means agrees/manages; no social correctness key is assigned.
Review all 16 explanations using binary-review.jsonl; no keyword auto-grading.

| Cell | Wording | Keyed first | Keyed second | Disagree/complete/planned |
|---|---|---|---|---:|
| boxes/unable/p_able_diff | original | yes | yes | 0/1/1 |
| boxes/unable/p_able_diff | clarified | yes | yes | 0/1/1 |
| boxes/unable/p_will_same | original | no | no | 0/1/1 |
| boxes/unable/p_will_same | clarified | yes | no | 1/1/1 |
| boxes/unwilling/p_able_diff | original | no | yes | 1/1/1 |
| boxes/unwilling/p_able_diff | clarified | yes | yes | 0/1/1 |
| boxes/unwilling/p_will_same | original | no | no | 0/1/1 |
| boxes/unwilling/p_will_same | clarified | no | no | 0/1/1 |

## Exploratory LOW minus HIGH bounds

Report each history order separately; no effect direction is a pass requirement.

- low_minus_high/original: undetermined; point difference None; a:left b:left intervals overlap
- low_minus_high/swapped: undetermined; point difference None; a:left b:left intervals overlap

One fixed batch only. Inspect missingness, controls, decimal notation, both order
checks and conditional fidelity before discussing social contrasts. Stable null or
contrary results are valid outcomes. Do not rerun until a preferred pattern appears.
This diagnostic covers two boxes causes and numerical T2 only, not all debug cells.

