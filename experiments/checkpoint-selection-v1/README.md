# Does checkpoint selection hide useful preference learning?

Prospectively specified follow-up to `search-budget-v1`, authorized October 30, 2026.
The preceding exploratory comparison suggested that selecting the lowest combined development
error can discard checkpoints with stronger choice-history learning. This study tests a
specific alternative on fresh training and evaluation seeds. It does not change the training
objective or claim that checkpoint selection changes the underlying training trajectory.

## Fixed design

- Eight independent paired runs; two readouts (`interaction`, `wide_control`), each with
  269 parameters and four memory values; evolutionary and matched-gradient optimization.
- 32 training trajectories. Each trajectory supplies both 512- and 2,048-update budgets
  and all three checkpoint policies. There are 192 policy/budget model records, potentially
  sharing identical parameter vectors. Random search is omitted because this test concerns
  checkpoint policy rather than optimizer superiority.
- Both choice and execution remain in training fitness: their equally weighted observed
  Brier errors. The unchanged model, world and external-game source is inherited from
  `search-budget-v1`. `baseline.py` is an unchanged copy of that experiment's implementation;
  shared scoring, donor intervention and integrity helpers are reused explicitly.
- The same 32,768 distinct training lifetimes form a bank of 512 batches of 64. The shorter
  budget makes one pass; the longer makes four passes, with later passes reshuffled.
  Population 32, elites 8 and all optimization hyperparameters remain unchanged.
- The original 256-lifetime development set, with its mixture of history lengths including
  zero, is retained in design but generated with fresh seeds. All policies use exactly the
  same development predictions. No donor-history measure, latent truth, external outcome
  or holdout evaluation enters selection.
- Candidate grids match the preceding experiment: initial plus steps 1–512 at the short
  budget; initial plus every fourth step through 2,048 at the long budget. Each has 513
  candidates. The union has 897 candidates per trajectory. Pools differ across budgets;
  this remains an unequal-compute comparison with equal distinct evidence.

## Three selection policies, fixed before outcomes

1. **Joint:** select the candidate with the lowest original combined development Brier error.
2. **Guarded choice:** first find the joint-selected candidate in the same pool. Among
   candidates whose development execution Brier is no more than **0.002 higher** than that
   candidate's, select the lowest development choice Brier. The joint candidate is always
   feasible. This guard is a development point-estimate rule; held-out noninferiority must
   still pass independently.
3. **Raw last:** take the raw model at the budget's final update, without development selection.

Exact ties go to the earliest step. Policies never feed back into evolution or gradients.
Every candidate vector, its development component scores, and the selections are saved.
All selections are written before any holdout generation or evaluation. Identical selected
vectors reuse cached evaluation predictions; this does not change any scientific comparison.

## Primary question and decision rule

The primary comparison is **guarded choice versus joint at 2,048 updates, evolutionary
optimization, interaction readout**, averaged equally over 4-, 12- and 24-event histories
in the canonical observed query context. Each cell uses 512 fresh evaluation lifetimes.
All five conditions must pass; this is one conjunction, with no substitution by a secondary result.

| Required outcome | Contrast | Required lower 95% bound |
|---|---|---:|
| Better choice forecasts | Joint choice error minus guarded choice error | > 0 |
| Stronger useful choice-history dependence | Guarded choice donor benefit minus joint choice donor benefit | > 0 |
| Useful choice learning retained | Guarded donor-history minus own-history choice error | > 0 |
| Useful execution learning retained | Guarded donor-history minus own-history execution error | > 0 |
| Execution noninferiority | Joint execution error minus guarded execution error | > -0.002 |

A donor intervention replaces the complete observed history with another target's history
within query-context and length strata, leaving the query and future outcomes unchanged.
It measures useful target-specific history dependence; it does not identify an abstract
IRV or separate internal mechanisms. Better choice forecasts and a larger history benefit
must both be demonstrated to meet the primary rule.

Inference uses eight whole-run paired differences, 10,000 bootstrap resamples, percentile
95% intervals and seed 248000000. The small number of independent runs limits precision.
Thresholds are strict. No optional stopping, seed replacement or outcome-driven reruns.

## Prespecified secondary analyses

- Choice and execution changes across budgets within each policy, including growth in
  donor-history benefit; raw stopping-point versus joint-selected models at both budgets.
- Fresh-seed replication of the earlier same-length exploratory result: raw-minus-joint
  **growth** in choice donor benefit from 512 to 2,048, at exactly 24 history events in the
  canonical observed context. This remains secondary and cannot rescue primary failure.
- Corresponding policy effects for the parameter-matched control and matched-gradient
  learner, plus observed-context, held-out-context, shifted-payoff and external-game results.
- Zero-memory interventions and selected checkpoint ages. External games are a previously
  inspected iterative-development benchmark, lack execution outcomes, and remain secondary.
- All component scores and contrasts are retained, including adverse effects. No multiplicity-
  adjusted confirmation claim is made for the collection of secondary intervals.

Fresh seeds are specified in `seeds_for`: initialization 241000000+s, training 242000000+s,
development 243000000+s, evolution 244000000+s, evaluation 246000000+1000s,
donors 249000000+1000s, and replay 250000000+s, for s=0..7. Evaluation adds fixed
suite/history offsets. The unused random-search/diagnostic fields preserve the inherited
seed dictionary interface; they do not launch additional procedures.

## Reproduction, integrity and publication

The workflow validates before launch and freezes this protocol, all executing source,
integrity tests, runtime versions, seed plan, external checksums and commit identifier.
Tests include exact tiny-run recovery of both predecessor training trajectories and joint
checkpoints, latent-truth exclusion, equal candidate counts, the execution guard, earliest
ties, short-budget isolation, fixed evidence replay and target-preserving donor interventions.

```bash
python -m pip install -r experiments/checkpoint-selection-v1/requirements.txt
python experiments/checkpoint-selection-v1/external.py upstream
python experiments/checkpoint-selection-v1/test_integrity.py
python experiments/checkpoint-selection-v1/experiment.py freeze --upstream upstream --out frozen
python frozen/experiment.py run --seed 0 --out runs/seed-0
# After all eight distinct seeds have completed:
python frozen/experiment.py aggregate --inputs runs --out final
```

The frozen predecessor is `219cacde3a7f1b4e6837ff30183836e9c543ba36`; the merged baseline is
`bacaf04e6522dd786962eb26d1e2f1e355624f79`. There are no model API calls. GitHub CPU compute
is used. A new launch requires the exact dedicated run-branch commit message in the workflow;
normal publication and merge commits do not launch training. Automatic study reruns are blocked.

Full results, selected parameters and candidate archives will be published under the user's
standing authorization in `experiments/PUBLICATION_AUTHORIZATION.md`. Source/protocol changes
after launch must be separated from the frozen study and explicitly documented.
