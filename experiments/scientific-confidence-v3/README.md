# Scientific confidence v3: fresh confirmation and sequential evidence updates

**Completed:** 1,360 calls, $23.62, no truncation. The one-call finding replicated on 64 fresh cases.
Both state-maintaining procedures were accurate throughout the sequential test; added ledger
instructions showed no meaningful benefit. See [findings](PILOT_FINDINGS.md).

Protocol written before API collection. Two separate experiments, one model/configuration,
no weight training, no case selection or score-dependent prompt tuning. The code is AI-assisted.
This extends the [v2 findings](../scientific-confidence-v2/PILOT_FINDINGS.md).

## Experiment A: confirm the post-hoc one-call finding

64 fresh cases (16 per original v1 design stratum), seed 20371101. Each case uses the EXACT
v2 ledger preparation call and then the EXACT v2 worksheet final call. Score the first table
and final table through the same source-blind calculator. The first call is shared between
paths; the two-call path includes its cost. The model's final stated probabilities are not
part of this confirmation. No source correction is allowed.

The prespecified practical confirmation criterion requires ALL of:

- The upper endpoint of a case-paired, 10,000-resample percentile bootstrap 95% interval
  for mean posterior loss(one call) minus loss(two calls) is below 0.001.
- At least 95% of first-call tables are source-faithful under the v2 tolerances.
- At least 95% of first-call results put every hypothesis within 0.005 of the exact
  probability (half a percentage point).

The margin is chosen before these results, not estimated from them. This is a practical
criterion, not proof of universal equivalence. Report absolute errors, failures, fidelity,
paired differences, and actual token cost. Matching a bad two-call path is insufficient.
Four separate development cases use seed 90371101. They are excluded from estimates.

## Experiment B: preserve a scientific evidence state across updates

32 independent trajectories, seed 20481101. Each has 12 checkpoints: initial two studies;
new study; duplicate reports; review; new study; duplicates; review; new study; duplicates;
review; new study; review. Six unique studies in total. There are three repeated reports
in each duplicate packet; IDs explicitly identify the original observation. Reports are
short prose with design, context, effect estimate, and standard error. The model maps this
prose into the evidence table. Hypotheses, original priors and the future-study specification
remain available at every checkpoint.

The first four studies use the unchanged v1 generator; two more randomized studies are
sampled under the same hidden mechanism, in contexts B and A. All trajectories come from
the stated generative model. We do not filter for disagreement or adverse model responses.
New evidence can conflict with earlier evidence, but not every trajectory is guaranteed to
have opposite-sign observations. The actual prevalence of conflict must be reported.
Presented estimates are rounded to 12 significant digits before constructing the oracle.
The hypotheses remain mutually exclusive, exhaustive and correctly specified; likelihoods
and priors are known. This is controlled scientific model comparison, not open-ended science.

| Condition | Information on each call | Update procedure | Probability readout |
|---|---|---|---|
| checklist_state | Prior working state + incoming packet + fixed model specification | General calibration checklist | Same deterministic calculator |
| ledger_state | Identical information | Explicit provenance, original-prior separation, unique-study counting, cell-by-cell mapping checks | Same calculator |
| ledger_rebuild | All original reports to date + fixed model specification; no prior model state | Same explicit ledger procedure | Same calculator |

All conditions produce the SAME schema: priors, study rows, future-study parameters, and
at most 120 words of evidence_basis. No model-stated probability is requested. The two state
conditions receive their own previous table, evidence_basis, and the calculator's derived
posterior/future probability. They do not receive the original historical reports again.
The common instruction already asks for original priors and all unique studies, so the
checklist is a strong baseline; this tests the added procedural discipline, not merely the
availability of a table or calculator. Schemas/call ceilings are matched; actual input/output
lengths and costs need not be equal. Rebuild is an archive-access diagnostic, not a clean
same-information estimate of the instruction's causal effect.

Calculator outputs are derived solely from model-produced state; gold and source diagnostics
are never feedback. The calculator has the same mechanical duplicate handling in every arm:
identical study IDs with identical rows count once; inconsistent copies invalidate the table.
It does not verify IDs, means, priors or numbers against the original documents. Source
errors therefore can persist. If no parseable state is returned, the last parseable state
is retained without inserting the missed evidence. If the calculator fails, the model sees
the returned table and an error type at the next step. No retry or automatic source repair.

**Primary:** ledger_state minus checklist_state in each trajectory's mean posterior loss
across all 12 checkpoints. Negative favors the operator. Bootstrap the 32 paired trajectory
means (10,000 resamples); checkpoints are not independent replicates. Secondary: ledger_state
minus ledger_rebuild, final-checkpoint error, source fidelity, cost, and losses by update type
and step. Event type and checkpoint position are not independently randomized; event summaries
are descriptive, not causal estimates of event difficulty. No multiplicity-adjusted claims.

For every valid adjacent pair, report actual belief movement and squared error in the update
relative to the exact posterior change. At duplicate/review steps, report whether error decreases
or increases. **A no-evidence review is allowed to correct earlier mistakes.** Movement alone
is not a failure; excessive confidence is not the only possible error. Invalid transitions
are excluded only from these movement diagnostics, with their count reported; primary loss
retains invalid outputs at the prespecified penalty. Two separate development trajectories
use seed 90481101, excluded from efficacy estimates.

## Shared scoring, collection, and stopping

Posterior loss is squared Euclidean distance from the exact posterior (excess expected
multiclass Brier loss). Future loss is squared distance from the exact predictive probability.
Invalid/missing posterior outputs get loss 2; invalid/missing future outputs get loss 1.
Also report valid-only losses, invalid counts, source fidelity (means tolerance 1e-8; other
copied numbers 1e-5), and maximum hypothesis probability error. These measure probability
accuracy in a specified model; they are not a calibration curve or proof of real-world truth.

All calls: claude-sonnet-4-6, temperature 0, thinking disabled, 4,096 maximum output tokens.
Eight workers. 80 development calls and 1,280 main calls = **1,360 planned calls**. Main data
and protocol are frozen before development. The development gate checks only API transport,
completed tool responses, settled usage, and the expected number of calls. It does NOT require
correct probabilities, source fidelity, or zero reasoning errors. If it fails, preserve the
partial run and diagnose; no repeated paid attempt on the same run. No main-results-based
stopping or case replacement. Infrastructure failures stop new requests and preserve artifacts.

Combined **$80 ceiling**, with reservations before sending and usage reconciliation afterward;
main restores development spending. Charges are estimated at $3/M input and $15/M output,
not an invoice. Costs and uncertain charges are reported. Run-attempt and phase markers prevent
accidental repeat billing. Offline code checks cover the oracle, duplicate/review invariance,
state corruption, gold isolation, budget handling and split-phase collection. They do not
require the experimental model to be error-free.

Raw requests, responses, cases, gold, frozen runner, hashes and usage remain in the private
research archive. Only source code, protocol and aggregate findings belong in the public PR.
The design does not modify other experiments or train a model.

## Reproduce

```bash
python -m unittest discover -s tests -p 'test_scientific_confidence*.py' -v
python experiments/scientific-confidence-v3/experiment.py generate --out runs/scientific-confidence-v3
# Paid, only with an explicitly configured key:
python runs/scientific-confidence-v3/experiment.py collect --out runs/scientific-confidence-v3 --phase development --budget-usd 80
python runs/scientific-confidence-v3/experiment.py collect --out runs/scientific-confidence-v3 --phase main --budget-usd 80
python runs/scientific-confidence-v3/experiment.py report --out runs/scientific-confidence-v3
```

Twelve updates are a first substantive sequential test, not Elicit's thousand-iteration target.
A null difference would suggest the extra instructions add little beyond a shared table,
calculator and strong common instructions. Perfect results would expose a task ceiling and
motivate harder provenance/model-misspecification tests, not more repetitions of an easy task.
