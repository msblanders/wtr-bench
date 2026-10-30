# Memory–payoff interactions under joint selection, v1

Prospective follow-up to [choice-objective-v1](../choice-objective-v1/README.md), frozen before any study training. That pilot found clearer preference acquisition after removing execution pressure, especially under gradient training, but execution prediction then deteriorated. This experiment retains both objectives and changes the readout. No API calls.

## Question and treatment

Can a supplied interaction operation make useful target-specific preference learning easier to acquire while preserving execution learning under joint selection?

Both architectures have the same four unnamed gated memory values and 269 inherited/trainable parameters. The shared recurrent core has 160 parameters; a common eight-unit tanh readout has 97. Each architecture adds 12 readout parameters:

| Readout | Additional operation | Additional parameters |
|---|---|---:|
| interaction | Bilinear products of each memory value with own payoff, recipient payoff and execution-query indicator | 4 × 3 = 12 |
| wide_control | Ninth ordinary tanh unit reading all four memory values and all six query features, with bias and output weight | 10 + 1 + 1 = 12 |

For memory h and query q, the treatment adds `h^T B q[3:6]` to the common eight-unit score. The control adds `v*tanh(u^T[h,q,1])`. Both score options with softmax and the execution query with sigmoid. Payoffs remain transformed by `asinh(payoff/4)` as in the predecessor. Context indicators are the first three query coordinates. The final query coordinate indicates execution; its payoffs are zero. On choice options the execution indicator is zero.

This is a comparison of a **readout package**: eight memory–payoff products plus four memory–execution-kind products, against one extra ordinary hidden unit. A positive result cannot attribute the effect uniquely to payoff multiplication rather than the execution-specific path or their combination. The control can learn interactions through its nonlinear hidden units. Neither architecture is given willingness/ability labels, cue-eligibility masks, a known utility coefficient, named memory banks, posterior updates or fixed evidence rules. Every recurrent weight and readout coefficient is selected/trained. The interaction operation itself is supplied by us; this experiment cannot show that evolution discovered multiplication or chose this architecture.

Parameter count, four-value memory, observations, scalar initialization distribution and training budgets are matched. Function-space initialization, FLOPs and inductive bias are not matched. The first 257 scalar coordinates have identical meanings in both architectures; the last 12 differ in meaning. Initial champions and candidate noise use identical numerical vectors across arms; this does not imply identical predictions. Record checkpoint-zero performance and final scores rather than hide this difference. Core updates are identical when recurrent weights are identical.

## Primary decision rule

Eight paired independent runs. The primary population is new targets from the canonical habitat mixture, queried in a context present in their history. Use final development-selected procedures and average equally over history lengths 4, 12 and 24. The primary method is evolutionary search.

All four criteria must pass for joint primary success:

1. `wide_control choice Brier − interaction choice Brier > 0`.
2. The interaction learner's own history beats another target's history on choice Brier.
3. The interaction learner's own history beats another target's history on execution Brier.
4. Execution noninferiority: `wide_control execution Brier − interaction execution Brier > −0.002`.

For each contrast, its paired whole-run bootstrap 95% lower bound must exceed the stated threshold. The absolute execution margin 0.002 is fixed before this run: roughly 1% of the approximately 0.20 execution Brier observed in preceding joint-objective pilots. It is a modest engineering tolerance, not a claim of exact equivalence or a theoretically derived constant. Report the raw execution difference and interval so readers can apply a different tolerance. Requiring a history benefit in both channels prevents a lower loss from being labeled simultaneous learning when only one channel uses target-specific evidence. A failure of any conjunct is a failed primary criterion, even if secondary results are favorable.

This is a small precision-limited pilot. No minimum meaningful choice improvement is imposed beyond reporting its magnitude. Do not equate a confidence-bound pass with broad practical utility, an IRV mechanism, or validation of evolutionary psychology generally.

## World, objective and methods

`worlds.py`, `external.py` and `requirements.txt` are byte-identical to the preceding study. The world specification and feature encoding remain unchanged. Targets have independent stationary Uniform(0,1) social-weight rho and execution probability a. Voluntary choices follow softmax of own payoff plus rho times recipient payoff, inverse temperature one. Assigned episodes force action. Executions have success probability a; 20% of attempted outcomes are missing and flagged. Training histories cover two of three public contexts. Three equally sampled habitats differ in menu costs, benefits and assignment rates; habitat identity is not an input.

All learners receive the same 15 observation features and six query features. Histories have lengths 0, 4, 12 or 24, equally likely during training. Future voluntary choice and guaranteed-attempt execution are observed outcome draws, not latent targets. Let C be categorical Brier `0.5*sum((p-onehot(y))^2)` and A be execution Brier `(p-y)^2`. **Every training, evolutionary-ranking and development-checkpoint decision uses `0.5*(C+A)` in both arms.** Latent truth is used only in labeled secondary evaluation. Compared with the preceding study, development selection is now joint; re-estimate both architectures with new seeds rather than compare their means to the old choice-selected models.

Each readout receives three optimization methods: evolved, independent random search, and matched gradient training on exactly that 269-parameter architecture. The larger dense architecture from the preceding study is omitted: the gradient control here asks whether each matched architecture can acquire the behavior, not whether a much larger model can. Total: 2 readouts × 3 methods × 8 runs = **48 procedures**.

Evolution uses 512 generations, 32 candidates, top eight log-rank weights, initial mean zero except gate bias −2, scalar SD .5, mean adaptation .3, SD adaptation .15, SD bounds [.05,2]. Candidate zero is the current mean. Each generation sees 64 fresh lifetimes; its updated mean is offered to development selection. Random search has the same candidate budget and a fixed original Gaussian distribution; the best training-batch candidate is offered to the same development judge. Both retain the best development candidate seen so far, including the initial random champion.

Gradient training uses Adam .003, gradient-norm cap 1, no weight decay, 512 updates and the same initial vector and batches as search. All methods use the same 256-lifetime development sample. Save development-selected checkpoints at 0, 128 and 512, and report their selected generation/update. Also save raw final means/gradient parameters and score them secondarily on the canonical observed-context 24-episode cell.

Each procedure sees 32,768 distinct training lifetimes. Each population search evaluates 16,384 candidates, or 1,048,576 candidate-lifetime combinations. Exposure is matched; gradients and population search do not have equal compute. Alternate readout order by replicate; use the same paired initialization, training, validation and noise streams. Verify training and validation hashes across all six procedures. Every procedure in both readouts completes training before test data generation. No early stopping, outcome-dependent extension or retuning.

## Evaluation and diagnostics

Each cell has 512 new targets, at lengths 4, 12, 24 and secondary length 48. Keep four suites:

- **canonical_seen:** primary acquisition, queried in the first history episode's context.
- **canonical_heldout:** secondary transfer; identical histories, menus, traits and future outcomes, but a previously absent query context. Relabeling is valid here because traits are context-shared.
- **shifted:** secondary unfamiliar payoff ranges and assignment rates, with an absent query context.
- **external_games:** secondary upstream `maxkw/evolution` generator and selfish/altruistic actors, pinned to commit `8d7f9946b3cc4ff1d7fae7a1a7a149499c35dede`; all sampled options retained. No execution outcomes. This already-inspected benchmark is iterative development, not an untouched confirmatory external test, full Bayesian Reciprocator interaction or human behavior.

At the final selected checkpoint, score intact history, zero memory, donor history, and the added 12-parameter branch disabled without retraining (`drop_extra`) for both readouts. The last ablation is secondary and may be off-distribution; it tests reliance on the supplied branch, not an abstract valuation representation. Zero-state histories appeared during training. Donors are complete-history derangements within query-context and length strata, with no fixed points and each history used once. All historical metadata move with the donor. Queries, target outcomes and latent scoring truth remain with the original target. All methods use the same donor mapping in a cell. Donors are not additionally matched on habitat; the target trait prior is identical across habitats. This is a useful-history test, not a mechanistic interchange intervention.

Retain the privileged supplied 81-point-rho/Beta-execution reference, which knows useful generative assumptions and sees full menus. It is not an equal-information competitor or an unrestricted oracle. Report future-observation Brier and secondary latent-probability error separately. Repeat five existing evidence contrasts on 256 eight-episode histories for both seen and absent query contexts: voluntary failure versus refusal, voluntary success versus failure, assigned success versus failure, assigned failure versus unchanged, refusal versus unchanged. Report both output channels and reference effect sizes; near-zero irrelevant effects do not demonstrate selectivity when relevant effects also vanish.

## Analysis, provenance and stopping

Replication unit: an entire paired selection/training run. Average the three primary lengths within run before forming contrasts; bootstrap eight whole runs with 10,000 resamples, seed 168000000. Report every run and all four primary bounds. Other methods, suites, joint Brier, zero-memory effects, difference in donor benefit between architectures, branch ablations, raw-final scores and behavioral diagnostics are secondary. No corrections make these exploratory contrasts confirmatory; do not select a favorable subset for the headline.

Replicate r seed streams: initialization 161000000+r, training 162000000+r, development 163000000+r, evolution 164000000+r, random search 165000000+r, evaluation 166000000+1000*r+100*suite_index+length (both canonical views use index zero), diagnostics 167000000+r, donors 169000000+1000*r+100*suite_index+length. Integrity tests use 171000000-series inputs/offsets, not study streams.

Freeze this protocol, source, configuration, pinned runtime and checksum-verified upstream files before launch. Deterministic one-thread CPU execution; eight first-attempt runs, with partial artifacts preserved on failure. No outcome-based repeat. Preserve readable final parameters, all metrics and source/data/donor hashes, plus checkpoint artifacts. Leave the pull request in draft and do not merge automatically. Subsequent changes require a new version and an explicit scientific reason.

A positive result supports acquisition under a helpful supplied readout bias in these tasks. It does not show selection over architecture primitives, spontaneous problem-specific learning machinery, generalization to unexamined ecologies or a single abstract causal valuation variable. A null can motivate inspection of search budget, parameterization and sampling precision; it does not establish that the desired organization is impossible.
