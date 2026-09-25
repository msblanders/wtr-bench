# Explanation calibration 36088607405: audit and decision

Reviewed 25 September 2026 UTC. **All 72 responses were usable. A/B answered
23/24 controls correctly and agreed across all six social pairs; SAM/YOU
answered 24/24 controls correctly but disagreed on one social pair. Neither
format meets the progression criterion fixed before the run.** Keep the full
debug battery and 888-item pilot paused.

This is improved observed performance relative to the answer-only structured
run, with one remaining known-answer error and one social pair inconsistency.
Those improvements do not erase the failures, establish reliability across
repeated requests or validate a social valuation measure.

## Provenance and verification

- [Run 36088607405, attempt 1](https://github.com/msblanders/wtr-bench/actions/runs/36088607405)
- Source: `70202aeaf16272c2de3b64e99a7a2e7e77885951`, package v0.4.6.
- Requested and returned model: `claude-sonnet-4-5-20250929`, all 72 rows.
- Protocol: `calibration-explanation-v1`; item hash: `838b96effb3ab30c`.
- Temperature 0; maximum output tokens 256; fresh context; required string
  `brief_basis` followed by the constrained `answer` field.
- Artifact ID: `10844589653`; original ZIP SHA-256:
  `2c0785c5812adba31433271f9f7109d3ae87b7aa429e07ad3055dfb06efd1014`.
- [Original extracted records and checksums](../results/calibration/36088607405/).
- [Pre-response protocol and progression criterion](inference-calibration-explanation.md).

The downloaded ZIP digest matches GitHub's artifact digest. All eight
original files are preserved byte for byte. All 72 expected item IDs,
API request IDs and API message IDs are unique, with no omissions or extra
responses. Saved prompts and their sequence match the generator exactly.
Protocol, configuration, submitted request bodies, complete SDK response
bodies, raw text and decoded records validate at the recorded source revision.
Both reports reproduce; the inspect report has one extra trailing newline.

An independent check also extracted the displayed allocations, question and
stated weights from the prompt text, recomputed each control's correct
recipient, and mapped the raw final-answer field back to the displayed
recipient. All truth keys and the reported scores agree with this check.
The API requests contain no truth keys, expected-value metadata or prior
responses. No new model calls were made for this audit; no scoring rule or
progression criterion changed.

## Results

| Check | A/B | SAM/YOU |
|---|---:|---:|
| Usable, normally completed responses | 36/36 | 36/36 |
| Recipient lookup correct | 8/8 | 8/8 |
| Quantity comparison correct | 4/4 | 4/4 |
| Explicit-rule controls correct | 11/12 | 12/12 |
| All known-answer controls correct | 23/24 | 24/24 |
| Control pairs semantically consistent | 11/12 | 12/12 |
| Social pairs semantically consistent | 6/6 | 5/6 |
| Candidate for full debug under the fixed criterion | No | No |

All 72 stop reasons were `end_turn`. There were no missing, refused,
truncated or unparsed responses. Outputs used 36–104 tokens, below the
256-token allowance. This run's remaining failures occurred in normally
completed, well-formed responses.

The criterion required 24/24 usable correct controls and six complete,
consistent social pairs **within the same reply format**. Combining the
recipient format's control accuracy with the letter format's social
consistency would not meet that criterion.

## The one control error: a false tie in the returned explanation

Item `wtrcalbasis-bf310a18b7ce03f6` is `rule_1_20`, A/B format, with Sam's
option second. The rule is Sam's points plus one times your points; the
unnamed recipient gets zero.

| Displayed option | Sam's points | Your points | Correct value to Sam |
|---|---:|---:|---:|
| A: You receive 10 | 0 | 10 | 10 |
| B: Sam receives 20 | 20 | 0 | 20 |

The correct answer is B (SAM). The response instead says:

> Sam values option A as 10 + 1(10) = 20 points, and option B as 20 + 1(0) = 20 points.

It then describes a tie and returns A (YOU). The observable error is in
assigning the payoff inputs: option A credits Sam with 10 points despite
the prompt assigning Sam zero. The addition itself is correct for those
incorrect inputs. This is not an observed case of a final choice
contradicting two correctly returned option values.

That same case was correct in the other A/B option order and in both
SAM/YOU orders. The earlier answer-only A/B run answered this exact case
correctly in both orders. Its old failure, the weight-2, 40-versus-10 case,
is now correct in both orders. Thus the residual A/B error has moved to a
different case; it is not simply a persisting failure on the previously
identified arithmetic problem.

This diagnosis concerns the returned text. It does not reveal the model's
internal computation or establish that the written explanation caused the
choice error. The explanation cannot be used to repair the recorded answer.

## The social mismatch: numerical HIGH, ratio 0.5

For this case, Sam previously took 15 points rather than give you 10, and
then took 25 rather than give you 10. The new choice is 5 for Sam versus
10 for you. The histories and amounts are identical across the option-order
pair; only the displayed options reverse.

| Reply format | Sam option first | Sam option second |
|---|---|---|
| A/B | SAM | SAM |
| SAM/YOU | SAM | YOU |

In the first SAM/YOU response, the explanation emphasizes Sam's prior
self-interested choices. In the reversed response, it emphasizes that the
new personal benefit is much smaller and predicts giving you the points.
Both outputs are preserved. These are different expressed rationales, not
evidence for different internal mechanisms.

There is no known correct social prediction here: the history does not
uniquely determine the new choice. The failure is disagreement across
matched option orders. With one response per exact prompt, this run cannot
separate a reproducible order effect from variability across repeated
requests. The earlier answer-only recipient run gave SAM in both orders,
so the mismatch is newly observed under this response protocol.

## All social judgments

Entries name the recipient in the model's prediction of Sam's choice, not
the responding model's own generosity. Each cell gives Sam-first / Sam-second.

| Case | A/B | SAM/YOU |
|---|---|---|
| Unable, ratio 0.1 | YOU / YOU | YOU / YOU |
| Unable, ratio 1 | YOU / YOU | YOU / YOU |
| Unwilling, ratio 0.1 | SAM / SAM | SAM / SAM |
| Unwilling, ratio 1 | SAM / SAM | SAM / SAM |
| Numerical LOW, ratio 0.5 | SAM / SAM | SAM / SAM |
| Numerical HIGH, ratio 0.5 | SAM / SAM | SAM / YOU |

The boxes cases now show a stable unable/unwilling distinction at the two
sampled payoff ratios in both formats. This is a descriptive finding from
one scenario. The explanations invoke intentions, compensation, reciprocity
or self-interest; their wording does not establish a shared latent valuation.
The calibration includes no ability readout, full ladder or independent
scenario replication, so it cannot establish the proposed valuation/ability
dissociation or useful threshold estimates. The mostly identical LOW/HIGH
predictions at one rung also do not establish equal underlying valuations.

## Comparison with prior protocols

| Measure | Answer-only structured | Required calculation fields | Brief explanation |
|---|---:|---:|---:|
| A/B explicit-rule accuracy | 10/12 | 12/12 | 11/12 |
| SAM/YOU explicit-rule accuracy | 6/12 | 12/12 | 12/12 |
| A/B social pair agreement | 5/6 | Not tested | 6/6 |
| SAM/YOU social pair agreement | 4/6 | Not tested | 5/6 |

The comparison uses the same underlying rule cases and, where tested, the
same social cases. Relative to the answer-only run, both formerly wrong
A/B controls became correct while one formerly correct control became
wrong; the other 21 remained correct. All six formerly wrong recipient
controls became correct and the other 18 remained correct.

These are observations across different elicitation protocols, not a
randomized isolation of explanation, field order or any internal computation.
The total 47/48 correct controls includes paired option orders and reply
formats; it does not represent 48 independent problems. The calculation
protocol tested only explicit-rule controls and cannot establish transfer
to social judgments on its own. Retain all earlier runs.

## Recommended next step: a bounded repeatability check

Keep the current explanation protocol unchanged for **two further complete
72-request batches**, giving three observations per exact prompt including
this run (144 additional requests, 216 across all three batches). Use the
same pinned model, temperature, output allowance, system/user instructions,
schema, cases, request sequence and option reversals. Fresh workflow runs
produce separate artifacts; every request still has fresh conversation
context. Preserve all three runs and their source revisions.

The purpose is to determine whether the one control error and one social
mismatch recur, and whether other failures appear, before choosing another
prompt intervention. Repeating the entire set avoids selecting only the
observed failures for the reliability estimate. The count is fixed in
advance; do not keep adding batches until a clean run appears.

For each format, report control accuracy, missingness and social pair
agreement separately for every run. Also report per-item answer agreement
across all three runs and the two option-order response distributions for
each case. Apply the original progression flag to each run, and retain this
run's failed flag. A later passing run does not erase earlier failures or
validate the pilot. Any future change in tolerated error or progression
criteria must be explicit before collecting new evidence to assess it.
Three observations per prompt provide a small descriptive repeatability
check, not a precise reliability estimate or definitive order-effect test.

Follow-up update: the two planned replications subsequently completed in
runs 36090248661 and 36090756872. The
[combined audit](calibration-explanation-repeats-review.md) retains the
initial failed flags above. A/B's final-answer error did not recur, but the
same incorrect stated calculation appeared in all three runs. SAM/YOU's
social mismatch repeated in both new runs. The fixed replication check is
finished; no further identical batches are recommended. The next candidate
is A/B for a compatible exploratory full debug workflow with concurrent
controls. The 888-item pilot remains unrun, unfrozen and unregistered.

## Article implications and usage

A defensible current account is that the measurement-development sequence
resolved truncation and formatting failures, exposed known-rule choice
errors, obtained correct rule performance with explicit calculation fields,
and then obtained 47/48 correct controls and 11/12 consistent social pairs
with a uniform brief-explanation protocol. The remaining failures show why
valid formatting, control accuracy, repeatability and social measurement
validity need separate checks. This is evidence about elicitation and
measurement behavior, not a demonstrated social valuation mechanism.

Recorded usage: 27,716 input tokens and 4,554 output tokens; zero recorded
cache tokens. These are usage records, not an invoice estimate.
