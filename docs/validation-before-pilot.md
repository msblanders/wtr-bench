# Validation before any pilot

**Decision, 25 September 2026 UTC:** The researcher requested measurement
validation before any pilot. Both the original 888-item study and the newly
configured 816-request robustness study are on hold. The latter workflow's
collection job is disabled and its CLI refuses `run` before creating an API
client. Its frozen plan is retained as a historical proposal, not current run
authorization. Do not edit that plan to conceal the change in direction.

The objective is to establish whether the original inference task can support
an interpretable test of social valuation versus ability. The desired social
effect is not a prerequisite for running that test. A procedure that measures
adequately can produce a null, reversed, censored or inconsistent social result.
No validation plan can guarantee that this instrument/model combination will
meet the requirements or recover the proposed theoretical pattern.

## What needs establishing

1. The software recovers the right interval from programmed threshold choices.
   Existing synthetic checks cover this; it is not evidence about an LLM.
2. The actual LLM, using the same answer interface and ladder, recovers known
   partner preferences in controlled cases where the answers are determined.
   A few arithmetic choices on each side of an explicit weight do not fully
   test this. The [completed recovery diagnostic](recovery-36111049496-review.md)
   now supplies that end-to-end test: explicit weights passed; history
   recovery was mixed, including wrong intervals and presentation sensitivity.
3. The original social prompts convey the intended evidence and future
   conditions, without a clear alternative explanation introduced by wording.
   This requires prompt-level review and condition comprehension checks,
   separately from whether the model endorses the social prediction.
4. The planned scalar or interval outcome has enough resolution for the claim.
   A consistent endpoint pattern yields a bound, not an invalid observation.
   If both comparison groups have overlapping bounds, that particular contrast
   is unresolved; it is not evidence of equality or automatically an instrument
   failure. Do not extend ranges until the desired ordering appears.

The claim concerns **the weight the model attributes to a described partner**.
It does not concern the model's own welfare preferences or prove an internal,
persistent scalar representation.

## An identification limit in the original histories

The original aggregate prompts say that the partner kept the payoff in both
observed choices. Under the assumed fixed linear value rule
`value = own points + w × other points`, keeping at ratio `own/other = r`
only constrains `w <= r` if the observed choice is weakly optimal. Two keeping
choices therefore imply `w <= min(r1, r2)`; with nonnegative weights, the
compatible set is `[0, min(r1, r2)]`.

The design already described these as upper bounds. What needs correcting is
the interpretation of the diagnostic outcomes: different upper bounds do not
logically require different inferred weights, or an interior switch. For the
debug set, LOW permits weights up to 0.5 and HIGH up to 1.5. A weight of 0.05
is compatible with both. So are LOW = 0.3 and HIGH = 0.1, which reverse the
predicted ordering. The LOW/HIGH ordering is a substantive inference hypothesis
that depends on assumptions such as the observer's prior; it is not a known
answer and must not be a measurement-validation pass criterion.

An offline audit checks this for all sixteen original numerical cells,
including construction, scaling and debug sets. This does not retract the
observed option-order disagreements or contradictions of stated conditions;
those are separate problems from underidentified history evidence.

## The missing experiment: known-partner recovery

**Status: collected once and audited, run 36111049496.**
The [review](recovery-36111049496-review.md) records 72/72 correct explicit
choices and 18/18 recovered fits, versus 137/144 history choices and 24/36
recovered fits. Five of six wrong answers state the correct history interval
before failing the current comparison or payoff mapping. The frozen clear-pass
rule was not met; these defects can change the inferred interval. All 216
explanations are separately reviewed. Do not rerun to seek a preferred result.
Both social pilots remain on hold. The [frozen collection plan](known-partner-recovery-v1.md)
and exact original prompts are unchanged. The generator is
`src/wtrbench/validation_recovery.py`; the design below records the completed test.

Use the same Sonnet snapshot, temperature 0, 256-token limit, fresh contexts,
brief explanation then structured A/B answer. Retain the original six ratios:
0.1, 0.2, 0.5, 1, 1.5, 2. No new range expansion or format comparison.

| Arm | Information supplied | What a pass establishes |
|---|---|---|
| Explicit weight | A constructed partner follows a fixed linear rule; its weight is supplied. | The model can execute the rule across a complete ladder through this response interface. |
| Choice history | The same fixed linear rule is stated, but its weight is withheld. A giving choice and a keeping choice bracket it. | The model can use the history to predict new choices whose answers are identified under the stated assumptions. |

The explicit fixed-rule assumption makes these **positive controls**, not
substitutes for the natural social scenarios. Do not add that assumption or
the correct weight to the original social questions in order to manufacture
the predicted result. Passing the controls does not validate spontaneous
social attribution, demonstrate a latent mechanism, or rule out every shortcut.

Three constructed profiles use private weights 0.3, 0.75 and 1.75. In the
history arm, the prompt never includes those values, profile labels, expected
answers or repetition identifiers. Each history has a gift choice at the
lower ratio and a keeping choice at the upper ratio:

| Private weight | Give at own / other payoff | Keep at own / other payoff | Interval recoverable on original ladder |
|---|---|---|---|
| 0.3 | 5 / 20 | 8 / 20 | 0.2 to 0.5 |
| 0.75 | 12 / 20 | 18 / 20 | 0.5 to 1 |
| 1.75 | 32 / 20 | 38 / 20 | 1.5 to 2 |

All test ratios lie outside the history's compatible interval, so every scored
choice is determined for **every** weight consistent with that history. No
point estimate is required to equal the private weight: an interval containing
it is the appropriate recovery target. The midpoint is only a summary.

Fixed budget: **216 requests**, 108 templates in two passes.

- Explicit: 3 profiles × 6 rungs × 2 option orders × 2 repeats = 72.
- History: 3 profiles × 6 rungs × 2 option orders × 2 history orders × 2 repeats = 144.

Histories contain integer payoffs. Both option orders and both history orders
are retained. Exact prompts repeat in fresh contexts; fixed hash ordering
differs between passes. No metadata with the answer enters the request body.
Generating the files makes no API calls and supplies no new model evidence.

## Interpretation and decision rule, specified before collection

The analysis report uses a deliberately conservative **clear-pass** rule:
all 216 choices usable and correct, with all 54 by-order and pooled ladder
fits recovering their containing interval without violations in either pass.
This also entails agreement across the planned option/history reversals and
repeats. It is an engineering criterion for this small constructed set, not
a confidence statement that the model's population error rate is zero.

Review all returned explanations separately for arithmetic, recipient mapping
and use of the supplied conditions. A correct final field with a false
calculation is not a clean explanation result. Explanation review is not a
claim about hidden reasoning, and the automatic choice gate cannot replace it.

| Observed outcome | Consequence |
|---|---|
| Explicit-weight arm has errors or fails recovery | The model/procedure combination has an execution or response problem even before preference inference. Inspect the exact errors; do not interpret social WTR fits as a clean test. |
| Explicit arm passes; history arm fails | The difficulty is exposed when recovering preferences from supplied evidence. This localizes a functional failure but does not uniquely identify its internal cause. |
| Both arms pass; natural histories remain censored | Saturation is compatible with a low inferred weight or insufficient original evidence. Do not declare general elicitation failure solely because a switch is absent. |
| Both arms pass; natural questions remain order-sensitive or violate conditions | The readout works on constructed controls, but transfer to those social prompts remains problematic. Examine semantic/evidence differences before the original pilot. |
| Both arms pass and prompt/condition review is adequate | Prepare the original theory-focused pilot with frozen contrasts, interval interpretation and missingness rules. A null or reversed theoretical result must remain possible. |

A small number of errors is a **mixed result requiring assessment of its
effect on the estimand**, not an automatic instruction to rerun until perfect.
Report which arm/profile/order failed and whether the interval conclusion
changes; do not silently relax the clear-pass rule. Do not choose the best
repeat, discard a profile or replace errors with the expected answer.

The diagnostic ran once through its manual collection workflow.
Any follow-up must target a specific failure demonstrated in that run and be
specified separately. There is no automatic second batch or pilot dispatch.
If the basic task remains unreliable, acknowledge that outcome rather than
guaranteeing that additional calibration will eventually validate it.

## Completed follow-up: matched payoff presentation

Following the recovery audit, the researcher authorized a targeted display
comparison. **Run 36115733552 is complete and [audited](presentation-36115733552-review.md).**
The [prospective plan](payoff-presentation-v1.md) remains unchanged: 288 requests
compared 144 newly collected original history responses with matched tables
showing both recipients' payoffs, including zeros. All profiles, rungs,
option/history reversals and two passes were retained, with the same model,
fixed-rule evidence and answer protocol.

Original wording scored 138/144 and tables 139/144: six paired improvements,
five regressions. Recovered fits were 24/36 and 28/36; explanation error labels
were 38 and 11 in the unblinded assistant audit. All five wrong table answers
state correct history bounds and current values before choosing incorrectly.
In both passes, one low-profile table condition yields a unique, monotonic
but wrong interval of 0.5 to 1 instead of 0.2 to 0.5. These errors can change
the valuation contrast, not merely its response-format quality.

Neither display meets the frozen rule. Stop payoff-display iteration here.
Before any new collection, specify the required effect resolution and assess
whether a proposed readout/error model can handle the demonstrated failures
without discarding them. A revised method selected on these data would need
fresh prospective validation; rescoring this batch is exploratory. Do not
repair final choices from explanations or quietly adopt a different measure.
Both pilots remain paused, and no new run is requested. The [runbook](inference-runbook.md)
retains historical collection instructions and offline reproduction.

## Remaining bridge to the original social pilot

Known-partner recovery is necessary evidence for the proposed interpretation,
not sufficient construct validation. Keep the six intended pilot scenarios
and construction sets out of model-facing development calls. Before releasing
them, review the original debug items for recipient roles, implicit zero
payoffs, persistence of incapacity, and stipulated future ability/effort.
The past clarification result is relevant evidence, not a universally proven
fix. If wording is changed, use one uniformly specified revision and preserve
the originals. Check premise comprehension independently of the desired
yes/no social answer; inability and unwillingness must not be collapsed.

Do not demand that unable > unwilling on inferred valuation as an entry
criterion; that is the scientific prediction to be tested. Likewise, do not
impose a numerical weight on natural stories, define agreement with a human
rating as numerical ground truth, or infer equality from overlapping bounds.
Decide the intended effect resolution and what unresolved bounds mean before
unfreezing any pilot. This plan restores the original research question; it
does not quietly substitute the robustness study for it.

## Offline reproduction and methodological precedent

```bash
uv run --frozen python -m wtrbench.validation_recovery generate
uv run --frozen pytest -q tests/test_validation_recovery.py tests/test_recovery_run.py
```

The generated `runs/validation-recovery/` contains all 216 scheduled
items, the original-history bound audit and a **programmed-oracle** recovery
report. That report must never be presented as an LLM result. Tests also
check that fixed-letter, always-keep, always-give and missing responders fail.

Kim, Kovach, Lee, Shin and Tzavellas, *Can an LLM Learn Preferences from Choice
Data?*, [arXiv:2401.07345v3](https://arxiv.org/abs/2401.07345v3), uses simulated
choices from known preference primitives and evaluates LLM predictions on new
decisions. It supports the general use of controlled preference-recovery
experiments, not our particular weights, budget or pass criterion. Our two
arms and bracketing construction are proposed adaptations. Existing
[development records](measurement-36099597085-review.md) remain unchanged.
