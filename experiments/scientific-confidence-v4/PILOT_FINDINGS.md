# Provenance changes expose a reinstatement failure; broad probability gains remain unconfirmed

The new test is no longer at a ceiling. Eight previously faithful active-only trajectories
developed incorrect evidence records when a withdrawn study was reinstated. Neither
full-history condition developed a first error at that event. This is a specific lead about
retaining excluded evidence, rather than evidence that the additional multi-step instructions
generally improve scientific reasoning.

The full versioned procedure had 88.15% lower mean probability error than the active-only
baseline. However, one trajectory accounts for 99.73% of the absolute paired difference,
and the primary bootstrap interval includes zero. Almost all of the absolute difference
(99.80%) lies in trajectories already containing an initial extraction error in at least one
condition. The large average reduction should not be presented as a replicated general gain.

## Run and scope

- 1,224/1,224 calls; estimated token cost $28.165155, within the $80 ceiling.
- 72 development calls cost $1.670739 and are excluded from efficacy estimates.
- 32 independent main trajectories, three conditions, 12 checkpoints: 1,152 main outputs.
- Zero truncation or unknown-cost calls; all 1,152 main outputs yielded valid calculated probabilities.
- Model: claude-sonnet-4-6, temperature 0, thinking disabled, 4,096 output-token ceiling.
- [Main run](https://github.com/msblanders/wtr-bench/actions/runs/41009350913).
- Frozen execution commit: fa66f1cbe079e56a7a0540b9f1f18c2b6877ac2b.
- [Frozen protocol](https://github.com/msblanders/wtr-bench/blob/fa66f1cbe079e56a7a0540b9f1f18c2b6877ac2b/experiments/scientific-confidence-v4/README.md).

Events included aliases, corrections, separately enrolled cohorts, stale reports, withdrawals,
context correction, reinstatement, and review. Of 224 substantive updates, 80 changed at
least one reference hypothesis probability by five percentage points. The reference is
inference from the currently authoritative record under stipulated reporting rules, not
a full Bayesian model of why scientists publish incorrect results or withdraw them.

## Prespecified results

Lower posterior loss is better. It is squared distance from the stipulated current-record
reference posterior. Each trajectory, not each checkpoint, is an independent observation.

| Condition | Faithful active tables | Entirely faithful trajectories | Mean posterior loss | Final-checkpoint mean loss | Main API cost |
|---|---:|---:|---:|---:|---:|
| Active record + checklist | 332/384 | 21/32 | 0.00936952 | 0.00882944 | $7.175631 |
| Full revision history + checklist | 357/384 | 29/32 | 0.00889204 | 0.00872327 | $9.531747 |
| Full revision history + explicit procedure | 360/384 | 30/32 | 0.00111029 | 0.00006092 | $9.787038 |

Faithfulness checks canonical active units, revisions, scope, numerical data, hypothesis
predictions, original priors and future-study parameters, with the frozen numeric tolerances.
The prose notes and identity-reference wording are not semantically graded. Correct
active tables therefore do not establish that every part of the written state is accurate.

| Paired trajectory-mean contrast | Mean difference | Descriptive 95% bootstrap interval |
|---|---:|---:|
| Full procedure minus active checklist — primary | -0.00825923 | [-0.02477811, 0.00001134] |
| Full-history checklist minus active checklist | -0.00047748 | [-0.00141587, approximately 0] |
| Full procedure minus full-history checklist | -0.00778175 | [-0.02474497, 0.00138273] |

The history-only interval ends at -9.29e-16: effectively zero, not a robust superiority
claim. Secondary comparisons have no multiplicity-adjusted confirmatory interpretation.
The full procedure cost 36.39% more than the active baseline; history without the additional
procedure cost 32.84% more. The design matched call ceilings, not actual token consumption.

Worst hypothesis-probability errors remained substantial: 37.29 percentage points for both
checklist conditions and 27.64 points for the full procedure. A lower mean does not make the
workflow uniformly reliable.

## What failed, and when

All first errors in the full-history arms appeared at the initial extraction checkpoint:
three trajectories for the checklist and two for the explicit procedure. The active
baseline also had three initial failures, followed by eight additional first failures
at reinstatement. This timing comes from a post-hoc, read-only audit of the frozen outputs.

Immediately before reinstatement, active-state fidelity was 29/32 for the active baseline
and 30/32 for both history arms. Immediately afterward it was 21/32, 30/32, and 30/32,
respectively. The eight newly unfaithful baseline trajectories had been faithful immediately
before the event; no history trajectory made that transition.

The active baseline uniquely showed missing/extra active units and wrong revision/value
flags. Across checkpoints, its diagnostic counts were 18 missing-unit, 16 extra-unit,
two wrong-revision, two wrong-value, and 36 prediction-mapping flags. Flags overlap.
The full-history checklist had 27 prediction-mapping flags. The full procedure had 24
prediction-mapping and 12 future-parameter flags. These counts identify failure categories;
they do not by themselves establish a unique psychological mechanism.

Evidence-state accuracy and immediate probability accuracy diverged. Nineteen active-baseline
checkpoints had an unfaithful record while all hypothesis probabilities remained within half
a percentage point of the reference; the corresponding counts were three and five for the
history arms. A mistaken identifier can leave a numerical likelihood unchanged for now,
while making subsequent source updates harder to resolve.

## Why the large average improvement is not yet convincing

Using the offline audit's descriptive threshold of 1e-8 in trajectory-mean loss difference,
the full procedure was materially better in two trajectories, the baseline in one, and
29 differences were negligible. The threshold was used for the offline descriptive audit,
not as the primary significance test.

One trajectory contributed 99.73% of the sum of absolute paired differences. The post-hoc
lineage check found that 99.80% of that absolute difference came from trajectories already
unfaithful at the initial checkpoint in at least one condition. Among the 29 trajectories
initially faithful in both primary conditions, the mean paired difference was only
-0.00001829. This selected subset is descriptive: initial correctness is itself affected by
the condition, so it is not a causal subgroup estimate or a replacement primary analysis.

The primary comparison remains a valid comparison of the complete assigned workflows.
What it does not isolate is maintenance quality from independent first-call extraction
mistakes. Repeatedly carrying forward one large initial mistake can dominate a trajectory's
mean, making an apparent long-horizon advantage originate before any revision occurred.

## Retention-policy and integrity audit

The active baseline included inactive rows at only one of 384 checkpoints. Each history
condition retained inactive rows at all 320 checkpoints where history was expected, so the
retention manipulation largely worked. Mean row counts were 3.41, 5.58, and 5.58; maximum
counts were four, eight, and eight. No note exceeded 120 words (maximums 68, 78, and 61).

Retaining rows is not the same as faithfully preserving their contents. Full revision
histories were faithful at 340/384 checkpoints for the history checklist and 344/384 for
the explicit procedure. The active-only arm was not expected to retain those inactive rows.

All 32 experiment checks and repository CI passed before paid collection. Offline audits
verified frozen file hashes and unique call/record keys. Two successive reports from the
saved records produced identical aggregate summaries. No scoring-diagnostic exceptions
occurred in valid main outputs. The audits made no model calls and did not change the
frozen primary scores or prompts.

The policy/concentration audit was prepared separately; the initial-error lineage analysis
was added after observing concentration and is explicitly post-hoc.
[Final audit run](https://github.com/msblanders/wtr-bench/actions/runs/41012507633).

## Refined hypothesis and next test

A narrower hypothesis is now justified:

**Retaining explicit records of inactive evidence reduces failures when that evidence
returns, independently of the quality of the initial extraction.**

The next useful comparison should give every condition the same verified initial record
on fresh trajectories, then compare active-only versus versioned retention. Add subsequent
reports referring back to a reinstated unit so identity errors have measurable downstream
consequences. A history-only condition is the economical candidate: both history conditions
avoided the new reinstatement failures, while the added procedure has not shown a robust
extra maintenance benefit.

This would be a new experiment, not a reclassification of the present results. No further
paid test was run after this batch. No weights were trained. The current evidence remains
limited to one model/configuration, a small supplied hypothesis class, clear reporting
authority, five unique registry/cohort units, limited prose templates and 12 checkpoints.

## Files

Aggregate results are in results/summary.json and results/offline_audit.json. The original
Actions artifact contains cases, gold, frozen code/protocol, raw calls, returned records,
scores, trajectory means and the private case-level failure audit. Raw records are not
committed to the public PR.

Original archive SHA-256:
9359e3ebcb21db14d47100884b9d76719ee5c058bf68735efacbcc08a5b55108

The local execution workspace was unavailable, so the usual separate Library ZIP could not
be created. Complete run files are attached to the main Actions run with 90-day retention.
Source, protocol and aggregate findings are durably recorded in the draft research PR.
