# Fixed-evidence optimization budget, v1

Prospective follow-up to [memory-payoff-v1](../memory-payoff-v1/README.md). That experiment found a small useful choice-history effect under evolutionary selection with the interaction readout, but no choice-accuracy advantage over a parameter-matched control. Matched gradient training used the readout more effectively. This study asks whether additional optimization, with the amount of evidence and development-selection opportunities held fixed, improves evolutionary acquisition. Freeze before any study training; no API calls.

## Treatment and controls

Compare **512 versus 2,048 optimization steps** on exactly the same bank of 32,768 observed training lifetimes. Keep both 269-parameter readouts, the four-state memory core, both objectives, population size and optimizer settings unchanged. Re-estimate both budgets on new seeds; do not reuse a favorable previous model.

Each of eight independent runs trains six trajectories: two readouts × evolved, random-search and matched-gradient procedures. Each trajectory supplies its 512-step and 2,048-step model. Thus there are **48 training trajectories and 96 budget-selected models**, with eight independent paired replications. Budgets, readouts, test targets and checkpoints within a run are not additional independent replications.

| Property | Short budget | Long budget |
|---|---:|---:|
| Optimization steps | 512 | 2,048 |
| Distinct training lifetimes | 32,768 | 32,768 |
| Presentations of lifetimes | 32,768 | 131,072 |
| Complete passes over the bank | 1 | 4 |
| Population candidates scored | 16,384 | 65,536 |
| Candidate-lifetime combinations | 1,048,576 | 4,194,304 |
| Gradient updates (gradient control) | 512 | 2,048 |
| Development candidate opportunities | 512 + initial | 512 + initial |

Generate 512 batches of 64 lifetimes once. The first pass uses generation order; each later pass uses an independently seeded permutation of all 512 batch indices. Every observation, missingness flag, menu, future choice and execution outcome is reused exactly; do not redraw future labels. Use the same batch order across all readouts/methods. Memory resets for every lifetime evaluation; replay does not lengthen an individual's history or persist its state across passes. Only inherited/trainable weights continue adapting.

The bank stays fixed while test targets are freshly generated from independent streams. Extra steps may overfit the bank; held-out outcomes decide whether they help. This tests more optimization of fixed evidence, not more data, longer histories or an unlimited evolutionary search.

## Equal development selection opportunities

The short-budget champion is selected among steps 1–512. The long-budget champion is selected among steps 4, 8, 12, …, 2,048. Both include the same initial random model and use the same 256-lifetime development set and joint Brier criterion. Each therefore has 513 candidate opportunities. When a step belongs to both grids, compute the same candidate's development score once and share it; the full trajectory needs 897 distinct development scores per method. Validation never changes the population mean, its SD, gradient updates or training-batch order; it only retains champions.

The long-budget candidate pool is not a superset of the short one. This is intentional: its budget changes how far optimization progresses while keeping the number of development choices fixed. It means the comparison is not “the best checkpoint among every one of 2,048 steps.” Save selected checkpoint ages and raw unselected parameters at steps 512 and 2,048. Their observed-context 24-episode scores are secondary checks on development selection.

The short training prefix is exactly the first 512 steps of the long trajectory. An integrity test compares it to a separately stopped short run and requires bit-identical selected parameters. Hash the unique bank, each ordered training prefix, full training stream, development set and replay schedule.

## Primary decision rule

Primary method/readout: **evolution with the interaction readout**. Primary population: new targets from the canonical habitat mixture, queried in a previously observed context. Average equally across history lengths 4, 12 and 24 before forming within-run contrasts.

All five requirements must pass:

1. Choice Brier at 512 minus choice Brier at 2,048 is positive.
2. Choice donor-history benefit at 2,048 minus that benefit at 512 is positive.
3. The 2,048-step model's own history beats donor history on choice Brier.
4. The 2,048-step model's own history beats donor history on execution Brier.
5. Execution noninferiority: execution Brier at 512 minus execution Brier at 2,048 exceeds −0.002.

Each paired whole-run bootstrap 95% lower bound must exceed the stated threshold. Requirement 2 asks whether useful target-specific updating grew, rather than whether longer optimization merely improved a history-independent prediction. Requirements 3–4 ensure that both channels use informative history. The absolute 0.002 execution tolerance is inherited unchanged from the preceding protocol. Report the raw difference and interval; this tolerance is an engineering margin, not exact equivalence or a theoretical constant. If any conjunct fails, the joint primary result fails. There is no outcome-dependent extension beyond 2,048.

The preceding architecture-superiority criterion is retained, unchanged in meaning, as a **secondary check at each budget**: interaction beats wide control on choice, has positive donor benefits in both channels, and is execution-noninferior to wide control within 0.002. The new primary question concerns the effect of budget, not architecture superiority. Report both questions and do not describe a positive budget effect as a replication of architecture superiority.

## What remains unchanged

`models.py`, `worlds.py`, `external.py` and `requirements.txt` are byte-identical to predecessor commit `4aa0e4dc6a62b87805dce673028d2ffbb6968556`. The interaction readout adds 12 bilinear coefficients for four unnamed memory values × own payoff, recipient payoff and execution-query kind. The control adds a ninth ordinary tanh unit, also 12 parameters. Both share 160 recurrent and 97 base-readout parameters, for 269 total. This remains a readout-package comparison; it does not isolate payoff multiplication alone. Scalar initialization draws are paired; function-space initialization and FLOPs are not identical.

The generator retains independent stationary Uniform(0,1) social-weight rho and execution probability a. Voluntary choices follow softmax of own payoff plus rho times recipient payoff; assignments force action; attempted executions have probability a and 20% missing observations. Three habitats vary costs, benefits and assignment rates. Training histories have lengths 0, 4, 12 and 24, equally likely, in two of three public contexts. All learners receive the same 15 event features and six query features. Latent truth never enters training or development fitness.

Let C be categorical Brier `0.5*sum((p-onehot(y))^2)` and A be execution Brier `(p-y)^2`. All training, evolutionary ranking and development selection use **`0.5*(C+A)`**. Neither objective is removed or reweighted.

Evolution keeps population 32, top eight log-rank weights, initial mean zero except gate bias −2, SD .5, mean adaptation .3, SD adaptation .15 and SD bounds [.05,2]. Candidate zero is the mean. After each update, the new mean is eligible for development scoring according to the corresponding budget's grid. The random control keeps the original Gaussian distribution and offers the best candidate on the current training batch to that same grid. It receives the same candidate budget, but no adaptation of the proposal distribution. Gradient control uses Adam .003, gradient-norm cap 1, no weight decay and the same initial scalar vector. Learning rate and mutation schedule do not change when replay begins.

The long budget keeps the previous optimizer hyperparameters for longer. This is a budget comparison at a fixed optimization scheme, not a search over better optimizers. Training exposure and parameters are matched across readouts within each method; population search and gradient descent are not equal-FLOP competitors.

## Evaluation and secondary analyses

Every trajectory completes training before any evaluation data are generated. Use 512 targets per suite/length, lengths 4, 12, 24 and secondary 48, and exactly the same held-out data and donor mappings across budgets/readouts/methods.

- **canonical_seen:** primary acquisition with an observed query context.
- **canonical_heldout:** same histories, menus, traits and outcomes with an absent query context; a valid relabeling because traits are shared here.
- **shifted:** unfamiliar payoff ranges and assignment rates with an absent query context. Preserve the previous adverse-transfer finding as an explicit comparison, not a discarded benchmark.
- **external_games:** the same pinned independent upstream game generator and selfish/altruistic actors; this benchmark was previously inspected and remains secondary iterative development. It has no execution outcomes.

Score each budget-selected model with intact history, zero memory, donor history and its additional readout branch disabled without retraining. Donors are complete-history derangements within query-context and length strata. No fixed points; each history used once. Historical metadata move with the donor; query, target and future outcomes remain fixed. There is no additional habitat matching; trait priors are identical across habitats. These controls measure useful history dependence, not an abstract valuation-variable intervention. Branch ablation can be off-distribution.

Keep the supplied full-menu 81-point-rho/Beta-execution reference as a privileged useful-rule benchmark, not a matched-information oracle. Report secondary latent-truth errors separately from future-observation Brier. Retain all five behavioral evidence contrasts at both budgets in observed and absent query contexts: voluntary failure versus refusal, voluntary success versus failure, assigned success versus failure, assigned failure versus unchanged, refusal versus unchanged. Small irrelevant effects do not establish selectivity when relevant effects are also small.

Report budget effects for both readouts and all optimizers, changes in donor-history benefit, architecture advantages at each budget and their difference, raw-final outcomes, checkpoint ages, initial predictions, longer histories, shifted payoffs and external games. All except the five declared primary requirements are secondary; do not elevate a favorable subset to the headline.

## Analysis, provenance and stopping

Bootstrap eight complete paired runs, 10,000 resamples, seed 188000000. Keep all runs, including adverse results. A target, generation, budget or optimizer within a run is not an independent replication. This is a small precision-limited pilot, with effect sizes and bounds reported rather than a broad utility claim from a binary pass/fail.

Seed streams for replicate r: initialization 181000000+r; bank 182000000+r; development 183000000+r; evolution 184000000+r; random search 185000000+r; evaluation 186000000+1000*r+100*suite_index+length (both canonical views use index zero); diagnostics 187000000+r; donors 189000000+1000*r+100*suite_index+length; replay order 190000000+r. Integrity tests use 191000000-series inputs or offsets, never study streams.

Freeze this protocol, source, configuration, runtime/dependency pins and checksum-verified upstream files before training. Deterministic one-thread CPU; eight first-attempt jobs; preserve partial artifacts on failure. Save selected model parameters at both budgets, full checkpoint files, every per-run metric, paired data hashes and analysis. Standing publication scope is recorded in [PUBLICATION_AUTHORIZATION.md](../PUBLICATION_AUTHORIZATION.md). Keep the pull request in draft; do not merge automatically. Any scientific change after seeing outcomes belongs in a new version.

A positive result would support additional optimization of fixed evidence as one way to strengthen acquisition in this supplied representation. It would not show that selection discovered the interaction operation, a functional decomposition, a single abstract IRV or a general multi-domain learning architecture. A null leaves limitations of this optimizer, representation, finite bank and statistical precision open; it does not establish impossibility.
