# Scientific confidence v5: history retention improves maintenance from a verified start

Completed October 30, 2026. **1,716/1,716 calls; $39.391224 in estimated token charges;
zero truncated or unknown-cost calls.** All 1,664 main calculated outputs were valid.

The prospective primary result supports the specific hypothesis: retaining explicit inactive
evidence reduced record errors when withdrawn evidence returned, even when both conditions
started with the same correct record. The advantage persisted through a later correction,
withdrawal and review. Probability estimates also improved on a secondary measure.

## Design

64 fresh paired trajectories, each with an identical verified three-study starting record.
No initial model extraction call. Each condition then performed 13 updates involving aliases,
revisions, withdrawals, cohort scope and reinstatement. Two separate development trajectories
checked transport/completion, not reasoning accuracy, and are excluded from efficacy estimates.

The only instructed difference was retention policy: active rows plus a short note versus
all active and inactive revisions plus the same note allowance. Both used the same checklist,
output schema, hypothesis specification and source-blind calculator. The active condition was
allowed to preserve historical identities in its note. Extra procedural instructions from v4
were omitted. Neither condition received later evaluator corrections.

Model: claude-sonnet-4-6, temperature 0, thinking disabled, 4,096 output-token maximum.
Protocol, fixtures and scoring were frozen before development. There were no retries,
fallbacks, rerolls, score-based stopping or prompt changes during collection.

## Primary result

The primary endpoint was the trajectory's fraction of incorrect active records over four
checkpoints: reinstatement, subsequent correction, subsequent withdrawal and review.

| Measure | Active-only record | Full revision history |
|---|---:|---:|
| Correct post-reinstatement records | 212/256 (82.81%) | 252/256 (98.44%) |
| Post-reinstatement error fraction | 17.19% | 1.56% |
| Entirely correct post-reinstatement trajectories | 53/64 | 63/64 |
| Correct records across all 13 updates | 786/832 | 826/832 |
| Entirely correct trajectories across all updates | 53/64 | 63/64 |
| Main-collection token cost | $15.746781 | $22.439226 |

**History minus active-only error fraction: -0.15625.** Paired 95% percentile-bootstrap
interval: **[-0.25000, -0.078125]**, or **15.63 percentage points fewer errors,
interval 7.81-25.00 points**. The bootstrap resampled 64 complete paired trajectories,
not 256 independent checkpoints.

Ten trajectories favored history, none favored active-only, and 54 tied on this endpoint.
Each of the ten contributes 10% of the absolute paired difference. Removing any one
trajectory leaves the mean difference between -15.87 and -14.29 percentage points.
Thus the primary result is not driven by one trajectory.

## Where the errors arose

Both conditions were correct on every case through update 7. At update 8, adding a new
study, both made a prediction-mapping error in the same case. It persisted in both conditions.
At reinstatement, ten additional active-only trajectories became incorrect; no additional
history trajectory did. All ten remained incorrect through the remaining updates.

| Update | Correct active-only records | Correct history records |
|---|---:|---:|
| Each of updates 1-7 | 64/64 | 64/64 |
| 8: New independent study | 63/64 | 63/64 |
| 9: Cohort-specific withdrawal | 63/64 | 63/64 |
| 10: Reinstatement | 53/64 | 63/64 |
| 11: Subsequent correction | 53/64 | 63/64 |
| 12: Subsequent withdrawal | 53/64 | 63/64 |
| 13: Review | 53/64 | 63/64 |

At the ten new active-only failures, the expected canonical unit was missing in all ten;
six also contained an extra active unit. Three had incorrect revision/value flags, and one
had scope/prediction flags. Flags can overlap. These are observed record failures; they do
not by themselves reveal the model's internal cognitive mechanism.

Five of those ten trajectories later had a hypothesis-probability error exceeding half a
percentage point. The remaining five still failed the record criterion without a probability
loss above the descriptive 1e-8 trajectory threshold. Record identity and numerical accuracy
are therefore related but distinct outcomes.

## Probability estimates: secondary evidence

| Measure | Active-only record | Full revision history |
|---|---:|---:|
| Mean posterior squared error, updates 10-13 | 0.03793091 | 0.01354325 |
| Mean posterior squared error, all updates | 0.01390519 | 0.00640129 |
| Mean future-probability squared error, updates 10-13 | 0.00530315 | 0.00114950 |
| Post checkpoints within 0.5 percentage points on every hypothesis | 236/256 | 252/256 |

Post-reinstatement posterior error fell **64.29%**. The paired mean difference was
**-0.02438766**, with descriptive 95% bootstrap interval **[-0.05939485, -0.00042823]**.
Five trajectories had a difference greater than 1e-8 favoring history; none favored active-only.
One trajectory accounted for 55.71% of the absolute probability-loss difference, so this
secondary outcome remains concentrated. Removing any one trajectory still leaves a negative
mean difference (-0.02477477 to -0.01097392); this is a sensitivity summary, not an additional
confirmatory test. Secondary intervals are not multiplicity-adjusted.

The common prediction-mapping error accounts for the history condition's remaining material
probability error. The full-history condition is not error-free: retaining old evidence does
not ensure correct mapping of new evidence to hypotheses.

These losses compare probabilities with the stipulated current-authoritative-record reference.
They do not establish empirical calibration about real scientific mechanisms or a fully
Bayesian model of publication, correction and withdrawal selection.

## Cost, adherence and limits

History cost **42.50% more** during main collection: $22.439226 versus $15.746781.
Development cost $1.205217. Total usage: 4,965,258 input and 1,633,030 output tokens,
priced at $3/M and $15/M respectively. Token charges are estimates, not an account invoice.

Mean retained rows were 3.39 versus 6.38. Active-only output included inactive rows once;
history included inactive rows at all 768 main checkpoints where history was expected.
No note exceeded 120 words. Full revision-history content was faithful at 765/832 history
checkpoints, including 209/256 post-reinstatement checkpoints. Correct active evidence thus
does not imply perfectly preserved inactive history. Prose notes and identity-reference
wording were not semantically graded.

The result concerns one model/configuration, five evidence units, short generated packets,
13 updates and limited event templates. Event type and position were fixed together.
Retention policy changes both representation and token use; the comparison is not token-matched.
All hypotheses and likelihoods are supplied. No weights were trained. Larger archives,
ambiguous authority, overlapping samples, model misspecification and real papers remain untested.

## Reproducibility

- Frozen source/configuration commit: `f16b4a2810c3ddf6371bdb4f2a5e96b32edd8b18`.
- Source/configuration passed repository CI before launch; all 37 scientific-confidence tests passed.
- Two aggregate reports generated from the saved run were identical.
- Exact integrity audit passed; aggregate audit results are in `results/integrity_audit.json`.

The integrity audit uses the original Python 3.11 environment and verifies frozen hashes,
fixture regeneration, unique complete call/record keys, matched first requests, every state
handoff, response-to-record identity and exact aggregate replay. A local Python 3.12 attempt
found only sub-7e-16 differences in regenerated derived probabilities; source packets and
record fields were unchanged. The exact audit was therefore run under the original runtime,
without changing scores or tolerances and without any model calls.

Source, protocol and aggregate findings are in draft PR #12. Raw requests, responses and
case-level failure records, original archive checksums and run references are preserved in
the private complete experiment package. This public report contains aggregate findings.
The private package also preserves the recovered original v4 archive.

## What this establishes and the next question

The evidence supports a bounded inference-time intervention: **keep explicit records of
inactive evidence so later reinstatements and amendments can be reconciled with the correct
unit**. This survived equal verified starts and produced downstream probability benefits in
some cases. It is stronger evidence for this maintenance procedure than v4's initial result.

A useful next test is whether a compact, persistent identity/status index can preserve the
benefit at lower cost than full numerical revision history. That would separate the value
of retained identity links from the cost of repeatedly emitting every old row. This next
test has not been run.
