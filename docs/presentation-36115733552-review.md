# Payoff presentation comparison: run 36115733552

**Decision, 25 September 2026 UTC:** Complete-payoff tables improved the
returned explanations in this audit, but produced little net improvement in
final-choice accuracy. Neither presentation met the frozen recovery rule.
Some errors produced orderly but wrong WTR intervals, including a repeated
low-profile interval resembling the middle profile. Both social pilots remain
paused. Stop payoff-display iteration here; do not repeat this batch to seek
a pass or treat the better aggregate score as validation.

This narrows the observable problem. All five wrong table answers state the
correct history interval and current option values, then make an incorrect
comparison or final choice. Correct statements can therefore coexist with an
unreliable choice-derived WTR readout. This is evidence about this model/task
procedure, not evidence that models lack stable welfare preferences or that
social valuation cannot be studied. The task predicts a **described partner's**
choices. Explanations are outputs, not access to internal reasoning.

## Source and integrity

- [Run 36115733552](https://github.com/msblanders/wtr-bench/actions/runs/36115733552),
  attempt 1, completed successfully on source commit
  `ae14ed5146d237cff3cd87705f5c526991e1ace0`.
- The [frozen prospective plan](payoff-presentation-v1.md) scheduled 288 calls:
  two displays, three history profiles, six rungs, two option orders, two
  history orders and two passes. All original-display responses were newly
  collected in this run. Prior responses were not used as the comparator.
- Same model `claude-sonnet-4-5-20250929`, temperature 0, 256 output tokens,
  fresh contexts, structured `brief_basis` then `answer`, no retries. Displays
  were interleaved in fixed hash order within each pass. No pilot scenarios
  were queried. The display package changes layout and explicit zeros
  together, so it cannot isolate the effect of zeros alone.
- [Archive](../results/diagnostics/36115733552/) preserves all 16 original
  artifact files byte-for-byte. `SHA256SUMS` covers originals; later work is
  in `audit/`. ZIP SHA256:
  `7437b020aeeea75e15e6f922185651a68c3697d6cf32755b3a625003ad915028`.
- Frozen source, plan, items, exact request bodies and configuration were
  verified. Original automatic reports, 72 fits, 576 pairs and review packets
  were reproduced. All 288 API request IDs and message IDs are distinct.
- The [offline verifier](../results/diagnostics/36115733552/audit/verify.py)
  derives truth from literal prose/table payoffs using rational arithmetic,
  independently enumerates threshold partitions, and verifies pairs, raw
  parsing, original hashes and label bindings. It reuses the previous audit's
  independent helper functions, not the production estimator. It does not
  automatically classify explanations or make model calls.

The programmed-oracle artifact remains software verification only. Recorded
usage was 149,040 input and 40,484 output tokens, with no cache tokens; this
is usage, not a dollar invoice or account-balance check.

## Choices and recovered intervals

| Outcome | Original wording | Complete-payoff tables |
|---|---:|---:|
| Usable / planned | 144/144 | 144/144 |
| Correct final choices | 138/144 (95.8%) | 139/144 (96.5%) |
| Recovered / planned fits | 24/36 | 28/36 |
| Explanations with calculation/mapping errors | 38/144 | 11/144 |

The last row is assistant coding, described below, and is separate from the
automatic choice/recovery result. Neither display passed the prospectively
specified requirement of all 144 correct usable choices and all 36 complete,
interior, zero-violation fits containing the generating weight. The criterion
has not been relaxed after seeing the data. Its failure alone is not the
reason to stop: the wrong intervals below directly affect the outcome of
interest.

Of 144 matched presentation pairs, **133 were both correct, six improved with
tables, and five became wrong with tables**; none were wrong in both displays.
The net accuracy change is one answer, or 0.69 percentage points. Among 36
matched fits, 18 recovered in both displays, ten only with tables, six only
with original wording, and two in neither. Fits overlap and prompts repeat;
these are descriptive results on a fixed set, not independent participants
or a population estimate of a display effect.

| History profile | Original correct / 48 | Tables correct / 48 | Original recovered / 12 | Tables recovered / 12 |
|---|---:|---:|---:|---:|
| Low: 0.25 < w < 0.4 | 46 | 43 | 8 | 4 |
| Middle: 0.6 < w < 0.9 | 45 | 48 | 6 | 12 |
| High: 1.6 < w < 1.9 | 47 | 48 | 10 | 12 |

The table failures concentrate in the low profile. Gains for the other
profiles do not justify excluding it. Original accuracy was 69/72 in each
pass; table accuracy was 69/72 then 70/72. No pass is selected as preferred.

| Semantic comparison | Original disagreements / complete | Table disagreements / complete |
|---|---:|---:|
| Option reversal | 6/72 | 5/72 |
| History reversal | 4/72 | 5/72 |
| Exact-request repeat | 2/72 | 1/72 |

All planned pairs are complete; no missing-response denominator adjustment
is needed. All 11 wrong answers print A. All six original errors have Sam as
A, while table errors include three with Sam as A and two with Sam as B.
This describes the outputs; it does not uniquely establish a letter-bias
mechanism or justify keeping only one option order.

## The remaining errors change the WTR conclusion

All five wrong table responses state `0.25 < w < 0.4` and correctly map the
current alternatives. The following indices are zero-based positions in the
archived collection. Full prompts, responses and notes are preserved in
[explanation-issues.jsonl](../results/diagnostics/36115733552/audit/explanation-issues.jsonl).

| Index | Table condition | Observable defect |
|---|---|---|
| 25 | Original history, pass 1; A gives Sam 2 | Uses `10w < 4` to conclude `10w < 2`, choosing A instead of B. |
| 116, 228 | Original history, passes 1 and 2; A gives Sam 1 | Uses `10w < 4` to choose 1 instead of the correctly bounded `10w > 2.5`. |
| 113, 149 | Reversed history, passes 1 and 2; B gives Sam 5 | Correctly places A's value `10w` between 2.5 and 4, then chooses A over B's value 5. |

This matters beyond the five individual mistakes:

- Low profile, reversed history, Sam second: **both passes** produce a unique,
  zero-violation interval **0.5 to 1**, rather than the correct ladder interval
  **0.2 to 0.5**. That is the middle profile's expected interval, so the error
  can erase a real low/middle distinction. A monotonicity filter alone would
  accept this wrong result.
- Low profile, original history, Sam first, pass 1: always keeping produces a
  left-censored interval below 0.1, despite the history requiring `w > 0.25`.
- Other table failures include four tied fits and one containing interval
  with a violation. The eight nonrecovered table fits comprise those five,
  the two wrong interior intervals and the one censored fit. They are
  overlapping analyses of the same responses, not eight independent errors.

Original wording also produces five wrong intervals, five tied fits and two
containing intervals with violations. Its wrong answers occur at indices
64, 95, 134, 198, 223 and 287. Errors include assigning a payoff from a rejected
alternative, misreading a giving history and false comparisons such as
`10w < 9 < 5`. Tables reduced these explanation defects overall without
establishing a dependable final-choice readout.

## Separate explanation audit

All 288 records have response-bound labels accepted by the production review
validator; none remain pending. Coding is by the assistant, unblinded to the
prompt, reference bounds and final answer. There is no independent human rater
or inter-rater reliability estimate.

There were **181 fresh reviews of distinct prompt/raw-response combinations**,
38 exact duplicates of those combinations within this run, and 69 responses
whose prompt and full raw text exactly match previously reviewed records
from run 36111049496. The latter labels were reused only after verifying both
identities and the prior review binding; prior notes were consulted. Every
current response has its own current digest and review ID, with the reuse
source recorded. This is disclosed reuse of assistant judgments, not a new
independent rating. All choice scores use current-run API responses.

| Display | Consistent | Calculation/mapping error | Errors despite correct final choice |
|---|---:|---:|---:|
| Original | 106 | 38 | 32 |
| Tables | 133 | 11 | 6 |

All other rubric categories have zero labels. Calculation/mapping has priority
when a response also contains an inference defect; zero in inference-only
does not establish the absence of inference errors. Loose but entailed bounds
are allowed when the comparison remains supported. An incorrect calculation
followed by an explicit repair remains an error, with the repair noted.

The eleven table error labels comprise the five wrong choices above and six
correct choices with flawed text. Four (44, 118, 203, 282) use false strict
boundary comparisons such as `18 > 0.9 × 20` or `0.6 × 20 > 12`, although the
stated weight bounds and final decisions are correct. Two (180, 190) make
incorrect intermediate claims before repairing the comparison and choosing
correctly. These are not counted as additional wrong final answers.

See the [reviewed report](../results/diagnostics/36115733552/audit/reviewed-report.md),
[labels](../results/diagnostics/36115733552/audit/explanation-labels.jsonl) and
[independent summary](../results/diagnostics/36115733552/audit/independent-summary.json).

## Decision before any further collection

End this display comparison. There is no evidence-based reason to expect
another cosmetic revision or unchanged repeat to settle the problem. Preserve
both displays, every profile, all reversals and both passes. Do not replace
wrong final answers with the correct statements in their explanations,
majority-repair this run, or select only the best-performing cells.

The next decision concerns **how to read out inferred valuation while
accounting for demonstrated choice errors**. Offline work should first specify
the resolution needed for the original social contrasts and test whether a
proposed scoring/error model can distinguish the known profiles without
discarding these observed failures. The clean-looking wrong intervals show
why checking for orderly ladders alone is insufficient. A revised method
selected using these data would remain exploratory until prospectively tested
on fresh known-answer cases; rescoring this run cannot validate it.

Alternatively, a new diagnostic could separately elicit history constraints
and test execution of a supplied constraint, but that would be a newly
specified measurement procedure needing its own justification and fixed
validation plan. It must not impose a known numerical weight on the natural
social stories. No such collection is configured or authorized by this audit.

Retain the original question about partner valuation versus ability, along
with the [remaining prompt-review and identification work](validation-before-pilot.md).
Different upper bounds in the original histories do not force different
inferred weights; null, reversed or unresolved social contrasts remain valid
possible findings. Neither the original 888-item pilot nor the proposed
816-request robustness pilot is released. No additional model calls were made
during this audit, and there is nothing new to click Run for.

To reproduce the independent checks without API calls:

```bash
python results/diagnostics/36115733552/audit/verify.py
```
