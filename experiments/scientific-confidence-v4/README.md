# Scientific confidence v4: changing evidence provenance

Prospective protocol, frozen before API collection. This follows the v3 ceiling result:
a simple structured record and calculator handled clean repeated updates, and extra ledger
instructions added no meaningful benefit. V4 changes identity, revision, withdrawal, and
scope requirements. It does not train weights or claim a new reasoning architecture.

## Question and conditions

Does a versioned evidence record improve probability updates when sources are renamed,
corrected, withdrawn, superseded, or reinstated? Can any gain be attributed to retaining
history versus additional procedural instructions?

| Condition | Retained evidence | Instructions | Readout |
|---|---|---|---|
| active_checklist | Current active rows plus identity references and a short note | General calibration checklist | Common source-blind calculator |
| versioned_checklist | All revisions, including superseded and withdrawn rows | Same checklist | Same calculator |
| versioned_operator | Same full revision history | Explicit identity/revision/scope update procedure | Same calculator |

All use the same output schema and call ceiling. The active baseline may preserve historical
information in identity_refs for active units and in its 120-word evidence_basis. It is not
forbidden to remember withdrawals in prose. It omits inactive rows by design. Full-history
conditions retain those rows explicitly. Thus the history comparison tests a representation
and retention policy, with potentially different token costs; it is not a token-matched
instruction-only comparison. The operator-versus-versioned-checklist contrast holds that
representation policy fixed.

All arms receive the same fixed hypothesis specification and incoming packet, their own
previous returned record, and beliefs calculated from that record. They do not receive the
full historical source archive or oracle corrections. The common rules already explain
revisions, withdrawals, distinct cohorts, and aliases. This is a strong, informed baseline.

## Cases and event sequence

32 fresh independent trajectories, seed 20591203. Two separate development trajectories,
seed 90591203, are excluded from efficacy estimates. Hypothesis labels, priors, numerical
observations, registry identifiers and project names vary across trajectories. There are
two alias-wording variants. This is limited template diversity, not natural papers.

Every trajectory has 12 checkpoints:
1. Three initial independent studies.
2. An unchanged report under a project alias, referring to the original document.
3. An authoritative numerical correction replacing estimate and SE.
4. A separately enrolled cohort sharing a registry but not participants with an existing unit.
5. A newly published reprint of the superseded values.
6. Withdrawal of all revisions of one evidence unit.
7. A correction to the new cohort's context, changing the relevant hypothesis predictions.
8. Reappearance of a withdrawn estimate under another title, without reinstatement.
9. A genuinely new study sharing a project title but having distinct registry and participants.
10. Withdrawal confined to one cohort; the main cohort remains valid.
11. Explicitly authorized reinstatement of a previously withdrawn unit as a new revision.
12. Review without new evidence.

There are five unique registry/cohort units and at most eight historical revision rows.
The new cohort is disjoint, not a statistically overlapping subgroup. Scope reasoning is
tested through a context correction and cohort-specific withdrawal. No covariance estimation
or overlapping-sample meta-analysis is claimed. Event type and position are fixed together,
so event-specific results are descriptive rather than causal estimates of difficulty.

## Reference answer and its limits

The reference is the posterior calculated from the **currently authoritative active record**
under the supplied Normal likelihoods and original priors. A deterministic evaluator updates
that record from the scripted, unambiguous amendment events. Initial estimates and replacement
values use the v1 generator plus independent seeded draws/perturbations; all displayed
non-simple numbers are rounded to 12 significant digits before scoring.

This is a normative record-consistency benchmark. It is **not** a fully specified Bayesian
generative model of erroneous publications and the selection process that produces corrections
or withdrawals. The task explicitly stipulates that superseded values and withdrawal notices
supply no additional likelihood. We do not claim empirical calibration about the latent true
mechanism over the entire reporting history. Hypotheses remain supplied, exhaustive and
correct for the stipulated current-record calculation; real-world model misspecification,
publication bias and genuinely ambiguous authority remain outside this test.

Gold contains the authoritative state and target probabilities at each checkpoint and is
never sent to model calls. The source-blind calculator filters model rows marked active,
rejects multiple active rows for the same canonical ID, and performs the common probability
calculation. It does not resolve aliases, choose the latest revision, determine scope,
repair a status or number, or consult source documents. Incorrect but structurally valid
states therefore remain incorrect. Source/history diagnostics are evaluation only.

## Prespecified analyses

**Primary:** versioned_operator minus active_checklist in each trajectory's mean posterior
loss across all 12 checkpoints. Negative favors the proposed bundle. Use a paired
10,000-resample percentile bootstrap over the 32 independent trajectory means.

Secondary component contrasts:
- versioned_checklist minus active_checklist: history-retention policy.
- versioned_operator minus versioned_checklist: additional update procedure.

These three arms do not identify the missing active-record + operator cell of a full
factorial design. Component contrasts are conditional and cannot establish a general
history-by-instruction interaction. Secondary intervals are descriptive, without a
multiplicity-adjusted confirmatory claim.

Posterior loss is squared distance from the current-record reference posterior; future
loss is squared distance from its Normal-tail predictive probability. Invalid/missing
outputs receive posterior loss 2 and future loss 1. Report valid-only results too. An
infrastructure-incomplete run is not an efficacy finding.

Also report faithful active sets, active revisions, design/context, copied numbers and
hypothesis-specific predictions; full-history fidelity in the versioned arms; final-step
loss; costs; and error types (missing/extra units, reactivated obsolete revisions, wrong
scope, values, predictions, priors or future parameters). Numeric-copy tolerance is 1e-5;
predicted-mean tolerance is 1e-8. Identity reference wording and the prose note are not
semantically graded. Active fidelity does not require an active-only baseline to retain
inactive historical rows.

Adjacent valid outputs also get update-error and belief-movement diagnostics. Corrections
during no-new-evidence review are permitted; unchanged evidence does not mean a previous
mistake must be preserved. Invalid transitions remain penalized in the primary metric.
Report how many substantive events change a target probability by at least five percentage
points, so a nearly uninformative dataset is visible.

If the conditions again reach a ceiling, report the null result. Do not retrospectively
select difficult cases, extend collection, change prompts, or call a small numerical
rounding difference an operator improvement.

## Collection and reproducibility

Model: claude-sonnet-4-6, temperature 0, thinking disabled, 4,096 maximum output tokens
per call. One call per update. Eight workers, independent trajectories. 72 development
plus 1,152 main calls = **1,224 planned calls**. Combined spending ceiling **$80**.
Costs use returned usage at the existing $3/M input and $15/M output rates; these are
estimates, not an account invoice.

The development gate checks transport, finished tool responses, settled usage and count,
not source accuracy or reasoning success. Main fixtures and all prompts are frozen before
development. There are no automatic retries, model fallbacks, case rerolls, or score-based
stopping. Ambiguous infrastructure failures retain reservations and stop new sending.
Phase markers and a run-attempt check prevent repeating collection. On a missing tool
response, the previous parseable state is retained without adding missed evidence; a
calculator error is passed back with the returned record on the next update.

Code checks cover revision/withdrawal/scope semantics, neutral-event invariance, numerical
agreement with the prior oracle, source-blind errors, matching schemas, gold isolation,
budget enforcement and split-phase collection. Tests run in repository CI before spending.
The exact runner, support files, protocol, cases, gold and hashes are frozen in the artifact.
Aggregate results may be recorded in the draft PR; raw calls and case-level audits are not
committed publicly. The complete run artifact is retained in Actions for 90 days.

The local execution workspace was unavailable during preparation. Code, offline checks,
collection and artifact creation therefore run in the existing GitHub Actions environment.
This changes execution location, not the scientific comparisons.

Run commands:
    python -m unittest discover -s tests -p 'test_scientific_confidence*.py' -v
    python experiments/scientific-confidence-v4/experiment.py generate --out runs/scientific-confidence-v4
    python runs/scientific-confidence-v4/experiment.py collect --out runs/scientific-confidence-v4 --phase development --budget-usd 80
    python runs/scientific-confidence-v4/experiment.py collect --out runs/scientific-confidence-v4 --phase main --budget-usd 80
    python runs/scientific-confidence-v4/experiment.py report --out runs/scientific-confidence-v4
