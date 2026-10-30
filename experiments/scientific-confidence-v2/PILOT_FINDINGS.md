# Second pilot: faithful evidence tables plus numerical calculation

The follow-up completed **252/252 calls for $5.170983** on 30 October 2026 UTC: four development
cases and 32 fresh evaluation cases. There were **no truncated responses** in either phase,
no infrastructure failures, and no unknown-cost requests. Development cost $0.586104 and main
evaluation cost $4.584879. Both pilots together have recorded $9.209979 in token charges.

The combined ledger-and-calculator procedure produced probabilities extremely close to the
independent oracle on all 32 main cases. The largest difference in any hypothesis probability
was 0.000001983, or **0.0001983 percentage points**. This is a promising result for the complete
procedure on this controlled task. It is not yet a general scientific-reasoning result.

## The components separate cleanly in this sample

Both procedures submit the same final worksheet and their own probability estimates. Each
worksheet is then scored using the model's probabilities and using a source-blind calculator.
The calculator never receives the original dossier or correct answers, so it cannot repair
incorrect predictions copied into the worksheet.

Mean posterior regret below is squared distance from the exact probability vector, summed over
the three hypotheses. Lower is better. All four entries use the same 32 cases with valid outputs.
These are two readouts of two model procedures, not four independent sets of observations.

| Preparation | Model's probability estimates | Calculated from its worksheet | Source-faithful final worksheets |
|---|---:|---:|---:|
| Calibration checklist | 0.04345064 | 0.04146956 | 29/32 |
| Source-linked ledger | 0.06676445 | 0.0000000000002645 | 32/32 |

This illustrates two distinct failure points. Reliable arithmetic cannot rescue a wrong mapping
between a hypothesis and its predicted observations. A faithful table also does not ensure the
model will state the correct probabilities. In this setup, the complete procedure addresses both.

The manual ledger path allocates its preparation to extraction rather than numerical reasoning.
Its poor manual estimates therefore do not establish that tables inherently impair reasoning:
the procedures allocate their work differently. The primary representation comparison holds the
calculator and final schema fixed, avoiding that arithmetic difference.

## Prespecified primary comparison and its practical limits

Ledger+calculator minus checklist+calculator: **-0.04146956** posterior regret over 32 paired cases.
The descriptive 95% bootstrap interval is **[-0.11070406, -0.0000000000000405]**. Its upper endpoint
is effectively zero; do not turn that last-bit numerical exclusion into a strong significance claim.

All material checklist+calculator error came from three cases. Two of those account for about
99.7% of that condition's total error. The source-fidelity comparison is only three discordant
cases: both procedures were faithful in the other 29. This sample supports a concrete failure
mechanism and a candidate remedy, while leaving uncertainty about how often the advantage appears
on a broader task distribution. Repetition across cases, models, and more realistic evidence is needed.

## What went wrong in the checklist worksheets

Posthoc inspection identified four wrong prediction cells across three cases. Study IDs and
design/context labels were preserved, but expected means were assigned incorrectly, including
substitutions that changed a predicted effect's sign. The calculator faithfully used those wrong
tables, preserving substantial probability error. The ledger path preserved the supplied values.
Detailed case-level examples and raw responses are included in the researcher's private package.

Conversely, every ledger final table matched the sources within the frozen copying tolerances,
but the model's own probabilities could still be off by as much as 52.8 percentage points. The
calculator readout eliminated these discrepancies without extra model calls or hidden answers.

## Original audit with a larger output allowance

The original checklist and audit instructions were preserved, with 4,096 output tokens per call
instead of 1,400. No responses were cut off. This removes the observed truncation limitation in
this run; new cases mean it is not a controlled within-case estimate of the effect of more tokens.

| Original verbal procedure | Valid probability vectors | Mean failure-aware posterior loss | Mean regret on valid cases |
|---|---:|---:|---:|
| Checklist | 32/32 | 0.04344683 | 0.04344683 |
| Contrastive audit | 31/32 | 0.06335945 | 0.00088718 |

One audit probability vector summed to 1.007, outside the frozen 0.005 tolerance. Its response
was complete, syntactically valid JSON; it failed the normalization rule. Under the prespecified
invalid-output penalty of 2, the overall audit-minus-checklist difference was +0.01991263 with a
wide interval [-0.09825797, +0.17404178]. On the 31 valid paired cases it had lower numerical error.
Thus the verbal audit comparison is mixed, not evidence that the audit is simply worse at reasoning.
Its composite mean is dominated by the failure penalty, which must not be confused with raw
probability error. The main ledger/calculator comparison has no invalid outputs and avoids this issue.

## Posthoc efficiency check: the second model call may be unnecessary

The frozen experiment used two-call paths to compare preparation and final-answer procedures.
Afterward, we evaluated the 32 FIRST ledger responses directly with the same calculator.
All 32 first ledgers were source-faithful; mean posterior regret was 2.7219e-13 and mean predictive
regret was 6.1266e-14. Those 32 first calls cost **$0.440913** in total.

No new API calls were made for this diagnostic. It suggests a cheaper candidate operator:

1. Extract a source-linked evidence table once.
2. Validate the table's numerical structure and compute its implied probabilities in code.
3. Keep the table, source links, and probabilities as separate parts of the knowledge state.

This is a posthoc finding, not an independently confirmed one-call condition. It needs a fresh
evaluation before claiming equivalent performance with the second pass removed.

## Research interpretation and next substantive test

Using an LLM to represent a problem and external code to calculate an answer is established in
[Program of Thoughts](https://arxiv.org/abs/2211.12588) and
[Faithful Chain-of-Thought](https://arxiv.org/abs/2301.13379). The calculator component is not a
novel contribution. This pilot identifies a specific evidence-mapping failure and tests whether
an explicit extraction stage prevents it under controlled conditions.

The more substantive next question is whether this representation preserves warranted uncertainty
over repeated scientific updates. Compare new independent studies, repeated reports of old
studies, genuinely conflicting findings, and repeated review without new evidence. Keep original
priors separate from derived posteriors so repeated review does not accidentally reuse a posterior
as a fresh prior while recounting old evidence.

Unchanged evidence can legitimately prompt correction of a previous reasoning error. The target
is movement toward the warranted probability followed by stability, not a blanket rule against
changing confidence. New observations should produce the appropriate updates. Omitted explanations
and uncertain likelihood models are also essential later tests: today's hypotheses and numerical
predictions were supplied, exhaustive, and correctly specified. No weights have been trained.

## Reproducibility

- [Execution run](https://github.com/msblanders/wtr-bench/actions/runs/40986360489).
- [Frozen execution source](https://github.com/msblanders/wtr-bench/tree/ac3fa6acdf3f33650841833c4a487b5e1b2ec53e/experiments/scientific-confidence-v2).
- [Aggregate summary](results/summary.json) contains all prespecified comparisons and truncation counts.
- The complete original archive and posthoc diagnostic are preserved privately for the researcher.
  No raw call archive is added to this pull request.
- Original archive SHA-256: `ac5e38314ca7ce8b181849316f218d5b2a015e69ee114b4bb8b4915fe0d2982d`.

All frozen source/input/protocol hashes were verified after download. Reanalysis reproduced the
results across Python 3.11 and 3.12 with a maximum absolute numeric difference of 1.78e-15.
Original run outputs are retained unchanged. Nineteen offline checks and repository CI passed.
This findings document, source-error inspection, efficiency diagnostic, and literature discussion
were added after collection; the private archive retains the exact pre-collection protocol.
