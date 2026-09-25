# Fixed response robustness pilot, version 1

**Status at specification: ready for its first collection; no pilot responses examined.**
This is the next pilot, not another prerequisite calibration. It replaces the
unrun 888-item scalar-WTR pilot as the next collection. The earlier design,
code, diagnostic records and negative findings remain available.

## Purpose and scope

The primary question is whether the model's observable responses are robust
to option reversal, respect expressly stipulated conditions, and repeat under
identical requests. A useful result can include instability or failure; it
does not require the theoretical WTR ordering to appear.

Development already found usable outputs and often correct control choices,
but recurrent false calculations, conditional errors, censored/tied ladders
and option sensitivity. See the [completed measurement audit](measurement-36099597085-review.md).
Those findings do not validate a scalar social measure. WTR fits in this pilot
are exploratory descriptions, not estimates of an established latent trait.

This plan is prospectively specified in GitHub before these pilot calls. It is
not an external preregistration or a confirmatory test of the original theory.
The pilot uses a deliberately narrower question, informed by the development
results; that change must be disclosed in any article.

## Fixed sample and budget

One model, one workflow, **816 requests: 408 distinct prompts repeated twice**.
Both passes are part of this pilot and run automatically in the same job.

| Block | Construction per pass | Per pass | Total |
|---|---|---:|---:|
| Known-answer controls | Original 8 lookup + 4 quantity + 12 rule items | 24 | 48 |
| Attribution valuation | 6 scenarios × 2 causes × 6 ratios × 2 option orders | 144 | 288 |
| Conditional binary probes | 6 scenarios × 2 causes × 3 probes × 2 wordings × 2 option orders | 144 | 288 |
| Numerical-history valuation | 2 sets × 2 diagnostics × 2 totals × 2 history orders × 3 ratios × 2 option orders | 96 | 192 |
| **Total** | | **408** | **816** |

The six original tasks are couch, faucet, spreadsheet, translate, dog and
presentation. Causes are unable and unwilling. Binary probes are willingness
on the same task, ability on the same task and ability on a different task.
The numerical construction sets are set0 and set1, with LOW/HIGH evidence and
T1/T2 totals. Form 0 fixes the existing names and relationships; no name effect
is separately estimated. The two construction sets are distinct designs, not
random samples from a population of situations.

Original social items are selected directly from the existing generator.
Their underlying item IDs and original prompts do not occur in archived
development item artifacts checked before collection. Thus they are held out
from the **recorded development calls**, not known to be absent from training
or otherwise unknown to the model. The reused controls are not held out.

Attribution ratios remain 0.1, 0.2, 0.5, 1, 1.5, 2. Numerical ratios are the
fixed subset 0.1, 0.5, 2, to cover two construction sets and repeated/history
comparisons within the budget. Three numerical rungs give coarse WTR bounds;
they do not support fine threshold estimation. There is no range expansion.

Excluded from this collection: the development boxes task and debug numerical
set; baseline, helped and constrained causes; different-task willingness;
set0x2 scaling; decimal/integer notation manipulation; additional models,
forms, names and temperatures. Claims cannot generalize over those factors.

## Wording and counterbalancing

All social questions preserve the original supplied evidence and choices.
Only the response instruction changes to the already tested brief explanation
then final A/B protocol. Every binary question additionally has one clarified
variant, with the following sentence inserted immediately before its question:

- Willingness: “For this question, take NAME's availability and ability to do
  this task at that future time as given, regardless of any earlier limitation.”
- Ability: “For this question, take NAME's effort and available time as given,
  regardless of any earlier willingness to help.”

Both original and clarified variants are retained for every selected task and
cause. These instructions stipulate opportunity/effort, not willingness or
successful performance. No numerical social weight is demanded or supplied.

Every social item has both option orders. Numerical histories also have both
evidence orders. Pass 2 repeats the exact request body for each template,
including system instruction and model settings, with a fresh independent
conversation and separate API request. Explanations are not carried forward.

Each pass starts with its 24 controls, then 384 social requests. Within each
block, order is determined by SHA-256 sorting with seed
`2026-09-25-response-robustness-v1`, pass number and template ID. Passes use
different fixed orders. Reversals are interleaved by hash ordering; chance
adjacency is possible.
The sequential passes may conflate time/backend variation with repeatability;
they are not independent scenario replications or a test across dates/models.

## Collection protocol and stopping rule

- Model: `claude-sonnet-4-5-20250929`; temperature 0; maximum 256 output tokens.
- API-enforced JSON object, exactly `brief_basis` then `answer`, with A/B enum.
  The basis requests one or two sentences; length is not an extra scoring gate.
- One fresh-context call per scheduled item, no SDK retries and no fallback.
- An answer is usable only if the strict existing parser accepts a nonempty
  basis and A/B final field, in order, with one text block and `end_turn`.
  Truncations/refusals/malformed replies remain unusable, even if text suggests
  an answer. Never repair the final choice from the explanation.
- Complete the fixed 816 calls despite wrong controls, unusable answers or
  disagreements. There is no accuracy threshold or calibration gate.
- A transport error, unexpected returned model, duplicate API ID or changed
  protocol stops further calls for technical integrity. Preserve partial data.
  The job has a 90-minute operational timeout. Do not automatically restart a
  failed workflow; inspect its artifacts first. Exact local resume can skip
  saved responses, including unusable ones. An uncertain server-side result
  after a transport failure must be documented before resuming; actual billed
  requests may differ from locally recorded completions. Do not replace a
  partial run with an unreported fresh run.
- No additional batch, changed wording, extra rung or repeat is triggered by
  an undesired result. Finish analysis of this pilot before proposing a new study.

Maximum allocated output tokens are 816 × 256 = 208,896; input tokens are
additional. This is a request/output ceiling, not a monetary quote. API usage
is billed to the repository's configured key. No API calls occur in CI tests.

## Prespecified primary outcomes

1. **Option-order disagreement:** compare the semantic choice after remapping
   A/B. Report disagreements / complete pairs, complete / planned pairs, and
   incomplete pairs. There are 384 planned social pair instances across the
   two passes (144 attribution valuation, 144 binary, 96 numerical). Separate
   passes, scenarios/sets, causes, probes, wordings and numerical cells remain
   available. A fixed-letter responder must be exposed by this measure.
2. **Exact-request repeatability:** compare final semantic choices for each
   template between passes. There are 384 social and 24 control pairs. Do not
   score wording similarity of explanations as repeatability. Report the same
   completeness and disagreement denominators as above.
3. **Adherence to stated conditions:** manually code all 288 returned binary
   explanations using the rubric below, including missing/unusable records.
   Report all four categories and pending reviews by task, cause, probe,
   wording and pass. A final yes/no choice is not a correctness key.

These are descriptive outcomes of the fixed question set. Do not compute a
pooled binomial confidence interval treating the many prompts or repeats as
independent scenarios. Report the six scenarios and two numerical sets
separately, with counts, rather than implying a large population sample.
No minimum percentage is designated as a “validated benchmark” threshold.

## Manual condition-coding rubric

Review the actual prompt and its returned basis, not a predicted social answer.

| Label | Rule |
|---|---|
| `respects_condition` | The expressed justification is compatible with the stipulated future ability/availability or effort/time; it does not use an excluded limitation to determine the answer. |
| `contradicts_condition` | The expressed justification relies on inability/unavailability when these are stipulated, or lack of effort/time when these are stipulated. Quote the conflicting claim and condition in notes. |
| `unclear_or_no_checkable_basis` | A usable output is too vague, irrelevant or ambiguous to establish adherence or contradiction. Mere absence of an explicit contradiction is insufficient. |
| `unusable_or_missing` | There is no usable parsed response. Preserve this category in the planned denominator. |

Someone may decline despite being able, or fail despite trying. Those answers
can respect the condition. A different-task ability judgment need not agree
with a same-task ability judgment. Review only what the returned text claims;
it is not a window into the model's internal reasoning.

The exported review template shuffles records by a fixed opaque review ID and
omits final labels, pass and variant metadata. It includes the actual prompt,
which reveals its wording; the review is not fully blinded. A separate key
restores analysis metadata. Each label is bound to the precise response digest.
Copy the template to a separate labels file, enter one allowed label and
supporting notes per item, then inspect with `--labels`. Missing labels remain
pending. Do not report an adherence rate before reviewing the records.

The first coding pass is an analyst review. Do not call it independent or
inter-rater reliable without a second reviewer. Preserve disagreements and
adjudication notes if a second review is later obtained; disclose who coded.

## Secondary outcomes and exploratory WTR

- Wording sensitivity: 144 original/clarified binary pair instances, matched
  on source question, option order and pass.
- History-order sensitivity: 96 numerical pair instances, matched on all
  other factors. Report separately from option-order sensitivity.
- Binary yes/no distributions by scenario/cause/probe/wording/pass, without
  truth-scoring the social answer or requiring a theoretical dissociation.
- Missing, unusable, refusal and truncation counts; stop reasons and token use.
- Controls: final accuracy among usable and out of all 48 planned, with kind,
  pass and option position retained in raw review rows. Separately review all
  24 rule explanations against exact computed values. Correct final choices
  do not establish correct calculations. Explicitly revisit the known
  `rule_1_20` / Sam-second false-tie explanation in both passes.
- Apply the existing threshold estimator separately to each valuation cell
  in each pass, by option order and pooled: 56 cells, 168 fits. Retain all
  censored and tied fits, violations and missing observations. Also count
  observed downward steps between adjacent planned rungs in each option
  order; missing rungs do not become adjacent. A complete zero-violation
  interior fit is a descriptive property, not construct validation.

Any WTR comparisons across causes, LOW/HIGH evidence or totals are exploratory.
Do not collapse passes into extra rungs, mix history orders or selectively
report the order/wording that produces a desired estimate. No confirmatory
theoretical sign test or new ladder-selection rule is specified here.

## Freeze, artifacts and interpretation

`protocols/response-robustness-pilot-v1.json` binds the ordered item JSONL,
request settings, this plan's SHA-256 and the generation configuration. The
runner refuses a mismatch. The collection artifact includes all 816 planned
items, this plan, the manifest, source revision, dependency versions, raw
API records, reports, pair-level records, ladder fits and review materials.
Future status updates belong in the runbook/README, not this frozen plan.

Report both the initial measurement failures and this revised research
question. A defensible article can describe how reliably an LLM handles
these controlled social-inference prompts and where it fails. Claims that
the benchmark measures a stable welfare weight require additional evidence;
this pilot neither assumes that claim nor requires a positive result.
