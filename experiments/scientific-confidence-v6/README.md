# Scientific confidence v6: compact retention of inactive identities

**Completed 2026-10-30:** all 3,900 calls and the exact integrity audit succeeded. The compact policy passed the three prospective record-accuracy/cost criteria, but severe probability errors remain. See [PILOT_FINDINGS.md](PILOT_FINDINGS.md) and [aggregate results](results/summary.json). The protocol below was frozen before collection.

Prospective protocol, frozen before any paid calls. V5 found that full revision history
prevented ten additional reinstatement failures on 64 cases with identical verified starts,
but cost 42.5% more than active-only records. V6 tests whether a smaller representation can
preserve that benefit. No weights are trained.

## Conditions and information boundary

96 fresh cases, each run under three retention policies:

| Condition | Retained working state |
|---|---|
| active_checklist | Active numerical rows and their identity references; up to 120 words of notes |
| versioned_checklist | All numerical revisions, active or inactive; same notes |
| compact_index | Active numerical rows, plus one small identity/status entry for each currently withdrawn unit; same notes |

The compact index contains only canonical registry/cohort ID, latest authorized revision,
withdrawn status and document/alias references. No old estimates, SEs, designs, contexts or
hypothesis predictions are retained in index entries. Active units retain their identity
links in their numerical rows. On withdrawal, those links move into the index; on
reinstatement, they move back into the restored active row. The union of active rows and
inactive index entries preserves known identities without retaining historical numerical rows.

All three conditions receive the same verified initial state: three active studies, their
correct priors/predictions/future-study parameters, an empty index and derived beliefs.
There is no initial extraction call. All use the same schema, checklist, fixed model
specification and source-blind calculator. The schema includes identity_index for everyone;
the active-only and full-history policies output an empty list. First prompts differ only
in the retention-policy text. The compact policy text necessarily explains how its fields
are maintained: this compares representation-and-maintenance policies, not a pure field-only
ablation or a token-matched instruction manipulation.

The model must maintain the index itself. The calculator ignores it entirely: it never
resolves aliases, restores identities, fixes status or looks at source documents. Later
calls receive their own returned state, derived beliefs, fixed specification and new packet;
there is no historical source archive or evaluator correction. All policies may retain useful
history in their 120-word note. Notes and free-form references are not semantically constrained
by a numerical-memory detector.

## Cases

Main seed 20791203, 96 independent trajectories. Development seed 90791203, four separate
trajectories, excluded from efficacy analyses. The four source-study strata are sampled
independently with equal probability; unlike v5, their realized counts are not forced equal.
Alias wording is independently sampled from the same two forms. The main generator has
26 replication, 21 design-contrast, 22 unequal-precision and 27 duplicate-report cases.
Actual case seeds and all selected fixtures are disjoint from earlier experiments. No case
is chosen or discarded using model performance or numerical difficulty.

Every case follows the same 13 paid updates as v5: alias duplicate; numerical correction;
new disjoint cohort; stale superseded reprint; withdrawal; cohort context correction; stale
withdrawn reprint; new independent study sharing a project title; cohort-only withdrawal;
authorized reinstatement; subsequent numerical correction with canonical ID; subsequent
canonical-ID withdrawal; review. The latter correction uses a seeded estimate in {-0.6, 0, 0.6}
and SE 0.25, as in v5. There are five unique evidence units, at most nine historical rows,
and at most two simultaneously withdrawn-unit index entries.

Event order is fixed, so event and position effects are not separated. Hypotheses and
likelihoods are supplied and exhaustive. The reference remains the current authoritative
record under stipulated correction/withdrawal semantics, not empirical calibration over a
generative publication or selection process. The benchmark does not model overlapping samples,
ambiguous authority, model misspecification or natural full-length papers.

## Primary success criteria

The accuracy endpoint is each trajectory's fraction of incorrect active records over updates
10-13: reinstatement, subsequent correction, subsequent withdrawal and review. All comparisons
are paired on the same fresh cases. Invalid/missing states count as failures. Active fidelity
uses the established canonical-ID, revision, scope, number, prediction, original-prior and
future-parameter checks; copy tolerance 1e-5, predicted means 1e-8. It does not require the
active-only baseline to retain old rows or the full-history condition to populate an index.

Call the compact policy an accurate, cheaper replacement only if **all three** criteria pass:

1. **Benefit over active-only:** the upper endpoint of a paired 10,000-resample 95% percentile
   bootstrap interval for compact minus active-only mean error fraction is below zero.
2. **Preserved accuracy relative to full history:** a conservative one-sided 95% upper bound
   on mean degradation is below **0.05** (five percentage points of the four-update error
   fraction). For each case let D = compact error fraction minus history error fraction.
   Since D <= 1{D > 0}, a Clopper-Pearson upper bound on the probability of a worse case also
   bounds mean degradation. Compute this exact binomial upper bound from the number of cases
   with D > 0, out of 96. Better compact cases do not offset worse cases in this conservative
   rule. With zero worse cases the upper bound is 3.07%; with one it is 4.85%; with two it is
   6.41%. An ordinary zero-width bootstrap at zero discordance is not accepted as proof of
   noninferiority. A nonsignificant difference is not equivalence.
3. **Meaningful cost saving:** the upper endpoint of a paired 10,000-resample 95% interval for
   the ratio of compact to history mean API token cost over all 13 updates is below **0.90**.
   Resample case pairs and recompute the ratio of mean costs, not the mean of individual ratios.

The five-point accuracy margin and ten-percent cost target are pragmatic prospective design
choices, not universal scientific standards. Passing supports those explicit margins in this
generator and model. Report each criterion, including inconclusive or negative outcomes; do
not expand the sample after seeing results. The joint claim requires all criteria, rather than
choosing whichever comparison succeeds. Unadjusted secondary intervals support no separate
confirmatory claims. The fixed 96-case sample is not a guarantee of power under all error patterns.

Only a complete run with settled costs, no truncation and verified starting states is eligible
for the joint decision. Otherwise report an infrastructure-incomplete result, not efficacy.

## Secondary and diagnostic analyses

- All three pairwise contrasts in posterior squared error across updates 10-13 and all 13
  updates, and future-probability squared error over updates 10-13. Invalid numerical outputs
  get loss 2 (posterior) or 1 (future). Also report valid-only posterior error.
- Full-history versus active-only replication on the record endpoint.
- Per-event correctness, new errors, recovery, first-error step, wholly correct trajectories,
  difference concentration and leave-one-case-out mean ranges. Cases are the independent units.
- Retained numerical rows, index rows, inactive rows where forbidden, nonempty indices where
  forbidden, full-history fidelity, notes exceeding 120 words and token costs.
- Compact index fidelity: canonical unit set, latest revision, withdrawn status, allowed fields
  and retention of known document IDs. Extra free-form aliases are not semantically graded.
  This diagnostic never repairs state and is not an exclusion criterion.
- Number of reference updates shifting a hypothesis probability by at least five points.

Differences within 1e-8 are called numerically negligible in descriptive probability-loss
counts only. Record-error fractions and the noninferiority event D > 0 use exact discrete
values. A successful record comparison alone does not establish improved probability estimates.

## Collection, privacy and reproducibility

claude-sonnet-4-6; temperature 0; thinking disabled; 4,096 maximum output tokens; one call per
update; 12 concurrent trajectory workers. Four development cases exercise the same worker
count. 156 development + 3,744 main = **3,900 planned calls**. Expected token charges roughly
**$80-100**, combined ceiling **$150**, at $3/M input and $15/M output. Costs are estimates,
not an account invoice. Request reservations are taken before sending; uncertain charges
remain reserved. No retries, fallbacks, semantic-accuracy gate or outcome-dependent stopping.

Freeze all code, protocol, fixtures and scoring before development. The gate checks complete
tool responses, unique expected call keys, count and settled usage only. Main collection
starts only after that transport gate. Phase markers and a workflow run-attempt guard prevent
accidental paid repeats. Infrastructure errors stop new sending and preserve partial records.

Raw files stay in one runner through development, main scoring and the exact offline integrity
audit. Before upload they are encrypted and authenticated with a fresh symmetric key, wrapped
with a public RSA key. The private recovery key is saved separately before launch and is never
supplied to GitHub. Only encrypted raw artifacts and aggregate results leave the runner; public
PR prose contains aggregate findings. The final private experiment package contains the raw
data and recovery materials. Encryption checks include round-trip recovery and tamper rejection.

The exact audit runs under the original Python 3.11 environment, checking frozen hashes,
fixture regeneration, matched initial prompts across all three conditions, every state handoff,
response-record identity and aggregate replay. It makes no model calls. This avoids the tiny
cross-version floating-point replay differences seen between Python 3.11 and 3.12 in v5.

Run commands:

    python -m unittest discover -s tests -p 'test_scientific_confidence*.py' -v
    python experiments/scientific-confidence-v6/experiment.py generate --out runs/scientific-confidence-v6
    python runs/scientific-confidence-v6/experiment.py collect --out runs/scientific-confidence-v6 --phase development --budget-usd 150
    python runs/scientific-confidence-v6/experiment.py collect --out runs/scientific-confidence-v6 --phase main --budget-usd 150
    python runs/scientific-confidence-v6/audit_saved_run.py --out runs/scientific-confidence-v6
