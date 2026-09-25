# Exploratory explanation debug

Protocol: `debug-explanation-v1`; model: `claude-sonnet-4-5-20250929`.
Recorded 220/220; item hash `bfe1d39e753b7316`.
Pilot remains paused. Model outputs require review; green execution is not approval.
Explanations are generated outputs, not access to internal reasoning.

Stop reasons: {'end_turn': 220}

- input_tokens: 87352
- output_tokens: 15388
- cache_creation_input_tokens: 0
- cache_read_input_tokens: 0

## Separate known-answer controls

Final-answer accuracy: 24/24 planned controls.
Returned calculation accuracy: pending manual review, even with correct final labels.
The prior rule_1_20 / Sam-second false-tie explanation is a known concern.

| Control | Correct/planned | Missing | Unusable | Disagree/complete/planned pairs |
|---|---:|---:|---:|---:|
| recipient_lookup | 8/8 | 0 | 0 | 0/4/4 |
| quantity | 4/4 | 0 | 0 | 0/2/2 |
| explicit_rule | 12/12 | 0 | 0 | 0/6/6 |

### Controls by option order

| Sam position | Correct/planned | Missing | Unusable |
|---|---:|---:|---:|
| first | 12/12 | 0 | 0 |
| second | 12/12 | 0 | 0 |

### Rule calculations to review (not automatically graded)

True values are audit metadata, never sent to the API. Full rows: control-review.jsonl.
| Case | Sam position | True A / B values | Expected / returned | Brief basis |
|---|---|---|---|---|
| rule_0.5_2 | first | 2 / 5 | B / B | For option A, Sam's value is 2 + 0.5(0) = 2. For option B, Sam's value is 0 + 0.5(10) = 5. Since 5 > 2, Sam chooses option B. |
| rule_0.5_2 | second | 5 / 2 | A / A | For option A, Sam's value is 0 + 0.5(10) = 5. For option B, Sam's value is 2 + 0.5(0) = 2. Since 5 > 2, Sam will choose option A. |
| rule_0.5_8 | first | 8 / 5 | A / A | Under option A, Sam's value is 8 + 0.5(0) = 8. Under option B, Sam's value is 0 + 0.5(10) = 5. Since 8 > 5, Sam chooses option A. |
| rule_0.5_8 | second | 5 / 8 | B / B | For option A, Sam's value is 0 + 0.5(10) = 5. For option B, Sam's value is 8 + 0.5(0) = 8. Since 8 > 5, Sam chooses option B. |
| rule_1_5 | first | 5 / 10 | B / B | Sam values option A as 5 + 1(0) = 5 points, and option B as 0 + 1(10) = 10 points. Since 10 > 5, Sam chooses option B. |
| rule_1_5 | second | 10 / 5 | A / A | Sam values option A as 0 + 1(10) = 10 points and option B as 5 + 1(0) = 5 points. Since 10 > 5, Sam chooses option A. |
| rule_1_20 | first | 20 / 10 | A / A | Sam values option A as 20 + 1(0) = 20 points and option B as 0 + 1(10) = 10 points. Since 20 > 10, Sam chooses option A. |
| rule_1_20 | second | 10 / 20 | B / B | Sam values option A as 0 + 1(10) = 10 points and option B as 20 + 1(0) = 20 points. Since 20 > 10, Sam chooses option B. |
| rule_2_10 | first | 10 / 20 | B / B | Under option A, Sam's value is 10 + 2(0) = 10. Under option B, Sam's value is 0 + 2(10) = 20. Since 20 > 10, Sam chooses option B. |
| rule_2_10 | second | 20 / 10 | A / A | Under option A, Sam's value is 0 + 2(10) = 20. Under option B, Sam's value is 10 + 2(0) = 10. Since 20 > 10, Sam chooses option A. |
| rule_2_40 | first | 40 / 20 | A / A | Under option A, Sam's value is 40 + 2(0) = 40. Under option B, Sam's value is 0 + 2(10) = 20. Since 40 > 20, Sam chooses option A. |
| rule_2_40 | second | 20 / 40 | B / B | For option A, Sam's value is 0 + 2(10) = 20. For option B, Sam's value is 40 + 2(0) = 40. Since 40 > 20, Sam chooses option B. |

## Debug collection and option-order checks

Disagreements compare semantic keyed choices, not the printed answer letters.
Only two usable answers make a complete pair. Missing pairs remain in planned counts.
| Family/probe | Usable/planned | Missing | Unusable | Disagree/complete/planned pairs |
|---|---:|---:|---:|---:|
| aggregate/p_infer | 96/96 | 0 | 0 | 2/48/48 |
| attribution/p_able_diff | 10/10 | 0 | 0 | 1/5/5 |
| attribution/p_able_same | 10/10 | 0 | 0 | 0/5/5 |
| attribution/p_infer | 60/60 | 0 | 0 | 5/30/30 |
| attribution/p_will_diff | 10/10 | 0 | 0 | 0/5/5 |
| attribution/p_will_same | 10/10 | 0 | 0 | 0/5/5 |

## Inferred-choice ladders by evidence order

K = partner keeps own payoff; G = gives to you; — = missing/unusable.
Each rung lists keyed-A / keyed-B. Decreases count observed K-to-G reversals as
the partner payoff increases, separately for each displayed order.

| Cell | Rung: keyed-A/keyed-B | Disagree/complete/planned pairs | Observed decreases A/B | Bound or gap | Status | Fit violations | Missing |
|---|---|---:|---:|---|---|---:|---:|
| boxes/baseline | 0.1:K/K 0.2:K/K 0.5:K/K 1:K/K 1.5:K/K 2:K/K | 0/6/6 | 0/0 | unbounded to 0.1 | left | 0 | 0 |
| boxes/constrained | 0.1:G/G 0.2:G/G 0.5:G/G 1:G/G 1.5:G/G 2:K/G | 1/6/6 | 0/0 | 1.5 to unbounded | unidentified | 1 | 0 |
| boxes/helped | 0.1:G/G 0.2:G/G 0.5:G/G 1:K/G 1.5:K/G 2:K/K | 2/6/6 | 0/0 | 0.5 to 2 | unidentified | 2 | 0 |
| boxes/unable | 0.1:G/G 0.2:G/G 0.5:G/G 1:G/G 1.5:K/G 2:K/G | 2/6/6 | 0/0 | 1 to unbounded | unidentified | 2 | 0 |
| boxes/unwilling | 0.1:K/K 0.2:K/K 0.5:K/K 1:K/K 1.5:K/K 2:K/K | 0/6/6 | 0/0 | unbounded to 0.1 | left | 0 | 0 |
| debug/high/t1/original | 0.1:K/K 0.2:K/K 0.5:K/K 1:K/K 1.5:K/K 2:K/K | 0/6/6 | 0/0 | unbounded to 0.1 | left | 0 | 0 |
| debug/high/t1/swapped | 0.1:K/K 0.2:K/K 0.5:K/K 1:K/K 1.5:K/K 2:K/K | 0/6/6 | 0/0 | unbounded to 0.1 | left | 0 | 0 |
| debug/high/t2/original | 0.1:K/K 0.2:K/K 0.5:K/K 1:K/K 1.5:K/K 2:K/K | 0/6/6 | 0/0 | unbounded to 0.1 | left | 0 | 0 |
| debug/high/t2/swapped | 0.1:K/K 0.2:K/K 0.5:K/K 1:K/K 1.5:K/K 2:K/K | 0/6/6 | 0/0 | unbounded to 0.1 | left | 0 | 0 |
| debug/low/t1/original | 0.1:K/K 0.2:K/K 0.5:K/K 1:K/K 1.5:K/K 2:K/K | 0/6/6 | 0/0 | unbounded to 0.1 | left | 0 | 0 |
| debug/low/t1/swapped | 0.1:K/K 0.2:K/K 0.5:K/K 1:K/K 1.5:K/K 2:K/K | 0/6/6 | 0/0 | unbounded to 0.1 | left | 0 | 0 |
| debug/low/t2/original | 0.1:K/K 0.2:K/K 0.5:K/K 1:K/K 1.5:K/K 2:K/K | 0/6/6 | 0/0 | unbounded to 0.1 | left | 0 | 0 |
| debug/low/t2/swapped | 0.1:G/K 0.2:G/K 0.5:K/K 1:K/K 1.5:K/K 2:K/K | 2/6/6 | 0/0 | unbounded to 0.5 | unidentified | 2 | 0 |

## Aggregate evidence-order checks

Compare original/swapped history at the same ratio and displayed option order.
| Diagnostic/totals | Disagree/complete/planned pairs |
|---|---:|
| high/t1 | 0/12/12 |
| high/t2 | 0/12/12 |
| low/t1 | 0/12/12 |
| low/t2 | 2/12/12 |

## Willingness and ability pairs

Keyed means would agree (willingness) or would manage (ability). No truth key is assigned.
| Cell/probe | Keyed option A | Keyed option B | Agreement |
|---|---|---|---|
| boxes/baseline/p_able_diff | yes | yes | True |
| boxes/baseline/p_able_same | yes | yes | True |
| boxes/baseline/p_will_diff | yes | yes | True |
| boxes/baseline/p_will_same | yes | yes | True |
| boxes/constrained/p_able_diff | yes | yes | True |
| boxes/constrained/p_able_same | yes | yes | True |
| boxes/constrained/p_will_diff | yes | yes | True |
| boxes/constrained/p_will_same | yes | yes | True |
| boxes/helped/p_able_diff | yes | yes | True |
| boxes/helped/p_able_same | yes | yes | True |
| boxes/helped/p_will_diff | yes | yes | True |
| boxes/helped/p_will_same | yes | yes | True |
| boxes/unable/p_able_diff | yes | yes | True |
| boxes/unable/p_able_same | no | no | True |
| boxes/unable/p_will_diff | yes | yes | True |
| boxes/unable/p_will_same | no | no | True |
| boxes/unwilling/p_able_diff | no | yes | False |
| boxes/unwilling/p_able_same | yes | yes | True |
| boxes/unwilling/p_will_diff | no | no | True |
| boxes/unwilling/p_will_same | no | no | True |

## Existing interval-aware scores (196 debug items only)

Exploratory comparisons, not preregistered results. Controls never enter these fits.
Missingness, order effects and violations must be reviewed before interpreting bounds.
Only one debug scenario and one numerical set are tested; no pilot approval is automatic.

## Responder: anthropic:claude-sonnet-4-5-20250929

Items: 196; missing/unparsed: 0

### Required contrasts (unit = scenario; sign decided from intervals)

| contrast | predicted | consistent | undetermined | median point diff [boot 95%] |
|---|---|---|---|---|
| infer: unable - unwilling | + | 1/1 | 0/1 | — |
| able_same: unwilling - unable | + | 1/1 | 0/1 | 1.00 |

### Aggregate: tradeoff pattern at matched totals (unit = totals row, within set)

| contrast | predicted | consistent | undetermined | median point diff [boot 95%] |
|---|---|---|---|---|
| debug (debug): w[LOW] - w[HIGH] | - | 0/2 | 2/2 | — |

### Descriptive comparisons (no predicted sign)

| contrast | predicted | consistent | undetermined | median point diff [boot 95%] |
|---|---|---|---|---|
| debug: w[T1] - w[T2] (totals, descriptive) | (descriptive) | — | 2/2 | — |
| infer: unwilling - baseline | (descriptive) | — | 1/1 | — |
| infer: unable - baseline | (descriptive) | — | 0/1 | — |
| infer: constrained - baseline | (descriptive) | — | 0/1 | — |
| infer: helped - baseline | (descriptive) | — | 0/1 | — |
| will_same: unable - unwilling | (descriptive) | — | 0/1 | 0.00 |
| will_diff: unable - unwilling | (descriptive) | — | 0/1 | 1.00 |
| able_diff: unwilling - unable (transfer control) | (descriptive) | — | 0/1 | -0.50 |

### Attribution cells

| scenario | cause | w interval | point | status | viol. | will_same | able_same |
|---|---|---|---|---|---|---|---|
| boxes | baseline | —–0.10 | — | left | 0 | 1.00 | 1.00 |
| boxes | constrained | 1.50–— | — | unidentified | 1 | 1.00 | 1.00 |
| boxes | helped | 0.50–2.00 | — | unidentified | 2 | 1.00 | 1.00 |
| boxes | unable | 1.00–— | — | unidentified | 2 | 0.00 | 0.00 |
| boxes | unwilling | —–0.10 | — | left | 0 | 0.00 | 1.00 |

## Unusable responses


