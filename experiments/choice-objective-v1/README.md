# Joint versus choice-only pressure, v1

Prospective, fixed-budget follow-up to [discovery-transfer-v1](../discovery-transfer-v1/README.md), whose evolutionary learners acquired useful execution updating but little useful social-choice updating. Freeze this protocol and source before study selection. Preserve the preceding result and every new replicate, favorable or unfavorable. No API calls.

## Question and interpretation

Does removing execution prediction from the training/selection objective produce useful target-specific preference learning, with architecture, observations, candidate budget and development checkpoint criterion held fixed?

The treatment is **joint versus choice-only fitness/training loss**. Both arms choose final checkpoints using the same development choice-prediction criterion. This avoids attributing an effect solely to judging the two arms' final models differently. It also means the new joint arm is not an exact rerun of the previous joint model, whose development criterion combined both tasks. Re-estimate both arms on new paired run seeds; do not reuse the old joint scores as a comparison group.

Three joint primary requirements for the evolved learner, evaluated in the canonical habitat mixture with a **previously observed query context**, at the final development-selected checkpoint, averaging equally across histories of 4,12,24 episodes:

1. Choice-only training gives lower observed future-choice Brier than joint training.
2. The choice-only learner gives lower choice Brier with its intact memory updates than with all memory held at zero.
3. The choice-only learner gives lower choice Brier with the target's own history than with another target's history.

For each requirement the paired whole-run bootstrap 95% interval must have a strictly positive lower bound (comparator minus treatment loss). All three are required to report joint success. Report effect sizes even when intervals exclude zero; these are pilot estimates, not a threshold of practical utility. The comparison with random search and gradient learners, a difference-in-donor-benefit between objectives, cross-context transfer, shifted payoffs, longer lifetimes and external games are secondary. Do not promote a favorable secondary result into the primary conclusion.

A positive result supports the narrower claim that the objective affected acquisition in this architecture/search budget. It does not prove gradient conflict, a particular internal valuation representation, separate physical modules, or successful simultaneous multi-domain learning. Dropping execution from the objective removes the demand to learn both problems; record execution performance as a tradeoff. A null leaves search budget, representation/readout and insufficient power open, rather than refuting evolvability in principle.

One concrete alternative remains: target memory must interact with option payoffs to change relative choice scores. In the linear limit of the shared readout, a common additive memory contribution cancels across options under softmax. The nonlinear readout can represent interactions, but they may be harder to acquire than direct state-dependent execution predictions. This study holds that readout fixed and does not test a new readout architecture.

## What remains identical

The copied `models.py`, `worlds.py`, `external.py` and `requirements.txt` are byte-identical to predecessor commit `edce7347c69beca326c0be2120b026caa57b9e61`; tests and the manifest record this. No cue masks, named memory states, hand-coded preference updates, new sensory features or new neural connections are introduced.

Targets have independent stationary shared social weight rho and execution probability a, each Uniform(0,1). Voluntary choices follow softmax of own payoff plus rho times recipient payoff, inverse temperature 1. Assigned episodes force action. Attempted executions succeed with probability a, with 20% missing outcomes explicitly marked. Histories occur in two of three public contexts. Development menus have two actions: do nothing or pay a cost to give a benefit. Three equally sampled habitats vary costs, benefits and assignment rates; their labels are not inputs. The predecessor protocol gives the exact ranges and feature definitions; the unchanged world source is authoritative.

All methods receive the same 15 event features, complete common query interface and two observed future targets. Training histories have lengths 0,4,12,24 sampled equally and are padded to 24. Future voluntary choice and guaranteed-attempt execution outcomes are actual independent Bernoulli/categorical draws, not latent-parameter or posterior targets. Choice-only fitness ignores the execution target, but receives exactly the same history—including informative or irrelevant execution observations—as the joint arm.

| Method | Architecture | Parameters | Persistent state |
|---|---|---:|---:|
| evolved | Four unnamed gated states, shared 8-unit query readout | 257 | 4 |
| random_search | Same small architecture | 257 | 4 |
| matched_gradient | Same small architecture | 257 | 4 |
| dense_gradient | Shared GRU and 16-unit query readout | 1969 | 16 |

Each small state can depend on every previous state and every event feature. All inherited update and readout weights are selected/trained. Within-lifetime memory resets for each new target; inherited weights remain frozen at evaluation. The shared readout scores each option and an execution query. The number of options may vary without truncation. The complete menu is summarized for history encoding, as in the preceding study; the supplied Bayesian reference sees full menus and knows a useful generative family, so it is a privileged reference rather than a matched-information competitor.

## Objective and common model selection

Let C be categorical choice Brier `0.5 * sum((p-onehot(y))^2)`, and A be execution Brier `(p-success)^2`.

| Arm | Training / population-selection loss | Development checkpoint loss |
|---|---|---|
| joint | .5(C+A) | .5C |
| choice_only | .5C | .5C |

Keeping the choice coefficient .5 in both arms holds its direct gradient contribution fixed; only the execution term is removed. A positive global scaling does not change evolutionary ranking. No learning-rate change accompanies the manipulation. The development loss is reported explicitly as half-choice Brier; evaluation reports ordinary choice Brier.

Both arms use 512 generations, 32 candidates per generation, 64 fresh lifetimes per generation, the same initialization distribution, the same paired random-number streams, and the same evolutionary algorithm. Thus each method sees 32,768 distinct training lifetimes; each search method scores 16,384 candidates / 1,048,576 candidate-lifetime combinations. The initial search distribution has mean zero except domain-independent gate bias −2, SD .5. Candidate zero is the current mean; the top eight receive normalized log-rank weights. Mean adaptation .3; SD adaptation .15, bounded [.05,2]. The original protocol/source specifies the exact update.

Evolution proposes its updated distribution mean for development scoring after every generation. Random search proposes the best candidate on that generation's training batch, using that arm's objective; the fixed random-draw distribution and total candidate budget are identical across arms. Both retain the best development candidate seen so far. The two arms therefore differ in candidate ranking and the resulting trajectory, not in the development judge. Search is not exhaustive development scoring of every random candidate.

Gradient learners receive the same batches and use 512 Adam updates, learning rate .003, norm cap 1, no weight decay. The matched learner shares the small initial candidate. Dense initialization is paired across arms. Both use the same 256-lifetime development set and .5C checkpoint criterion. Save checkpoints at 0,128,512, with no early stopping or outcome-based extension. Report the generation/update at which each final champion was selected. Also score the raw, unselected generation-512 evolved mean and final gradient weights on the canonical observed-context 24-episode cell as a secondary check.

Within a replicate, both objectives and all four methods receive identical training and development arrays/targets, confirmed by hashes. Evolution and random search use the same respective random streams across objectives; evolutionary candidate values diverge when fitness changes the trajectory. Objective order alternates across replicates; gradient-method order also alternates. Eight independent replicate seeds produce **64 procedures**. No methods receive external histories during selection. Every procedure in both arms finishes training before evaluation begins.

Exposure and within-method budgets are matched across objectives. Population search and gradient training have different computational costs; dense and small learners have different capacity. Do not claim equal-FLOP superiority.

## Acquisition, transfer and control histories

Each test cell contains 512 fresh targets. Test lengths are 4,12,24,48; 48 is secondary. The primary canonical observed-context view and secondary held-out-context view reuse exactly the same histories, query payoffs, underlying shared traits and realized future outcomes. Only the query's public context changes to the first history episode's context. This is valid because traits and choice probabilities are shared across contexts in this world. It tests source acquisition without requiring transfer to a never-observed context. Do not use this relabeling in a context-local generator.

| Suite | Role |
|---|---|
| canonical_seen | Primary acquisition: new targets, query in an observed context |
| canonical_heldout | Secondary cross-context transfer, paired with canonical_seen |
| shifted | Secondary new costs/benefits and assignment schedule, held-out context; unchanged predecessor suite |
| external_games | Secondary previously inspected independent generator and actors, new target/menu draws |

For each final model, score intact history, all-state-zero memory, and **donor history**. Donors are a random derangement of whole histories within query-context and length strata: no target receives its own history, and every history is used once. Donor observations, menus, actions, outcomes and lengths move together; query payoffs, query context, future outcomes and target truth remain attached to the original target. In the primary view the query context remains observed; in the held-out view it remains absent. Donors are not additionally matched on payoff habitat or exact event sequence. Target traits have the same independent prior across these habitats, and query menus are supplied in full to the readout, but the donor comparison is still a behavioral history-dependence control rather than a causal latent-variable intervention. The same donor permutation is used for all methods/objectives in a cell.

This control distinguishes useful target-specific information from generic effects of having any nonzero recurrent state. The zero-state control is also relevant: zero-length histories made up a quarter of training, so an empty state is within training support. Neither control identifies a particular abstract IRV or a minimal physical locus.

External implementation remains pinned to `maxkw/evolution` at `8d7f9946b3cc4ff1d7fae7a1a7a149499c35dede`, with checksum-verified unchanged generator and selfish/altruistic agent definitions. Two players, upstream `nactions=3,benefit=5,cost=1,tremble=.02`, inverse temperature 1, and equally likely actor types; every sampled action is retained. There are no execution outcomes, so external scores concern choice only. This is not the full Bayesian Reciprocator, adaptive strategic interaction or human data. The benchmark informed the current question through the previous result, so new random seeds do **not** make it an untouched confirmatory benchmark. Label these results secondary iterative development.

## Diagnostics and analysis

Retain the supplied 81-point shared-rho/Beta-execution reference, intact, no-memory and donor-history scores. It is a useful-rule reference, not a learned oracle. Latent choice/execution probabilities enter only secondary scoring. The loss functions and tests prohibit their use in training or checkpoint selection.

Repeat the prior evidence contrasts on 256 new eight-episode histories for both observed and held-out query contexts: voluntary failure versus refusal, voluntary success versus failure, assigned success versus failure, assigned failure versus unchanged, refusal versus unchanged. Report both output-channel magnitudes, informative-direction accuracy and irrelevant-channel shifts. A near-zero irrelevant-channel effect is not evidence of selective cue processing when relevant effects are also near zero. These remain descriptive behavioral diagnostics.

Use the entire paired selection/training run as the replication unit. Average equally across the three primary history lengths before forming within-run contrasts. Bootstrap eight complete runs, 10,000 resamples, seed 148000000. The three primary requirements form a conjunction; all must pass. No separate success declarations from the other methods or suites. Secondary estimates include donor-gain differences between objectives, execution losses, all method comparisons, selected checkpoint ages, raw-final scores and longer-lifetime results. Report all runs, not just champions across replicate seeds. Do not treat targets, options, checkpoints or generations as independent experimental replications.

Seed plan for replicate r: initialization 141000000+r; training 142000000+r; development 143000000+r; evolution 144000000+r; random search 145000000+r; evaluation 146000000+1000*r+100*suite_index+length, with both canonical views using suite index 0; diagnostics 147000000+r; donors 149000000+1000*r+100*suite_index+length. Integrity tests use 151000000-series inputs or offsets, not these study streams.

Freeze source, this protocol, copied-source hashes, runtime/dependency pins and upstream files before launch. Run deterministic one-thread CPU training once per seed, keep partial artifacts on failure and reject re-running the same Actions attempt. Preserve every final selected model as readable parameter arrays in addition to checkpoint artifacts, with its replicate and configuration hash. Save all per-run metrics, donor/data hashes and analysis. No original files or results are overwritten, no outcome-based budget increase, and no success-dependent rerun. Any later adjustment is a new version with an explicit reason.
