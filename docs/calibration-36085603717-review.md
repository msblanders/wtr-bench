# Structured calibration 36085603717: audit and decision

Reviewed 25 September 2026 UTC. **The structured protocol collected every
answer successfully, but neither reply format passed the checks fixed
before the run. Keep the full debug battery and 888-item pilot paused.**

## Provenance and verification

- [Run 36085603717, attempt 1](https://github.com/msblanders/wtr-bench/actions/runs/36085603717)
- Source: `3d694ef45cde84cb878e8777078182f4e84fe006`, package v0.4.4.
- Requested and returned model: `claude-sonnet-4-5-20250929`, all 72 rows.
- Protocol: `calibration-structured-v1`; item hash: `ac2f89d22ce87380`.
- Temperature 0; maximum output tokens 256; required JSON `answer` enum;
  separate A/B and SAM/YOU formats; fresh context per request.
- Artifact ID: `10843369255`; original ZIP SHA-256:
  `a2deedf94f30f3b72f20d567e7a2d1d5d79352ea0a60e2f9c92ea9abc35827a2`.
- [Original extracted records and checksums](../results/calibration/36085603717/).

All 72 expected item IDs and request IDs are unique, with no omissions or
extra responses. Saved prompts match the generator byte for byte; protocol
settings and recorded request bodies match the implementation. Full SDK
response bodies, raw text, stop reasons, metadata and semantic decoding
validate. Both original reports reproduce; the inspect report has one extra
trailing newline. The ZIP digest matches GitHub's artifact digest.

The original reports and records are preserved unchanged. This audit made
no new model calls and changes no scoring rule or progression criterion.

## Collection worked; substantive checks still failed

| Check | Structured A/B | Structured SAM/YOU |
|---|---:|---:|
| Usable answers | 36/36 | 36/36 |
| Recipient lookup | 8/8 correct | 8/8 correct |
| Larger quantity | 4/4 correct | 4/4 correct |
| Explicit choice rule | 10/12 correct | 6/12 correct |
| All known-answer controls | 22/24 correct | 18/24 correct |
| Control option-order disagreements | 0/12 complete pairs | 0/12 complete pairs |
| Social option-order disagreements | 1/6 complete pairs | 2/6 complete pairs |
| Candidate for full debug under the fixed criterion | No | No |

All 72 responses ended with `end_turn`; none was truncated, refused or
unparsed. Each output used 8–10 tokens. The previous A/B social responses
disagreed in all six pairs; this run disagreed in one. The previous recipient
format had three incomplete social pairs; this run completed every pair.

These improvements are observed across protocol packages. System/user reply
instructions, constrained decoding and the output allowance changed together;
their individual causal contributions are not isolated. The remaining
errors occurred in short, normally completed responses, so truncation is no
longer an explanation for those errors.

## Every explicit-rule error

The rule states that Sam chooses the larger value of Sam's own points plus
the specified weight times your points. In each option, the other recipient
gets zero. Every rule case is presented in both option orders. Predictions
in this table were identical across those two orders.

| Weight on your points | Points offered to Sam | Value to Sam of taking own points | Value to Sam of giving you 10 | Correct recipient | A/B prediction | SAM/YOU prediction |
|---:|---:|---:|---:|---|---|---|
| 0.5 | 2 | 2 | 5 | YOU | YOU | YOU |
| 0.5 | 8 | 8 | 5 | SAM | SAM | YOU |
| 1 | 5 | 5 | 10 | YOU | YOU | YOU |
| 1 | 20 | 20 | 10 | SAM | SAM | YOU |
| 2 | 10 | 10 | 20 | YOU | YOU | YOU |
| 2 | 40 | 40 | 20 | SAM | YOU | YOU |

Thus the A/B format missed one underlying rule case in both orders: at
weight 2, Sam should take 40 for Sam rather than give you 10, because 40 is
greater than 2 × 10 = 20. It predicted the latter allocation twice.

The recipient format answered YOU on all 12 rule-control prompts, yielding
six correct and six wrong responses on this balanced set. Its perfect
option-order stability on those controls is therefore insufficient evidence
of rule-following. These are three failed underlying cases, each repeated
in two option orders, not six independent arithmetic problems.

The same recipient format correctly selected the larger quantity when the
simple quantity control offered Sam 20 versus you 10. It selected YOU when
the explicit rule with weight 1 offered those amounts. This localizes the
failure to the changed task context/protocol; it does not establish whether
the cause is rule representation, perspective interpretation, a response
shortcut, or something else. The final answers do not expose that cause.

## Social judgments

Entries name the payoff recipient in the model's prediction of Sam's choice,
not the responding model's own generosity. No preferred social answer is
assigned a truth key.

| Case | A/B: Sam first / second | SAM/YOU: Sam first / second |
|---|---|---|
| Unable, ratio 0.1 | YOU / YOU | YOU / SAM |
| Unable, ratio 1 | SAM / SAM | SAM / SAM |
| Unwilling, ratio 0.1 | YOU / SAM | YOU / SAM |
| Unwilling, ratio 1 | SAM / SAM | SAM / SAM |
| Numerical HIGH, ratio 0.5 | SAM / SAM | SAM / SAM |
| Numerical LOW, ratio 0.5 | SAM / SAM | SAM / SAM |

The unwilling, ratio-0.1 pair reverses its predicted recipient in both
formats. The recipient format also reverses the unable, ratio-0.1 pair.
The matched numerical predictions at this single rung establish neither
equal valuations nor an absent diagnostic-pattern effect. No ladder
estimates or valuation/competence dissociation are inferred from these cases.

The fixed progression rule required 24/24 usable correct controls and six
complete consistent social pairs within a format. Neither format qualifies.
All cases remain exploratory: they reuse one boxes scenario and one
numerical construction, with no new independent scenarios.

## Recommended next diagnostic

The immediate target is the explicit-rule failure. A small **24-request
control-only diagnostic** can reuse all six explicit-rule cases, both option
orders, and both reply-label conditions. Keep the same model and request
budget, and ask for the computed value to Sam of each displayed option in
addition to the final answer, using a fixed structured schema such as:

```json
{
  "option_a_value_to_sam": 40,
  "option_b_value_to_sam": 20,
  "answer": "A"
}
```

That example illustrates the output fields; it should not be inserted as a
worked demonstration in model prompts. Evaluate each returned value against
the independently calculated truth, and separately check whether the final
answer selects the larger returned value and the larger true value.

This would distinguish observable calculation errors from inconsistencies
between returned calculations and the final choice. The returned calculations
are task outputs, not a transparent record of the model's internal reasoning.
Requiring them also changes the task; success would not retroactively validate
the answer-only protocol or demonstrate a psychological mechanism.

This diagnostic is a recommendation, not yet implemented or run. Do not
rerun the current structured workflow expecting it to include those fields.
Interpret this result before preparing another request batch; do not advance
to the full debug or pilot merely because the output now parses.

## Implications and usage

The run separates three things that should remain distinct in the article:
valid output syntax, stable responses under option reversal, and correct
performance on known-answer controls. A format can meet the first two while
failing the third. The proposed valuation findings remain unresolved, and
this calibration supports no claim about a maintained/shared internal
valuation variable or about Sonnet's general social competence.

Recorded usage was 22,532 input tokens and 665 output tokens, with zero
recorded cache tokens. These are usage records, not an invoice estimate.
