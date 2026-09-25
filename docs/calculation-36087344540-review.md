# Calculation diagnostic 36087344540: audit and decision

Reviewed 25 September 2026 UTC. **All 24 responses returned both option
values correctly and selected the correct recipient. Every complete
option-order pair agreed.** The calculation-first protocol succeeds on
these six explicit-rule controls in both reply-label formats.

The next question is whether an explanation-permitting protocol can also
collect stable social judgments. This control-only success does not validate
the earlier answer-only protocol or authorize skipping the social calibration.

## Provenance and verification

- [Run 36087344540, attempt 1](https://github.com/msblanders/wtr-bench/actions/runs/36087344540)
- Source: `36bab886777eff3e0285b6a7a75e2f908349dd22`, package v0.4.5.
- Requested and returned model: `claude-sonnet-4-5-20250929`, all 24 rows.
- Protocol: `calculation-diagnostic-v1`; item hash: `7306b8fde1e80015`.
- Temperature 0; maximum output tokens 256; required numerical values for
  displayed options A and B, followed by a required answer field.
- Artifact ID: `10843958831`; original ZIP SHA-256:
  `7226c87c62896590528b86f7e535f66e114edd9ab498c97d1b168d2244e1a751`.
- [Original extracted records and checksums](../results/diagnostics/36087344540/).

All 24 expected item IDs and API request IDs are unique, with no missing or
extra responses. Prompts match the generator byte for byte. Config,
protocol, recorded request bodies, complete SDK response bodies and decoded
fields validate against the run's source revision. Both reports reproduce;
the inspect report has one extra trailing newline. The downloaded ZIP digest
matches GitHub's artifact digest.

In addition to reproducing the scorer, an independent check extracted each
weight and both displayed allocations from the prompt text, recomputed the
two values, parsed the raw JSON, and checked the answer against the larger
value. Every response passed. The submitted request bodies contain no truth
keys, expected-value metadata, demonstrations or prior answers.

The original reports and responses are preserved unchanged. No new model
calls were made for this audit.

## Results

| Check | A/B | SAM/YOU |
|---|---:|---:|
| Usable, normally completed answers | 12/12 | 12/12 |
| Both returned option values correct | 12/12 | 12/12 |
| Final choice correct | 12/12 | 12/12 |
| Choice follows returned value ranking | 12/12 | 12/12 |
| Reported value ties | 0 | 0 |
| Semantic option-order disagreements | 0/6 pairs | 0/6 pairs |

All stop reasons were `end_turn`. There were no refusals, truncations,
unparsed answers, calculation errors, choice errors or incomplete pairs.
Both option orders separately passed every check.

| Weight on your points | Sam's allocation | Value to Sam of own allocation | Value to Sam of your 10 points | Correct and observed recipient |
|---:|---:|---:|---:|---|
| 0.5 | 2 | 2 | 5 | YOU |
| 0.5 | 8 | 8 | 5 | SAM |
| 1 | 5 | 5 | 10 | YOU |
| 1 | 20 | 20 | 10 | SAM |
| 2 | 10 | 10 | 20 | YOU |
| 2 | 40 | 40 | 20 | SAM |

Each row was tested in both option orders and both formats. In the previously
failed weight-2, 40-versus-10 case, all four responses now returned 40 versus
20 in the correct displayed order and selected Sam's allocation.

## Comparison with the answer-only structured run

| Final-choice accuracy on the same rule cases | Prior answer-only run | Calculation-first run |
|---|---:|---:|
| A/B | 10/12 | 12/12 |
| SAM/YOU | 6/12 | 12/12 |

The eight previously incorrect responses became correct; the sixteen
previously correct responses remained correct. The recipient format no
longer answered YOU on every rule control. These counts include paired
option orders: six underlying problems were tested, not 24 independent
problems. There is one response per item per protocol, with no sampling
replicates or significance test.

This establishes that the model can solve the stated calculations and map
the result to either reply-label system under the new protocol. The earlier
failures cannot be treated as evidence that the model is incapable of this
arithmetic. Performance is sensitive to the elicitation protocol in these
observations.

It does not identify the exact internal cause of the prior errors. No
calculations were returned in the answer-only condition. Asking for values
changes the prompt instructions, output schema, output sequence and the
generated content; field order does not establish neural processing order.
Because the error disappeared in this diagnostic, we did not observe a
remaining bad calculation or choice inconsistency to localize further.

## Recommended next step: transfer to a uniform response protocol

Return to the **original 72-request calibration design**, using the same
model, cases, option reversals and two reply-label conditions, with a
required brief explanation followed by a final answer. A single protocol
should apply to recipient lookup, quantity comparison, explicit-rule
controls and the six existing social debug cases. Keep fresh contexts,
temperature 0 and the 256-token allowance; request a concise explanation
and retain strict completion/schema checks.

For example, a schema can require a string `brief_basis` followed by an
`answer` enum. The instruction should ask for a brief basis for the answer
using the supplied information. It should not prescribe the desired
social ordering, supply a worked example, or tell the model to fit a WTR.
Do not assign truth keys to the social judgments.

The calculation fields used here do not transfer directly to social
prediction: those prompts do not supply a known utility coefficient.
Requiring the model to invent that coefficient would introduce the very
representation the behavioral study aims to investigate. A generic brief
explanation avoids imposing that numerical representation, although it is
still a new response protocol requiring its own calibration.

Assess final-answer completeness and known-answer accuracy before inspecting
social pair consistency. Retain the previously stated progression criterion
within each format: 24/24 usable correct controls and all six complete,
semantically consistent social pairs. Explanations are saved as outputs;
they are not scored as evidence of internal mechanism or used to recover
a missing final answer.

If a format passes, then implement and run a compatible full debug battery
to assess ladder coverage, censoring, monotonicity and remaining order
effects before any pilot freeze. If both pass, carry both into that
comparison. Select formats by measurement behavior, never by whether they
produce the favored valuation hypothesis. Retain all earlier runs.

Implementation update: this next calibration is now available as
[Inference calibration (explanation)](inference-calibration-explanation.md),
protocol `calibration-explanation-v1`. It subsequently completed in
[run 36088607405](calibration-36088607405-review.md), with all 72 answers usable
but neither format meeting the combined progression criterion. This update
does not change the calculation diagnostic or its conclusions. No additional
calculation-only batch is needed on the current evidence. The full debug
battery and 888-item pilot remain paused.

## Article implications and usage

The current defensible empirical statement is that answer-only elicitation
produced explicit-rule errors that were absent when the same model was
asked to return the two option values before its choice. That is a concrete
measurement-development observation. The social valuation dissociation,
stable partner estimates and shared internal variables remain unestablished.

Recorded usage: 9,976 input tokens and 911 output tokens, with no recorded
cache tokens. Individual outputs used 33–42 tokens. These are recorded
usage totals, not an invoice estimate.
