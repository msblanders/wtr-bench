# First pilot: no demonstrated benefit from the explicit audit

The 32-case pilot completed all 224 planned API calls on 30 October 2026 UTC. Recorded
token-based cost was **$4.038996**, below the $25 guard. There were no infrastructure failures
or unknown-cost requests. This was an inference-time procedure comparison, not model training.

The calibration checklist had the lowest mean posterior error. The longer contrastive audit
did not demonstrate improvement over it. A substantial output-budget problem limits interpretation:
89 of 96 preparatory responses hit the 1,400-token ceiling, including all 32 audit preparations.
The final responses all finished; two audit probability vectors failed the normalization rule.

## Frozen primary analysis

Posterior regret is squared distance from the exact Bayesian posterior, summed over the three
hypotheses. It equals excess expected multiclass Brier loss under the supplied model. Lower is
better. Means below include each arm's valid cases, so the audit column has a different sample.
The primary comparison below the table uses only the 30 cases valid in both compared arms.

| Procedure | Valid cases | Mean posterior regret | Mean future-probability regret | Preparations cut off |
|---|---:|---:|---:|---:|
| Generic review | 32/32 | 0.00515817 | 0.00411179 | 26/32 |
| Calibration checklist | 32/32 | 0.00001373 | 0.00012884 | 31/32 |
| Contrastive audit | 30/32 | 0.00208726 | 0.00197349 | 32/32 |
| Oracle-posterior readout (diagnostic) | 32/32 | 0.000000000283 | 0.00001149 | Not applicable |

Audit minus checklist, on 30 paired cases: **+0.00207262**, descriptive bootstrap 95% interval
**[-0.00001369, +0.00621174]**. Positive means the audit was worse. This is not evidence of an
audit benefit, nor a precise estimate of its intrinsic effect without truncation. Differential
invalidity also prevents an unqualified efficacy comparison. Do not interpret realized Brier scores
from the 30-case audit subset as superiority over a different 32-case baseline sample.

The supplied-posterior control nearly reproduced its given probabilities and had low future
prediction error. This checks part of the output pipeline; it does not validate scientific judgment.

## Posthoc inspection: concrete failure modes

These observations were made after collection. They motivate new hypotheses, not confirmatory
claims about why the procedure failed.

- **SC006, audit:** its preparation correctly calculated approximate log weights -4.423 and
  -3.761 for H2 and H3, but was cut off during exponentiation. The final answer treated H2's
  relative weight (about 0.516, versus H3's weight 1) as H2's probability. It returned H2=0.516,
  H3=0.484; the exact posterior is H2=0.340250, H3=0.659750. This case contributes most of the
  audit's posterior error. Correct intermediate calculations did not guarantee a correct update.
- **SC027, generic review:** it identified duplicate reports correctly, but substituted +0.4
  for H1's observational-context-B mean, which was -0.2. It confidently computed probabilities
  from that incorrect mapping. The final H1 probability was 0.5862 versus the correct 0.270480.
  Its location in the duplicate-report stratum does not establish a duplicate-counting error.
- **SC023, generic review:** it copied H2's likelihood contribution into H3's randomized-B
  contribution despite their different means. It also used an incorrect Normal-tail value.
  A coherent-looking table and calculation can preserve a mistaken association.
- **SC015 and SC028, audit:** the final probability sums were 1.0085 and 0.994, respectively,
  outside the frozen 0.005 tolerance. These were numerical invalidities, not malformed JSON or
  truncated final outputs. They were not repaired or rescored into the primary analysis.

## Revised hypothesis worth testing

**An operator that maintains explicit links between evidence, candidate explanations, and their
predictions, then delegates probability arithmetic to a verified calculation, will outperform a
verbal audit on new evidence-synthesis cases.** The two components should be tested separately.

For a clean next experiment:

1. First resolve the output-budget issue using development cases and a predeclared sufficient
   budget or compact intermediate schema. Repeat the original comparison on fresh cases.
2. Separate extraction/mapping quality from arithmetic: compare a checked evidence table alone,
   calculator access alone, both, and the strong checklist. Give calculator access equally when
   testing whether the representation itself adds value. On this fully specified task, a correct
   table plus exact arithmetic solves the inference problem by construction; that alone would
   not establish a novel general reasoning capability.
3. For the residency's iterative focus, retain original priors and study IDs in the knowledge
   state. Test repeated review, genuinely new studies, and repeated reports separately. No new
   evidence should not cause systematic confidence inflation.
4. Only then move to underspecified text, omitted hypotheses, or training with proper rewards.
   Use new evaluation cases and a separately fitted posthoc calibration baseline.

This pilot supplies a working verifier and baseline, plus specific errors to target. It does not
prove a general scientific-reasoning improvement or a novel training method.

## Reproducibility and provenance

- [Run](https://github.com/msblanders/wtr-bench/actions/runs/40982969430)
- [Frozen execution commit](https://github.com/msblanders/wtr-bench/tree/d40a102dbd9024b2f233213a532bead5221f9a50/experiments/scientific-confidence-v1)
- [Complete original archive](results/pilot-20261030.zip): all requests/responses, input and gold
  cases, original runner, original protocol, manifest, scores, summary, and spend ledger.
- [Machine-readable summary](results/summary.json) and [per-case scores](results/scores.json).
- Archive SHA-256: `2313acf754e4a406e0ad5de29a63443b4f458488b9b52c6a1f1d405272330dc6`.

All frozen source/input/protocol hashes were verified after download. Reanalysis of the original
responses reproduced the results within 1e-14 absolute numerical tolerance across Python 3.11
and 3.12; minor last-bit floating-point differences occurred. Archived outputs are the original
run's files. Later repository lint changes affect exception handling/string layout, not prompts,
cases, or scoring rules. The README's follow-up discussion and this interpretation were added
after the run; the archive retains the original protocol. Ten offline tests and repository CI pass.
