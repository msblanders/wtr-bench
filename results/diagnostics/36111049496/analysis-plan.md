# Known-partner recovery diagnostic: frozen collection plan v1

Specified 25 September 2026 UTC, before examining responses to this diagnostic.
This implements the [validation-before-pilot plan](validation-before-pilot.md).
**216 scheduled requests, once. Both social pilot proposals remain on hold.**
This is a prospective GitHub specification, not an external preregistration.

## Question and fixed design

Can the model recover a constructed partner's preference interval using the
same six-rung choice ladder and response protocol, first when its weight is
explicitly supplied, then when an informative history constrains it?

The controls explicitly assume a fixed linear value rule:
`value = Sam's points + w × your points`. A recipient not named receives zero.
This assumption defines the constructed task; it must not be imposed on the
natural social scenarios to force a favored theoretical result.

| Condition | Design | Requests |
|---|---|---:|
| Explicit weight | 3 weights × 6 ratios × 2 option orders × 2 passes | 72 |
| Choice history | 3 weights × 6 ratios × 2 option orders × 2 history orders × 2 passes | 144 |
| Total | 108 distinct prompts repeated in fresh contexts | 216 |

Ratios are exactly 0.1, 0.2, 0.5, 1, 1.5, 2, with your payoff fixed at 10.
Sam receives 1, 2, 5, 10, 15 or 20 points in the other option. Sam appears in
both option positions. No names, ranges, output formats or models are selected
adaptively. These controls contain no original held-out social scenarios.

| Private generating weight | Observed gift choice | Observed keeping choice | History supports | Ladder should recover |
|---|---|---|---|---|
| 0.3 | Give you 20 instead of keeping 5 | Keep 8 instead of giving you 20 | 0.25 < w < 0.4 | 0.2 to 0.5 |
| 0.75 | Give you 20 instead of keeping 12 | Keep 18 instead of giving you 20 | 0.6 < w < 0.9 | 0.5 to 1 |
| 1.75 | Give you 20 instead of keeping 32 | Keep 38 instead of giving you 20 | 1.6 < w < 1.9 | 1.5 to 2 |

History prompts state that choices follow one fixed nonnegative weight, prefer
the strictly larger value, and involve no ties. Both history orders are used.
They do not reveal the generating weight or profile label. Every test ratio
lies outside the history interval, so the expected answer holds for every
compatible weight. A point estimate need not equal the private generating
value. No question asks the model to return a numerical weight or valuations.

The exact draft prompts, IDs and sequence from commit
`fbfc211c8bb92a3c4e61826690e98a4e67de3a98` are preserved. The final protocol
name drops “draft,” while the ordering seed remains
`known-partner-recovery-v1-draft`. Within each pass, items are sorted by the
fixed hash of seed and unique request item ID. Pass 2 repeats the same API
bodies in a different fixed sequence. Each request is a new conversation.
Repeated calls are not independent participants or evidence across dates.

## Collection and stopping

- Pinned model: `claude-sonnet-4-5-20250929`; temperature 0; 256 output tokens.
- Use the existing API-enforced object with `brief_basis` then `answer` (A/B).
  One or two sentences are requested; numerical calculations are not demanded.
- The existing strict acceptance rule is retained: exactly those ordered JSON
  keys, a nonempty string basis, A/B answer, one text block and `end_turn`.
  Truncated, refused and malformed outputs are unusable. Keep the raw output;
  never infer or repair a final answer from its explanation.
- Make all 216 planned calls despite incorrect choices or unusable answers.
  The choice pass rule is an analysis criterion, not an early-stopping gate.
- No SDK retries, alternate model, fallback output format or automatic rerun.
- Transport errors, model-ID mismatches, duplicate API IDs or changed frozen
  protocol stop collection for integrity. Persist any received response before
  an integrity check stops further calls. Upload partial records on failure.
- The workflow has a 45-minute timeout and runs both passes once. A GitHub
  rerun starts a new collection; inspect a failed artifact before considering
  exact local resume. Resume skips all saved responses, including unusable
  ones, and requires the original ordered data, configuration and revision.
  An unrecorded response after a transport error may still have been billed;
  document uncertainty about server completion before resuming.
- Maximum allocated output is 55,296 tokens; input is additional. This is not
  a dollar quote. The existing repository API key is billed for collection.

## Prespecified outcomes

Report separately by condition, profile, history order, option order and pass:

1. Final-answer correctness, both correct / usable and correct / planned;
   also missing, unusable and incorrect-but-usable counts.
2. Containing-interval recovery under the existing threshold estimator, with
   censoring, tied fits, missing observations and violations retained. Fit
   each pass and history order separately, by option position and pooled:
   18 explicit-condition fits and 36 history-condition fits, 54 total.
   These fits share observations and are not 54 independent replications.
3. Semantic option-order disagreements: 108 planned pairs. Exact-request
   repeat disagreements: 108 pairs. History-order disagreements: 72 pairs.
   Use disagreements / complete pairs and complete / planned denominators.
   A/B letter changes expected under reversal are not semantic disagreement.
4. Returned-explanation quality, reviewed separately with the rubric below.
5. Stop reasons and token usage. Preserve all errors and partial responses.

The conservative **choice clear-pass** rule from the draft is unchanged:
216/216 usable, correct choices and 54/54 complete, zero-violation interior
fits containing the generating value. Report pass status for each condition
as well. Missing records are incomplete, not a pass. Any other complete result
is mixed or failed and must be examined case by case. This criterion is not a
population error-rate guarantee, a test of a hidden mechanism, or full social
construct validation. Do not change it after viewing results or rerun until
it passes. Do not discard failed profiles or choose a preferred repetition.

## Explanation review

Review all 216 scheduled records after collection. The exported template shows
the prompt, raw response, parsed basis, final and expected answer, and reference
values. It is an unblinded audit, not an independent rating study. Disclose the
reviewer; assistant-authored coding must not be described as human coding.

Explicit-weight items have exact option values. History items instead have
feasible value intervals: Sam's payoff has a fixed value, while the value of
your payoff depends on the unknown weight within its open interval. Do not
mark a compatible estimate wrong merely because it differs from the hidden
generating value. Claiming that the history uniquely proves one exact weight
is unsupported; an explicitly qualified illustrative value can be compatible.
Recognizing which choice wins for all compatible weights is sufficient and
does not require a numerical calculation in the explanation.

| Label | Criterion |
|---|---|
| `consistent` | The checkable claims are compatible with the supplied rule, history, recipient mapping and final choice; no unsupported unique weight is asserted. |
| `incorrect_calculation_or_mapping` | The text contains an incorrect calculation, payoff/recipient mapping, inequality or contradiction between its stated comparison and final choice. |
| `unsupported_inference` | The text makes a conclusion not warranted by the supplied evidence, such as a uniquely known hidden weight or a decision rule contradicting the stipulated fixed rule. |
| `unclear_or_no_checkable_basis` | A usable output gives too little relevant, checkable justification to assess. Mere absence of an explicit error is insufficient. |
| `unusable_or_missing` | No usable parsed response is available. |

If more than one error applies, use calculation/mapping first, then unsupported
inference, and record both in notes. All coded labels require supporting notes.
These categories describe returned text, not internal reasoning.

Copy `responses.explanation-review-template.jsonl` to a separate labels file.
Keep review IDs and response digests unchanged, enter labels and notes, and
run `inspect --labels PATH`. Unknown/duplicate IDs, stale digests, disallowed
labels and missing notes are rejected. Uncoded records stay pending. The
command archives accepted labels and does not overwrite the reviewer's file.
No final-choice result automatically becomes a clean explanation result.

## Decision after review

Errors in the explicit condition expose an execution/readout problem before
history inference. A clean explicit result with history failures exposes a
functional difficulty when the weight must be inferred from evidence; it
does not uniquely identify an internal cause. Clean results in both conditions
support recovery on these constructed tasks. Review transfer to natural social
prompts and their stipulated ability/effort conditions before any pilot.

The original numerical histories only show keeping and give upper bounds.
They need not imply an interior switch or the favored LOW/HIGH ordering.
The original social effect must remain a hypothesis, not a validation key.
The workflow does not release, alter or launch either social pilot. Any
follow-up must address a specific finding and be documented separately.

## Freeze and artifacts

`protocols/known-partner-recovery-v1.json` binds this plan, ordered item JSONL,
actual request bodies and settings. Generation, collection and inspection
reject a mismatch. Status updates after collection belong in the runbook or
an audit, not edits to this frozen plan.

The artifact includes planned items, protocol/manifest, this plan, source
revision, dependencies, original-history bound audit, a separately labeled
programmed-oracle check, raw API records, arm/cell summaries, all fits and
pairs, and the explanation review template. The programmed-oracle check is
software verification and must never be presented as a model result.
