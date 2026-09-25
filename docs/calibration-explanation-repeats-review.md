# Explanation calibration: three-run repeatability audit

Reviewed 25 September 2026 UTC. The two planned replications are complete.
**A/B met the original final-answer progression criterion in both new runs;
SAM/YOU repeated the same social option-order mismatch in all three runs.**
There is an important qualification: the A/B explanation still gives the
same incorrect option value in every run, even when its final answer is
correct. The initial failed run remains part of the evidence.

A/B is the better candidate for the next exploratory full debug battery,
with concurrent controls and the calculation anomaly explicitly retained.
This is not a claim of flawless rule-following or pilot readiness. The
888-item pilot remains unrun, unfrozen and unregistered. The bounded
repeatability check is finished; no further identical calibration batches
are recommended at this point.

## Provenance and verification

All three batches used `calibration-explanation-v1`, item hash
`838b96effb3ab30c`, model `claude-sonnet-4-5-20250929`, temperature 0, maximum
output tokens 256, fresh context per request, and `brief_basis` followed by
`answer`. The 72 prompts, their sequence, request bodies, schema property
order and dependency versions match across all three batches.

| Batch | Run | Source revision | Artifact ID |
|---|---|---|---|
| Initial | [36088607405](https://github.com/msblanders/wtr-bench/actions/runs/36088607405) | `70202aeaf16272c2de3b64e99a7a2e7e77885951` | `10844589653` |
| Replication 1 | [36090248661](https://github.com/msblanders/wtr-bench/actions/runs/36090248661) | `c7d292319f142b52bea42f6263b0d6f9282a48ff` | `10845397082` |
| Replication 2 | [36090756872](https://github.com/msblanders/wtr-bench/actions/runs/36090756872) | `c7d292319f142b52bea42f6263b0d6f9282a48ff` | `10846080759` |

The intervening commit changed only documentation and archived results;
source code, tests, workflows and dependencies were unchanged. Both new
workflows completed successfully on attempt 1. The new ZIP digests match
GitHub's artifact digests:

- 36090248661: `f9a1fbd34f9bd8003819baf2fd3db4d1b792279be516ef6db4c671cd8651b11b`
- 36090756872: `8ec69cf10d6ee6f5281c219f18f90ab06fc9895ab5304378c4e0e7249c1cb798`

Original files are preserved byte for byte, with SHA-256 manifests:
[initial](../results/calibration/36088607405/),
[replication 1](../results/calibration/36090248661/),
[replication 2](../results/calibration/36090756872/).
The [initial audit](calibration-36088607405-review.md) records the fixed
two-replication plan before either new batch was collected.

All 216 expected responses are present, with 216 distinct API request IDs
and message IDs. Every response ended with `end_turn` and passed the
completion/schema checks. There were no missing, truncated, refused or
unparsed responses. Each saved request and full response validates; all six
original reports reproduce. Independent extraction of the displayed
allocations and stated rules from prompt text confirms the truth keys,
final-answer decoding and control scores. This audit made no model calls
and changed no parser, scoring rule or progression criterion.

## Final-answer results, retaining every run

| Batch | A/B controls | A/B social pairs consistent | A/B original progression flag | SAM/YOU controls | SAM/YOU social pairs consistent | SAM/YOU original progression flag |
|---|---:|---:|---|---:|---:|---|
| Initial | 23/24 | 6/6 | Not ready | 24/24 | 5/6 | Not ready |
| Replication 1 | 24/24 | 6/6 | Candidate | 24/24 | 5/6 | Not ready |
| Replication 2 | 24/24 | 6/6 | Candidate | 24/24 | 5/6 | Not ready |

In both new runs, each format separately answered all eight recipient
lookups, four quantity comparisons and twelve explicit-rule controls
correctly. All six social pairs were complete in each format in every run.
The combined final-answer control counts are A/B **71/72** and SAM/YOU
**72/72**. Across displayed orders, A/B was 36/36 when Sam's option was first
and 35/36 when it was second; SAM/YOU was 36/36 in each order.

The original criterion remains 24/24 usable correct controls and all six
complete, consistent social pairs within a format and run. The two new
A/B flags are supported by that existing rule. The initial failed flag is
not replaced by a pooled percentage or a best-run result. These counts
repeat the same small item set; they are not independent problem or
scenario replications and do not precisely estimate a general error rate.

## The correct answers conceal a persistent stated-value error

The initial A/B error occurred on `rule_1_20` with Sam's option second,
item `wtrcalbasis-bf310a18b7ce03f6`:

| Option | Sam's points | Your points | Correct value under the stated rule |
|---|---:|---:|---:|
| A: You receive 10 | 0 | 10 | 10 |
| B: Sam receives 20 | 20 | 0 | 20 |

The rule says to choose the greater value of Sam's points plus one times
your points. **All three responses instead assign option A a value of 20**,
using `10 + 1(10)`, and claim a tie with option B. The error credits Sam
with points the prompt explicitly says Sam does not receive; it is an
incorrect payoff input, not incorrect addition of those inputs.

| Batch | Stated A value | Stated B value | Final answer | Final-answer accuracy |
|---|---:|---:|---|---|
| Initial | 20 | 20 | A / YOU | Wrong |
| Replication 1 | 20 | 20 | B / SAM | Correct |
| Replication 2 | 20 | 20 | B / SAM | Correct |

The later responses resolve their claimed tie in favor of Sam as the direct
recipient. They do not repair the option values or select B by comparing
the correct 10-versus-20 values. Thus the original final-answer error did
not recur, but the observable calculation error did. It would be inaccurate
to report that replication resolved the arithmetic problem.

A manual audit of all 72 explicit-rule explanations across the three
batches found correct stated option values in the other 69 responses.
These correspond to 37 unique explanation-and-answer outputs, with many
identical repeats. The same problematic case was correctly calculated in
the opposite A/B order and in both SAM/YOU orders in every batch.

Explanation correctness was not part of the pre-response scoring rule, so
this finding does not retroactively change the two passing A/B flags. It is
a separate, material output-quality finding. The written explanation also
does not reveal internal reasoning: neither a correct choice nor the text
establishes how the model internally reached that choice. Future evaluation
should keep final-answer accuracy and correctness of any checkable stated
calculations distinct.

## Repeatability and option-order robustness are different

| Exact prompts giving the same semantic answer in all three runs | A/B | SAM/YOU |
|---|---:|---:|
| Controls | 23/24 | 24/24 |
| Social judgments | 12/12 | 12/12 |
| All prompts | 35/36 | 36/36 |

Only one of the 72 exact prompts changed its final answer: the A/B control
above, from YOU to SAM to SAM. All 24 exact social prompts gave the same
answer across runs. This is repeatability of semantic choices, not of the
explanation text. The two new batches had identical raw output on 54/72
items, while their final choices matched on all 72.

See the [complete per-item repeatability table](calibration-explanation-repeatability-items.md).
The following table gives the counts of each social prediction at each
option order; each entry represents three responses to the same prompt.

| Case | A/B: Sam first | A/B: Sam second | SAM/YOU: Sam first | SAM/YOU: Sam second |
|---|---|---|---|---|
| Unable, ratio 0.1 | YOU 3/3 | YOU 3/3 | YOU 3/3 | YOU 3/3 |
| Unable, ratio 1 | YOU 3/3 | YOU 3/3 | YOU 3/3 | YOU 3/3 |
| Unwilling, ratio 0.1 | SAM 3/3 | SAM 3/3 | SAM 3/3 | SAM 3/3 |
| Unwilling, ratio 1 | SAM 3/3 | SAM 3/3 | SAM 3/3 | SAM 3/3 |
| Numerical LOW, ratio 0.5 | SAM 3/3 | SAM 3/3 | SAM 3/3 | SAM 3/3 |
| Numerical HIGH, ratio 0.5 | SAM 3/3 | SAM 3/3 | SAM 3/3 | YOU 3/3 |

The numerical HIGH recipient-label mismatch therefore repeated in every
batch. With Sam's option first, the response predicts SAM; with your
option first, it predicts YOU. In this specific case it consistently
selects the first displayed option despite answering with recipient names.
This is a repeated association with option order under the fixed request
sequence, not a general diagnosis of the model's internal strategy or a
precise estimate of its order sensitivity.

The written bases also differ with order: the SAM responses emphasize
Sam's prior self-interested choices; the YOU responses emphasize that the
new personal payoff is smaller. There is no known correct psychological
prediction for this history. The problem is that the same evidence produces
different predictions when only the displayed option order changes.

The boxes unable/unwilling distinction is stable in both formats at both
sampled ratios. A/B gives the same SAM response to numerical LOW and HIGH
at the single sampled ratio. Neither observation establishes the full
valuation/ability dissociation, ladder coverage, or a shared internal
valuation variable. The calibration has one boxes scenario, one numerical
construction and no ability readout.

## Decision and next step

**End the bounded replication check here. Carry A/B forward as the candidate
for exploratory full debug; retain SAM/YOU as an observed order-sensitive
comparison.** This choice follows the previously fixed final-answer and
order-consistency checks, not a preferred social ordering. A/B passed both
planned replications, but its initial final-answer error and three faulty
stated calculations must remain visible. SAM/YOU failed the same social
pair in all three batches despite perfect exact-prompt repeatability.

The recommended next batch is a compatible **220-request exploratory debug
run: the existing 196 debug items plus the 24 A/B known-answer controls**.
Keep the same model, temperature, 256-token allowance, fresh contexts and
brief-explanation-then-A/B schema. Preserve the existing debug evidence,
payoffs, ladder, option reversals and evidence-order reversals. Retain the
controls as a separate block with separate accuracy reporting; they do not
enter ladder fits. Do not require numerical social valuations or repair
final answers from explanations.

Before those calls, implement and document the compatible runner and
scorer. Continue to distinguish final-answer control accuracy from any
checkable calculations the model volunteers, including the known false-tie
case. An error in a written calculation must not be described as corrected
merely because the final label is right. This qualification is why the
recommended next run remains measurement development, not validation of
reliable computation or authorization for the pilot.

The full debug review should examine collection, controls, option-order
and evidence-order agreement, monotonicity, censoring, threshold bounds and
whether the existing ladders are informative. Review the ability probes
alongside valuation predictions before evaluating the proposed dissociation.
Report conflicting and unresolved patterns rather than choosing a format
or ladder to obtain a favored psychological result.

Subsequent execution update: the v0.4.7 [220-request explanation debug
is complete and audited](debug-36095971330-review.md). Its controls and all
twelve rule calculations were correct, including the previously faulty case.
Its broader battery exposed eight option-order disagreements, unresolved
ladder estimates and a conditional ability/willingness issue. The pilot
remains paused. The recommendation above records the decision made before
that run; the new audit records the next measurement-development decision.
The existing **Inference debug** workflow retains the earlier answer-only
protocol; **Inference debug (explanation)** reproduces this completed batch.

## Article implications and usage

This sequence now supplies two concrete measurement-development findings:
a correct final label can coexist with an incorrect stated calculation,
and exact-prompt repeatability can coexist with systematic option-order
inconsistency on a matched pair. Both findings concern observable outputs.
Neither identifies internal computation, validates the social measure, or
establishes general model competence.

| Batch | Input tokens | Output tokens |
|---|---:|---:|
| Initial | 27,716 | 4,554 |
| Replication 1 | 27,716 | 4,538 |
| Replication 2 | 27,716 | 4,552 |
| Total | 83,148 | 13,644 |

Every output used 36–104 tokens; all recorded cache-token counts were zero.
These are usage records, not an invoice estimate.
