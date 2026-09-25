# Payoff presentation diagnostic: prospective plan v1

Specified 25 September 2026 UTC, before collecting any responses to this
comparison. The researcher authorized this follow-up to the
[known-partner recovery audit](recovery-36111049496-review.md).
**288 scheduled requests, once. Both social pilots remain on hold.**
This is a prospective GitHub specification, not an external preregistration.

## Purpose and interpretation

The previous recovery run answered all 72 explicit-weight questions correctly,
but made six wrong history choices and produced one unusable history response.
Five wrong responses stated the correct weight interval before an incorrect
comparison or payoff mapping. All six wrong choices occurred with Sam first;
their reversed options were correct. Some correct choices had faulty
explanations. A presentation revision is a candidate remedy, not a proven one.

Compare the original history prompts with a uniform revision showing both
recipients' payoffs, including zeros, in every past alternative and current
A/B option. This tests the **combined display revision**: explicit zeros and
tabular organization change together. It cannot isolate either feature's
individual effect, reveal internal reasoning, or establish full social
construct validity. False numerical comparisons may persist even if mapping
improves. The target remains the original partner-inference measurement task,
not a substitute robustness pilot or the model's own welfare preferences.

## Fixed sample and matched presentations

Use all history cases from the recovery diagnostic, including cases previously
correct. Do not select only the six observed failures, remove a profile or
choose the better option/history order. The explicit-weight arm is omitted
because it already passed and is outside this targeted history comparison.

| Factor | Levels |
|---|---|
| Presentation | Original prose; complete-payoff tables |
| Constructed partner profile | Low, middle, high; private generating weights 0.3, 0.75, 1.75 |
| Current own payoff / your payoff | 1/10, 2/10, 5/10, 10/10, 15/10, 20/10 |
| Current option order | Sam as A; Sam as B |
| History order | Original; reversed |
| Exact-request repetitions | Two, each in a fresh context |

There are **144 distinct prompts and 288 requests**: 144 per presentation.
Every original has one matched table version within each pass. Each original
prompt and API body is byte-identical to its corresponding history request
from the previous diagnostic. Original records are linked through
`source_item_id` and `source_template_id`; historical responses are never
substituted for current comparison responses. All 288 calls are new.

Both presentations repeat exactly in pass 2. All first-pass requests precede
pass 2; presentations are interleaved within each pass by the fixed SHA256
ordering of protocol name and request ID. There is no selection of order
after results, and the two matched prompts do not share a conversation.
This fresh paired baseline helps avoid attributing differences between runs
to the new presentation. Two passes are not independent model participants
or replication across dates, deployments or model snapshots.

The original rule, identity (Sam), evidence, payoffs, chosen alternatives,
strict preference/no-ties conditions, question and answer instruction remain.
The revised display replaces only the two history descriptions and the A/B
payoff lines with tables whose columns are **Points for Sam** and **Points for
you**. History alternatives remain in their original own/other order and use
local outcome labels 1/2; their stated chosen outcome is preserved. History
blocks are reversed where specified. Current A/B rows preserve the specified
option reversal. The original sentence about an unnamed recipient receiving
zero is retained, although the table now displays every zero explicitly.

No worked example, computed value, inferred interval, hidden generating
weight, profile label, expected answer or repetition ID enters a request.
Neither presentation adds a stronger behavioral assumption. The fixed linear
rule was already part of these constructed controls and must not be added to
natural social stories to force the intended social effect. The six held-out
social scenarios and original construction sets are not model-facing here.

| Profile | Historical giving choice | Historical keeping choice | Identified weight interval | Correct ladder interval |
|---|---|---|---|---|
| Low | Give you 20 over keeping 5 | Keep 8 over giving you 20 | 0.25 < w < 0.4 | 0.2 to 0.5 |
| Middle | Give you 20 over keeping 12 | Keep 18 over giving you 20 | 0.6 < w < 0.9 | 0.5 to 1 |
| High | Give you 20 over keeping 32 | Keep 38 over giving you 20 | 1.6 < w < 1.9 | 1.5 to 2 |

Each current ratio lies outside the compatible history interval. Thus its
truth key follows for every compatible weight; matching one private point
value is not required. The programmed-oracle artifact checks software only.

## Collection, cost exposure and stopping

- Pinned `claude-sonnet-4-5-20250929`, temperature 0, 256 output tokens,
  API-enforced ordered JSON `brief_basis` then A/B `answer`. Same system
  instruction and answer instruction as the recovery diagnostic. No format,
  model, output-budget or worked-reasoning comparison is added.
- Preserve the strict acceptance rule: one text block, `end_turn`, exactly
  those ordered fields, nonempty string basis and A/B answer. Malformed,
  refused or truncated outputs are unusable. No repair from explanations.
- Make all 288 planned calls despite wrong/unusable answers. Zero SDK retries;
  no fallback model, adaptive stopping for accuracy or automatic extra batch.
- Transport errors, wrong model IDs, duplicate API IDs or freeze violations
  stop collection. Save any received response before an integrity stop;
  upload partial data even if collection or inspection fails.
- One manual workflow job, 60-minute operational timeout. API calls use the
  existing `ANTHROPIC_API_KEY` and its billing account. Maximum allocated
  output is **73,728 tokens**; input is additional and table prompts are longer.
  This is 288 calls rather than 216 previously; no fixed dollar cap or account
  balance is asserted. Preparation and offline tests make no model requests.
- Click Run workflow once; one job includes both presentations and passes.
  GitHub Re-run jobs starts another collection, not a resume. Inspect partial
  data before considering a local exact resume. Saved responses, including
  unusable ones, are never repeated by resume. An unrecorded request after a
  transport error may already have been billed; document that uncertainty.

## Prespecified analyses

1. **Matched final-answer outcomes:** 144 presentation pairs, ordered original
   then explicit payoffs. Among complete usable pairs, count both correct,
   explicit-payoffs-only correct (gain), original-only correct (regression),
   and both incorrect. Report net gains and accuracy difference over complete
   pairs. Separately report each presentation's correct/144 planned, usable,
   wrong, missing and unusable, and the difference in correct/planned. An
   incomplete pair is not evidence of a corrected or regressed usable answer.
2. **Containing-interval recovery:** 36 fits per presentation, 72 total:
   three profiles × two history orders × two passes × pooled/Sam-first/Sam-second.
   Use the existing estimator and report every bound, censoring state, tied
   fit, violation and missingness. These fits overlap. Highlight changed or
   apparently coherent wrong intervals; monotonicity is not correctness.
3. **Within-presentation consistency:** each presentation has 72 planned option
   pairs, 72 history pairs and 72 exact-repeat pairs. Report disagreements /
   complete pairs and complete / planned. All comparisons use semantic
   keeping/giving, not printed A/B changes. Preserve pair-level records.
4. **Separate explanation audit:** review all 288 scheduled outputs with the
   rubric below, including correct final choices. Report by presentation.
5. **Breakdowns:** planned choice counts by presentation/profile/history/pass/
   option cell; paired gains and regressions by profile, rung, history order,
   pass and option order. Report stop reasons and actual input/output/cache
   tokens. All denominators remain fixed; missing records are not discarded.

The primary comparison is descriptive on this fixed development set. Do not
treat 288 calls or 72 overlapping fits as independent samples for population
significance. Do not select one factor level or the better repetition as the
result. The old run remains context, not the contemporaneous comparator.

Apply the previous conservative **choice clear-pass** concept separately to
each presentation: all 144 planned responses usable/correct and all 36 fits
complete, interior, zero-violation and containing the generating weight.
Incomplete collection is incomplete; any other complete result is mixed or
failed. This is a known-task engineering criterion, not a zero population
error guarantee or a revised pass for the previous 216-request experiment.
Do not relax it after seeing responses. Paired improvement and clear pass are
different outcomes: report both, even when improvement falls short of a pass.

## Explanation review and coding boundaries

Use the existing response-bound review IDs, raw text and reference intervals.
The packet includes both prompt and presentation, so review is unblinded.
Disclose the reviewer; assistant coding is not independent human coding or
an inter-rater reliability study. Do not equate a correct answer with a
correct explanation, or treat returned text as internal reasoning.

| Label | Criterion |
|---|---|
| `consistent` | Checkable claims agree with the supplied evidence, payoff mapping, rule and final choice; no uniquely known hidden weight is asserted. |
| `incorrect_calculation_or_mapping` | Incorrect calculation, payoff/recipient mapping, inequality, or contradiction between comparison and final choice. |
| `unsupported_inference` | An unwarranted inference, such as a uniquely identified weight or a rule contrary to the stipulated fixed rule, without a higher-priority calculation/mapping defect. |
| `unclear_or_no_checkable_basis` | Usable output with insufficient relevant, checkable justification. Absence of an obvious error alone is not a consistent label. |
| `unusable_or_missing` | No usable parsed response. Do not reconstruct an answer from text. |

Calculation/mapping takes precedence over unsupported inference; record all
defects in notes. A true, looser bound is permitted if it suffices for the
decision and no false equality or exact characterization is asserted. A
qualified compatible illustrative weight need not equal the private weight.
Record incorrect displayed payoff mappings even when their resulting loose
inequality is true. If the response repairs an initial error, note the repair
but retain the included error under this rubric. Mathematical value described
as “points” can be utility shorthand when formula and mapping are otherwise
correct; note any ambiguity rather than inventing a physical transfer.
Apply these rules equally across presentations. Any later coding refinement
must be disclosed with a sensitivity count, not silently substituted.

Copy the template to a separate labels file. Keep IDs/digests, supply an
allowed label and supporting notes, and inspect with `--labels PATH`.
Unknown/duplicate IDs, stale digests, invalid labels, missing notes and labels
inconsistent with response usability are rejected. Uncoded records stay
pending. Accepted labels are archived; the original template is not a labels
file, and must not be overwritten with manual coding.

## Decision after review

- If the new presentation passes choices and explanation review is adequate,
  it supports recovery with that presentation on these controls. Complete the
  original-prompt review of ability/willingness and future conditions, plus
  assessment of effect resolution, before preparing any social pilot.
- If accuracy improves but errors still change intervals or remain dependent
  on reversals, report a mixed result. Improvement alone does not validate the
  scalar measure or authorize a pilot. Assess the error's effect on the intended
  contrasts rather than just the aggregate accuracy percentage.
- If both presentations pass, this run supplies limited evidence of recovery
  but no observed advantage for the revision; the earlier failures remain.
  If the revision does worse or leaves the defects unresolved, record that
  outcome and do not rerun or tune displays until a favorable result appears.
- No result automatically releases either pilot. Any additional development
  collection requires a specific documented reason and a new fixed plan;
  there is no promised number of tests after which validation must succeed.

The original numerical histories still imply upper bounds rather than known
distinct weights. LOW/HIGH separation and valuation-versus-ability effects
remain scientific hypotheses, not validation keys. A future original pilot
must permit null, reversed, censored and unresolved outcomes.

## Freeze, files and reproduction

`protocols/payoff-presentation-v1.json` binds the plan, source implementation,
ordered item JSONL, request bodies and settings. Generation, collection,
resume and inspection reject changed configuration. Post-collection status
belongs in a separate audit/runbook, not edits to this plan or raw results.

The artifact contains items, protocol, manifest, plan, source revision,
dependencies, matched prompt examples, separately labeled programmed-oracle
fits, raw responses/request bodies/API IDs, summary, 72 fits, 576 total pair
records, explanation packet and any accepted manual labels.

```bash
uv run --frozen python -m wtrbench.payoff_presentation generate
uv run --frozen pytest -q tests/test_payoff_presentation.py tests/test_recovery_run.py
```

These commands are offline. Collection is the single manual **Inference
payoff presentation diagnostic** workflow; the researcher will launch it.
