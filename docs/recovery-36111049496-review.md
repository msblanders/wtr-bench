# Known-partner recovery: run 36111049496

**Decision, 25 September 2026 UTC:** The explicit-weight condition passed all
choice, interval and explanation checks in this run. History-based recovery
was mostly accurate but did not meet the frozen clear-pass rule. The failures
include option-order sensitivity and coherent-looking wrong intervals, so
they cannot be dismissed as only a missing final-answer field. Both social
pilots remain paused. Do not repeat this batch to obtain a passing result.

This is progress on the original measurement question, not a replacement
robustness pilot. It shows that the model can execute the ladder with a supplied
weight and often recover the correct interval from informative histories.
It does not establish reliable end-to-end recovery across the tested
presentations, nor show that models lack stable welfare preferences.
These questions concern a **described partner's** choices, not the model's own
preferences. Returned explanations are observable outputs, not access to
internal reasoning or a uniquely identified internal cause.

## Source and integrity

- [Run 36111049496](https://github.com/msblanders/wtr-bench/actions/runs/36111049496),
  attempt 1; completed successfully on source commit
  `ef372ef9286c18a86ba78f03bf7107bd132cbccd`.
- [Frozen prospective plan](known-partner-recovery-v1.md): 216 requests,
  `claude-sonnet-4-5-20250929`, temperature 0, 256 output tokens, structured
  `brief_basis` followed by A/B `answer`. No retries or added requests.
- [Raw archive](../results/diagnostics/36111049496/) preserves all 16 artifact
  files unchanged. `SHA256SUMS` covers them; `audit/` contains later work.
- Downloaded ZIP digest:
  `76ee14fac9e467ebafe04e0f80998970658e22e7a4bd656c151ea4be8876321c`.
  Source revision, exact prompts, request bodies, plan, configuration, model
  IDs, response order and unique API IDs were checked. The original automatic
  summaries, fits, comparisons and explanation packet were reproduced.
- A [separate verifier](../results/diagnostics/36111049496/audit/verify.py)
  derives truth keys from the literal displayed histories and options using
  rational arithmetic; independently enumerates threshold partitions and
  comparison pairs; checks parsing, original-file hashes and review bindings.
  It makes no API calls and does not automatically rate explanations.

The artifact's programmed-oracle check is software verification, not a model
result. None of the original held-out social scenarios were queried here.

## Choices and interval recovery

| Condition | Correct / planned | Usable | Incorrect usable | Unusable | Recovered / planned fits |
|---|---:|---:|---:|---:|---:|
| Explicit weight | 72/72 | 72 | 0 | 0 | 18/18 |
| Choice history | 137/144 | 143 | 6 | 1 | 24/36 |
| Total | 209/216 | 215 | 6 | 1 | 42/54 |

History accuracy is 95.1% of planned requests, or 95.8% of usable answers.
The frozen rule required all 216 usable and correct and all 54 complete,
zero-violation containing fits. Its status remains **mixed_or_failed**;
the rule has not been relaxed after observing the data. Repeated prompts and
overlapping fits are not independent samples or evidence across models/dates.

| History profile | Correct / planned | Wrong | Unusable |
|---|---:|---:|---:|
| Low: 0.25 < w < 0.4 | 44/48 | 3 | 1 |
| Middle: 0.6 < w < 0.9 | 46/48 | 2 | 0 |
| High: 1.6 < w < 1.9 | 47/48 | 1 | 0 |

All six wrong answers choose **A, keeping for Sam**, where B (giving to you)
is required. All occur when Sam is option A: 66/72 correct in that order,
versus 71/71 usable correct when Sam is option B, plus one unusable response.
The six matched option reversals are correct. This is descriptive evidence
of presentation sensitivity; it does not isolate a universal A bias from a
Sam-first interaction or justify retaining only the better order.

| Comparison | History disagreements / complete | History planned pairs | Explicit disagreements / complete |
|---|---:|---:|---:|
| Option reversal | 6/71 | 72 | 0/36 |
| Exact-request repeat | 4/71 | 72 | 0/36 |
| History reversal | 4/71 | 72 | Not applicable |

One unusable response removes one pair from each history comparison. Overall,
including explicit controls, option reversal is 6/107 complete pairs out of
108 planned; exact repeat is 4/107 out of 108. Pass 1 history accuracy is
68/72; pass 2 is 69/72, with two wrong and one unusable. Do not select pass 2
or either history/option order after seeing these outcomes.

## Exact failures and what the explanations add

All wrong and unusable final answers are listed below. Indices are zero-based
positions in the frozen request/response files. Full IDs, prompts, raw text
and notes are in [explanation-issues.jsonl](../results/diagnostics/36111049496/audit/explanation-issues.jsonl).

| Index | History/profile/pass; current Sam payoff | Observable defect |
|---|---|---|
| 36 | Reversed / low / 1; 2 | Misrepresents the giving history, then infers `10w < 2` from `10w < 4`. |
| 41 | Reversed / low / 1; 1 | Eventually states the correct weight interval but says `1 < 10w` is false. |
| 56 | Original / middle / 1; 5 | Correct interval and option values, followed by `10w < 9 < 5`. |
| 75 | Original / low / 1; 2 | Correct interval and option values, followed by `10w < 4 < 2`. |
| 146 | Original / middle / 2; 5 | Repeats index 56's false `9 < 5` comparison. |
| 159 | Reversed / low / 2; 5 | Hits 256 output tokens before the final answer field; raw text includes initial errors and later correction. Retained as unusable. |
| 191 | Original / high / 2; 5 | Correct history interval, but assigns A value `5 + 10w` even though you receive zero under A. |

**Five of the six wrong responses state the correct history interval before
giving the wrong choice.** Three of those give the correct current option
values followed by a false numerical inequality (56, 75, 146); another gives
the correct values but rejects a true comparison (41); the last maps the
current payoff incorrectly (191). Thus “history arm failed” does not mean
every failure is failure to derive the weight bounds. Adding history inference
exposes a failure somewhere in the full history-to-choice procedure, including
comparison and payoff mapping. The returned text helps locate observable
defects but cannot establish what caused the answer internally.

The truncation includes a suggested B in its explanation, but it never
supplies the required answer field. It is not repaired or credited. Raising
the output allowance alone would not address the six completed wrong answers.

### Explanation audit, separate from accuracy

All 216 records were read and coded by the assistant using the frozen rubric,
unblinded to answers and reference values. This is not independent human
coding, an inter-rater study, or an automated correctness classifier.
[Response-bound labels and individual notes](../results/diagnostics/36111049496/audit/explanation-labels.jsonl)
were accepted by the existing review validator; none remain pending.

| Condition | Consistent | Calculation/mapping error | Unsupported inference only | Unclear | Unusable |
|---|---:|---:|---:|---:|---:|
| Explicit weight | 72 | 0 | 0 | 0 | 0 |
| Choice history | 103 | 40 | 0 | 0 | 1 |

The 40 error labels comprise all six wrong answers **and 34 correct answers**.
Repeated defects include adding the payoff from the rejected option, impossible
inequalities such as `5 + 20w < 20w`, false bounds, and unsupported claims
that consistent histories contradict each other. When both calculation and
inference defects occur, the frozen priority rule assigns calculation/mapping;
zero in the inference-only column does not mean no inference defects occurred.

Coding details that matter for interpretation:

- Loose but entailed bounds are permitted. Indices 118, 153 and 200 use weaker
  bounds than the tight history interval, but those bounds are true and their
  decisive comparisons are valid. They are consistent; exact bounds were
  not required. They do not claim a division equals the loose bound.
- At 141, an initial payoff mapping is immediately corrected and the final
  inference is sound. It remains in the error category because the returned
  text includes that mapping, with the repair explicitly noted. Excluding
  this one repaired case would give 39 errors and 104 consistent history
  explanations, and would not change any choice, fit or readiness conclusion.
- “Sam gets ... points” inside an otherwise correct weighted-value calculation
  is read as utility shorthand at indices 32, 66, 82, 102, 152 and 154. Those
  labels note the imprecise wording. No incorrect value or choice mapping is
  inferred solely from that shorthand.
- A wrong displayed representation of a history choice is recorded even when
  its derived weaker inequality happens to be true. Correct answers and later
  correct bounds do not erase an unretracted impossible equation or payoff
  mapping. No hidden generating weight is demanded of history explanations.

These disclosed judgments make the explanation count reviewable. The six
incorrect choices, raw truncation, option disagreements and fit failures do
not depend on these coding boundaries.

## Why a few choice errors matter to this measure

The 12 nonrecovered history fits overlap. They are not 12 separate failures or
participants. Classified by their principal failure:

| Fit outcome | Count |
|---|---:|
| Tied best fits with violations | 4 |
| Unique, zero-violation interior interval excluding the generating weight | 3 |
| Zero-violation left-censored fit excluding the generating weight | 1 |
| Correct containing interval but nonzero violations | 2 |
| Missing response, even though estimated interval contains the generating weight | 2 |

For the middle profile in original history order, both passes with Sam first
yield a clean-looking interval **0.2 to 0.5**, instead of the required **0.5
to 1**. For low/original/pass 1/Sam-first, the fit is **0.1 to 0.2**, instead
of **0.2 to 0.5**. Low/reversed/pass 1/Sam-first is left-censored below 0.1,
despite the history requiring a weight above 0.25. These examples show why
monotonicity alone is insufficient: a wrong answer at a switch can move the
interval without producing a threshold violation. Pooling reversals exposes
some inconsistencies but does not make them disappear.

## Implication for the original pilot and next decision

The software/interface can recover all three supplied weights in this sample.
Informative histories also often work, so neither “the ladder cannot work” nor
“models cannot infer WTR” is supported. However, the current model/procedure
combination can turn the same stated preference evidence into different and
sometimes wrong intervals under equivalent presentations. We cannot yet treat
its natural-social WTR outputs as a clean measurement of stable attributed
valuation. This is narrower and better supported than the earlier uncertainty
between underidentified histories, censored responses and collection errors.

The original histories still provide only upper bounds under a fixed linear
interpretation. Their LOW/HIGH separation remains a theoretical prediction,
not a validation answer. The original pilot would test that prediction and
the attribution of valuation versus ability; it must allow null, reversed,
censored or unresolved outcomes. It would not test the model's own WTR.

**Recommended next development action:** prepare one matched presentation
check on these constructed controls that displays both recipients' payoffs,
including zeros, for each history alternative and current option. Preserve the
fixed rule, information, payoffs, unknown weights, both option positions and
both history orders; compare against the originals with a prospectively fixed
sample and analysis. Do not add the correct weight, interval or a worked
solution. The payoff-mapping errors motivate this candidate; the false
comparisons mean it is not a proven remedy and might fail. This audit does
not configure or authorize another collection, and the same run should not
simply be repeated. No number of additional A/B tests can be guaranteed to
validate the measure.

Before any later pilot release, require a documented assessment of errors'
effects on the planned contrasts and the separate original-prompt review of
ability, willingness and future conditions described in the
[validation plan](validation-before-pilot.md). A favorable social ordering is
never an entry requirement. If the targeted revision remains unreliable,
report that measurement limitation rather than silently converting these
results into validated WTR estimates or relaunching the robustness substitute.

The present diagnostic can be included in the eventual article as a
measurement-development result, with its mixed recovery and error examples.
It should not be described as the original social pilot or full construct
validation. This review launches no model calls and incurs no additional model
usage. The recorded collection used 96,408 input and 26,745 output tokens,
with no cache tokens; these are usage figures, not a billing invoice.

## Offline reproduction

From this repository, without model requests:

```bash
python results/diagnostics/36111049496/audit/verify.py
```

The independent summary is saved in `audit/independent-summary.json`.
`audit/reviewed-summary.json` and `audit/reviewed-report.md` contain the existing
analyser's output after accepting the manual labels. Original reports retain
their original pending-review status so the collection artifact is unchanged.
Use the archived labels, rather than editing the original template or response
file. Neither scoring path repairs errors, selects a pass or discards an order.
