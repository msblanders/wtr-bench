# Fixed measurement diagnostic: run 36099597085

Reviewed 25 September 2026 UTC. **The fixed diagnostic is complete. Stop
further range expansion and repeated calibration under this development
sequence. The current instrument does not support a claim of stable scalar
WTR measurement.** This does not prevent research on the observed response
patterns; it changes what the next study can defensibly claim.

All 156 responses are usable and all 32 final control choices are correct.
Manual review finds correct stated values in **19/20 rule explanations**:
the earlier false-tie error has returned. Five of six combined ladders
remain left-censored at 0.01, and the sixth is unidentified. Clarification
improves adherence to supplied conditions in the returned explanations,
but does not eliminate option-order disagreement.

The 888-item pilot remains unrun, unfrozen and unregistered. No additional
model calls, new diagnostic workflow or pilot dispatch was made during
this audit. The recommendation is to write a narrower prospective pilot
plan with response robustness as a primary outcome before collecting more.

## Provenance and verification

- [Workflow run 36099597085](https://github.com/msblanders/wtr-bench/actions/runs/36099597085):
  attempt 1, successful; source `dd9dac7b95210ea6ac0a25fb3db3cfb765cd5842` (v0.4.8).
- Artifact `10848863371`, `inference-measurement-diagnostic-36099597085-1`.
- ZIP SHA-256, matching GitHub's artifact digest:
  `6ec172b7de2b1f0567572cc0464754cc3e4cd84cf21c3eaee6e1f0cb2b74b773`.
- Protocol `measurement-diagnostic-v1`; batch hash `a23f46bf6a51a8c8`.
- Model `claude-sonnet-4-5-20250929`, temperature 0, maximum output tokens
  256, fresh context, `brief_basis` then A/B `answer` under the existing schema.
- [Prospective specification](inference-measurement-diagnostic.md): 32 controls,
  96 range probes, twelve notation checks and sixteen conditional probes.

The eleven original artifact files are preserved byte for byte in
[results/diagnostics/36099597085](../results/diagnostics/36099597085/), with a
`SHA256SUMS` manifest for those originals. Original reports retain their
pending-review labels. Finished manual reviews and independent calculations
are separate files under `audit/`; no original response or score is edited.

The generator reproduces all prompts, sequence and metadata. Configuration,
source revision and full request/response records validate. All 156 request
IDs and message IDs are present and distinct; model IDs match the snapshot.
Every response ended with `end_turn` and passed the strict completion/schema
checks. There are no missing, refused, truncated or unusable replies.
Both Markdown reports, the diagnostic JSON and both review files reproduce
exactly. Usage was **62,848 input and 11,239 output tokens**, with no cache tokens.

The offline audit independently extracts control truth keys and semantic
choices from actual displayed prompt text, checks exact fractional payoffs,
enumerates threshold gaps, and reconstructs matched comparisons. It agrees
with the original report. Run from the repository root:

```bash
uv run --frozen python results/diagnostics/36099597085/audit/verify.py
```

The saved output is [audit/summary.json](../results/diagnostics/36099597085/audit/summary.json).
Manual explanation reviews are assistant-authored, using the pre-response
criteria. They are not independent human ratings, automated prose scores,
or evidence of internal reasoning.

## Controls: correct choices, one recurrent false calculation

| Control block | Correct final choices | Correct stated rule values | Consistent option pairs |
|---|---:|---:|---:|
| Original controls | 24/24 | 11/12 rule explanations | 12/12 |
| Fractional-rule controls | 8/8 | 8/8 rule explanations | 4/4 |
| Total | **32/32** | **19/20** | **16/16** |

The original block comprises eight recipient lookups, four quantity
comparisons and twelve explicit-rule questions. Both displayed orders have
16/16 correct final control answers across the full diagnostic. Every
fractional-rule explanation assigns the correct payoffs, computes the
correct values and selects the greater value. This supports success on
those explicit fractional rules, not universal invariance of social answers
to fractional notation.

The exception is the original `rule_1_20` control with Sam's option second,
item `wtrmeasure-692f040c2725bd7a`. The actual allocations are A: you get 10,
Sam gets 0; B: Sam gets 20, you get 0. With weight 1 on your payoff, the
correct option values are **A = 10, B = 20**. The returned explanation instead
uses `10 + 1(10) = 20` for A and claims a tie with B, then selects B because
Sam is its direct recipient. The final label is correct despite the wrong
payoff assignment and false comparison. Addition of the stated operands is
correct; the error is including Sam's nonexistent 10-point payoff under A.

| Exact A/B case under the explanation protocol | Stated A / B | Final answer |
|---|---|---|
| Initial calibration 36088607405 | 20 / 20, incorrect | A, incorrect |
| Replication 36090248661 | 20 / 20, incorrect | B, correct |
| Replication 36090756872 | 20 / 20, incorrect | B, correct |
| Full debug 36095971330 | 10 / 20, correct | B, correct |
| Current diagnostic 36099597085 | 20 / 20, incorrect | B, correct |

The previous audit correctly described the error as absent in that run,
not permanently fixed. Its recurrence illustrates why final-label accuracy
and checkable explanation accuracy must remain separate. These are repeats
of one exact problem, not five independent problem samples. No change in
request sequence is established as the cause of the differing explanation.

All twenty manual records, including the returned text and the incorrect
stated values, are in
[audit/control-calculations.jsonl](../results/diagnostics/36099597085/audit/control-calculations.jsonl).

## Wider range: bounds tighten, but a common stable switch does not emerge

Sam's payoff ranges from 0.1 to 80 points while your payoff remains 10:
ratios **0.01, 0.05, 0.1, 0.2, 0.5, 2, 4, 8**. Each cell has sixteen
responses: eight ratios in both displayed option orders. Decimal spelling
checks and controls are excluded from these fits.

| Cell | Combined fit | Minimum violations | Disagreeing option pairs | Keep-to-give decreases, Sam first / second |
|---|---|---:|---:|---:|
| Boxes: unable | Tied gaps spanning 0.5–4 | 2 | 2/8 | 1/0 |
| Boxes: unwilling | Left-censored at 0.01 | 0 | 0/8 | 0/0 |
| HIGH/T2, original history | Left-censored at 0.01 | 0 | 0/8 | 0/0 |
| HIGH/T2, swapped history | Left-censored at 0.01 | 0 | 0/8 | 0/0 |
| LOW/T2, original history | Left-censored at 0.01 | 1 | 1/8 | 0/1 |
| LOW/T2, swapped history | Left-censored at 0.01 | 2 | 2/8 | 1/0 |

There are **zero uniquely identified interior fits shared across option
orders in the six cells**. The result is five left-censored fits and one
unidentified fit, not six precise weights. Censored fits with violations
must not be described as clean bounds on a demonstrated constant weight.
All displayed-order fits and rung patterns remain in the original
[diagnostic JSON](../results/diagnostics/36099597085/responses.diagnostic.json)
and [report](../results/diagnostics/36099597085/responses.md).

The upper extension is informative in one limited respect: **unable with
Sam's option second** has a clean interior gap from 2 to 4. In the other
order its best gap is 0.5–2 with one violation: Sam keeps 40 points at ratio
4 but gives you 10 rather than keeping 80 at ratio 8. A single common,
monotone threshold does not reproduce both sequences. Thus the range
extension did not fail to locate every individual-order switch; it failed
to establish a stable shared one.

On numerical range questions, the model predicts Sam keeps in **61/64**
responses. All sixteen numerical responses on the two new lower rungs
predict keeping, including 0.1 points for Sam versus 10 for you. In LOW/T2,
however, the model predicts giving at some larger personal payoffs, producing
two observed keep-to-give decreases. Both LOW-minus-HIGH interval comparisons
remain undetermined. The data do not establish equal latent valuations,
exactly zero concern, or the absence of a valuation mechanism.

The fitted unable bound remains above unwilling's fitted upper bound,
but the unable fit has order disagreement and a monotonicity violation.
This is a qualified descriptive pattern, not a validated scalar contrast.
Same-task ability was not remeasured in this diagnostic, so the full
valuation/same-task-ability dissociation is not a new replicated result here.

## Which comparisons changed

| Comparison | Disagreements / complete pairs |
|---|---:|
| Range option reversal | 5/48 |
| Decimal-anchor option reversal | 0/6 |
| Original binary option reversal | 1/4 |
| Clarified binary option reversal | 1/4 |
| Integer versus decimal spelling at the same allocation | 1/12 |
| Original versus clarified binary wording | 2/8 |
| History reversal, range probes | 3/32 |
| History reversal, decimal anchors | 0/4 |

These denominators answer different questions and overlap in responses;
they are not additive independent failures. The selected item set differs
from the previous 196-question battery, so the raw disagreement proportions
should not be treated as an improvement or deterioration in a general error rate.

The five range disagreements are unable at ratios 2 and 8, LOW/T2 original
at 0.2, and LOW/T2 swapped at 0.1 and 0.2. The three observed decreases are
unable/Sam-first at 4→8; LOW/T2 original/Sam-second at 0.1→0.2; and LOW/T2
swapped/Sam-first at 0.05→0.1. Every flagged valuation pair was inspected;
their item IDs are enumerated in the independent summary.

The notation mismatch is LOW/T2 swapped, Sam first: **“Sam receives 1 points”
predicts giving to you; “Sam receives 1.0 points” predicts Sam keeps.** All
other prompt characters and request settings are the same. The former
explanation emphasizes a small sacrifice; the latter emphasizes a repeated
preference for self-benefit. This is an observed matched disagreement,
not proof that decimal spelling alone caused it: there is one response per
variant in a fixed sequence, and exact-prompt variability is also observed.

Of the 80 byte-identical request anchors from the prior run, **79 retain
their final choices**: 24/24 controls, 47/48 valuations and 8/8 binaries.
The changed anchor is LOW/T2 original at ratio 0.2, Sam second, now predicting
giving instead of keeping. The false-tie control also changes its explanation
despite retaining its final B answer. High exact-prompt agreement therefore
coexists with between-order disagreement and explanation instability.

## Clarification helps conditional fidelity, not overall order stability

Manual reading uses the four labels fixed before collection. All sixteen
responses have a checkable basis: **original 5/8 respect the condition and
3/8 contradict it; clarified 8/8 respect it**. There are no missing/unclear
labels in this batch. The completed records and reasons are in
[audit/binary-conditions.jsonl](../results/diagnostics/36099597085/audit/binary-conditions.jsonl).

In this table, pairs are keyed option first / second. “Yes” means agreeing
or managing; it is not a correctness key.

| Cause and probe | Original choices | Original bases respect condition | Clarified choices | Clarified bases respect condition |
|---|---|---:|---|---:|
| Unwilling, same-task willingness | no/no | 2/2 | no/no | 2/2 |
| Unwilling, different-task ability | no/yes | 1/2 | yes/yes | 2/2 |
| Unable, same-task willingness | no/no | 0/2 | yes/no | 2/2 |
| Unable, different-task ability | yes/yes | 2/2 | yes/yes | 2/2 |

The original unwilling/ability no answer substitutes refusal or failure to
follow through for the stipulated effort. Both original unable/willingness
explanations say the shoulder prevents helping despite the supplied future
ability. These are the same types of contradiction identified previously.

The clarified unwilling/ability pair accepts the effort stipulation and
becomes consistent. The clarified unable/willingness pair also accepts
future ability in both explanations, **but its final judgments diverge**.
One predicts agreement from prior helpful intent; the other predicts
declining from inferred embarrassment despite restored ability. That latter
no answer respects the ability condition. Its extra psychological inference
is not an established fact, but a no answer cannot be relabeled incorrect
merely because the investigator expected agreement.

Clarification therefore removes all three observed premise contradictions
in these returned explanations while moving the location of the one
binary order mismatch. Both versions still have one disagreeing pair out
of four. Choosing whichever wording gives the preferred final social
pattern would obscure this result. These small, assistant-reviewed samples
do not establish a general causal effect of clarification or reveal internal
reasoning; independent human coding would strengthen a later study.

## Decision: end this tuning loop, specify the narrower claim

This batch satisfies the predetermined **stopping rule**, not a pilot
validation gate. It directly tested the proposed fixes. The wider range
and clearer stipulations did not establish a stable WTR instrument across
these debug cases. Do not respond by expanding the ladder again, repeatedly
running this diagnostic, or selecting favorable orders or explanations.

The next useful work is an **offline plan for a pilot of response robustness**:

1. Make option-order agreement, adherence to stated conditions, exact-prompt
   repeatability, monotonicity and censoring explicit observable outcomes.
   Keep final control accuracy separate from stated-value accuracy.
2. Retain the pinned model and explanation/A-B protocol as a documented
   condition. If original and clarified wording are compared, keep them
   as planned experimental conditions; do not silently substitute the
   successful variant case by case.
3. Use unexposed pilot scenarios to assess transfer, with item selection,
   repetitions, denominators, coding rules, request budget and analysis
   fixed before calls. The existing 888-item design is not automatically
   approved or relabeled as this new study.
4. Keep WTR fits exploratory and conditional on their measurement checks.
   Report stable null or contrary social patterns and failures of the
   measurement assumptions. Do not require a desired theoretical ordering
   before allowing the study to proceed.

This recommendation narrows the primary claim; it does not configure a new
batch or assert that the model lacks social inference. The original
baseline/helped/constrained cases, numerical T1, additional scenarios and
other probes were outside this diagnostic. Findings here cannot resolve
their earlier limitations or support broad population/model claims.

## Article implications

The completed development sequence already supports a methods account:
correct final labels can conceal recurring stated-value errors; strong
exact-prompt agreement can coexist with sensitivity to option order and
equivalent number spelling; clearer conditional wording can improve the
stated basis without stabilizing the final social judgment. These claims
concern recorded outputs under specified conditions.

An article can present those findings and the transparent stopping decision
now. It should describe WTR-Bench as an instrument under evaluation, retain
the unsuccessful checks, and distinguish this exploratory development
record from any later frozen pilot. It should not advertise a validated
scalar welfare-tradeoff measure or a completed 888-item study.
