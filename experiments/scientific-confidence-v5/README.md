# Scientific confidence v5: identical verified starting records

**Completed:** 1,716 calls, $39.39, no truncation. With identical verified starts, full history reduced post-reinstatement record errors by 15.63 percentage points (paired 95% interval 7.81-25.00). Mean posterior error also fell on the secondary outcome. See [findings](PILOT_FINDINGS.md).

Prospective protocol. Freeze this file, code, all cases and reference states before any
paid call. V4 suggested a specific reinstatement failure in active-only records, but its
large probability-loss difference was dominated by an initial extraction error. This
test separates initial extraction from maintaining a changing evidence record.

## Hypothesis and intervention

Retaining explicit inactive evidence rows reduces active-record errors when a previously
withdrawn unit is reinstated and subsequently amended. The two conditions are:

| Condition | Working record | Other instructions and readout |
|---|---|---|
| active_checklist | Active rows; historical information permitted in their identity references and a 120-word note | Shared calibration checklist, source-blind calculator |
| versioned_checklist | All revisions with active/superseded/withdrawn status; same note allowance | Same checklist and calculator |

Both conditions receive the **same independently verified initial structured record**,
original priors, predicted means, future-study specification and calculated starting beliefs.
The initial record has only active rows and no condition-specific edits. There is no initial
model extraction call. Every later call sees only its own previous returned state and derived
beliefs, the common model specification, and the new packet. There is no subsequent oracle
feedback or historical source archive. The calculator does not repair identity, scope,
revision, status or extracted values. Malformed output retains the last parseable working
state; a calculator error is returned with the model's record on the next update.

This estimates a retention-policy and representation effect, including its token cost.
It is not a token-matched pure reasoning comparison. The active condition can preserve the
two withdrawn units' identities in its note; it is not forbidden from remembering history.
The extra procedural operator from v4 is omitted because its incremental maintenance
benefit was not established. No weights are trained.

## Cases and events

64 fresh independent main trajectories, seed 20691203; two separate development trajectories,
seed 90691203. All are frozen together. The seed schedules are disjoint from v1-v4. Numerical
observations, hypothesis labels/priors, registry identifiers and project aliases vary. The
limited templates and two alias-wording variants are inherited from v4. This is not a study
of natural papers, ambiguous sources or overlapping participant samples.

The verified starting record contains three independent studies. Each model then performs
13 paid updates, in this fixed order:

1. Alias duplicate of an initial study.
2. Numerical correction, superseding its original revision.
3. A disjoint cohort under another existing registry.
4. Stale reprint of the superseded result.
5. Withdrawal of all revisions of the corrected unit.
6. Context correction for the new cohort, requiring different predicted means.
7. Stale reprint of the withdrawn unit, without reinstatement.
8. New independent study sharing a project title with an old report.
9. Withdrawal of the additional cohort only.
10. Authorized reinstatement of the first withdrawn unit as revision 3, identified by old document references.
11. Correction to revision 4, now giving the canonical registry/cohort and referring to revision 3.
12. Withdrawal of every revision of that canonical registry/cohort.
13. Review without new evidence.

Steps 1-10 match the v4 event types with fresh draws. Step 11 uses a seeded draw from
effect estimates {-0.6, 0, 0.6}, SE 0.25, with unchanged design/context. These are stipulated
replacement values, not draws from a calibrated model of the publication process. Giving
the canonical identity in later packets lets a model correct an earlier alias mistake;
recovery is allowed and measured. Numerical leverage is reported, not used to select cases.
There are five independent units and at most nine historical rows. Event type and position
are fixed together, so event summaries cannot identify a causal position effect.

## Primary endpoint and interpretation

**Primary:** versioned_checklist minus active_checklist in the trajectory's fraction of
incorrect active records over steps **10-13** (reinstatement, subsequent correction,
subsequent withdrawal, review). Negative favors history retention. This is a prospective
test of the specific maintenance hypothesis suggested by v4, not a re-use of its cases.

A record is correct only if its active canonical units, revisions, design/context, copied
estimate/SE, hypothesis-specific predictions, original priors and future-study parameters
match the reference. Tolerances: copied numbers 1e-5, predicted means 1e-8. Incorrect or
missing records count as failures. Inactive-row retention is not required for active fidelity.
Identity-reference wording and prose notes are not semantically graded. Also report complete
revision-history fidelity, including inactive rows, separately.

Use a paired 10,000-resample percentile bootstrap over the **64 independent trajectories**.
The four checkpoints within a trajectory are not independent. A primary interval fully below
zero supports the narrow maintenance benefit in this setting; an interval including zero is
inconclusive. Report the raw paired difference, per-arm counts, discordant trajectories and
leave-one-trajectory-out mean range. The sample size is a fixed follow-up choice, not a
formal power guarantee. No post-treatment subset is used for the primary comparison.

Secondary endpoints, without multiplicity-adjusted confirmatory claims:

- Mean squared distance from the reference posterior over steps 10-13 and over all 13 updates.
- Future-study probability squared error over steps 10-13.
- Per-event fidelity, transitions into error and recovery, first-error position, and entirely
  faithful trajectories. Errors before reinstatement remain in the main estimand.
- Full-history fidelity, retention-policy adherence, notes exceeding 120 words, token usage/cost.
- Number of reference updates moving any probability by at least five percentage points.
- Concentration of paired differences; differences within 1e-8 are labeled numerically
  negligible for descriptive trajectory counts, not used as a significance threshold.

Invalid posterior outputs receive loss 2; invalid predictive outputs receive loss 1. Valid-only
posterior means are also reported. A more faithful table alone does not establish better
probability estimates: evaluate both and report if gains are only representational.

The reference is the current authoritative active record under the supplied exhaustive
hypotheses and independent Normal likelihoods. Original priors are used each time;
corrections replace old values, and withdrawals themselves supply no likelihood. This is
**normative record consistency**, not empirical calibration about real scientific mechanisms
or a fully Bayesian model of erroneous publication, correction and selection processes.

## Collection and safeguards

Use the same model/configuration as v4: claude-sonnet-4-6, temperature 0, thinking disabled,
4,096 maximum output tokens, one call per update, eight concurrent trajectory workers.
52 development plus 1,664 main calls = **1,716 planned calls**. Combined ceiling **$80**;
expected token charges roughly $35-45 based on v4. Costs use returned usage at $3/M input
and $15/M output; these are token-cost estimates, not an account invoice.

Development checks transport, unique expected call keys, finished tool responses, settled
usage and count only. It does not gate on reasoning accuracy. No retries, model fallbacks,
case rerolls, selective replacement, result-based prompt changes or accuracy-based stopping.
Freeze before development. Preserve reservations on ambiguous failures and stop new sending.
Phase markers and run-attempt checks prevent accidental paid repeats. An incomplete
infrastructure run is not an efficacy result.

Before spending, check initial-state identity and reference correctness, amendment semantics,
source-blind calculator behavior, information boundaries, numerical leverage, no seed overlap,
primary scoring and full mocked split-phase collection. Existing scientific-confidence tests
also run. The frozen artifact contains exact code, support modules, protocol, fixtures,
hashes, raw requests/responses and aggregate analysis. Aggregate findings and source may
be committed to the existing draft PR; raw records are not committed publicly.

Commands:

    python -m unittest discover -s tests -p 'test_scientific_confidence*.py' -v
    python experiments/scientific-confidence-v5/experiment.py generate --out runs/scientific-confidence-v5
    python runs/scientific-confidence-v5/experiment.py collect --out runs/scientific-confidence-v5 --phase development --budget-usd 80
    python runs/scientific-confidence-v5/experiment.py collect --out runs/scientific-confidence-v5 --phase main --budget-usd 80
    python runs/scientific-confidence-v5/experiment.py report --out runs/scientific-confidence-v5
