# Selection of evidence-routing and transfer rules

Prospective exploratory protocol, 29 October 2026. This is the next small experiment after the controlled-memory pilot, not the full multi-domain EFLA study.

## Question and scope

Can mutation and selection discover which observations should update willingness and ability, and when each estimate should generalize across settings? Does allowing different transfer rules help specifically when the two quantities have different environmental structures?

This experiment evolves executable update programs. Individuals learn target-specific rates during their lifetimes; their descendants inherit programs, not those learned rates. There is no language model or API call. The search space, event representation, two estimates, Beta counting machinery, and query meanings are supplied by the experimenter. Selection can discover evidence gating and transfer within that space, not invent arbitrary learning algorithms or discover the number of modules. This is one social domain with two estimation problems, not a test across multiple domains of knowledge.

## World and observations

Extend the existing unable-versus-unwilling world in `functional-learning-v1/experiment.py`. Preserve its partner/context randomization, willingness parameters and first 24 exposure choices. Add independently variable execution rates across settings and extend the same assignment/context schedule to 96 exposures per partner. Execution outcomes are regenerated with a separate seeded stream in every condition, including shared-ability conditions. This is a documented extension, not a claim that outcomes are identical to the earlier pilot.

Four equally weighted ecological conditions cross willingness shared/local with ability shared/local. Each world contains four new partners and three settings; two settings supply observations and the third is held out. The agent sees assignment, attempt, outcome, partner and setting. It never receives the ecology label, seed, true probability, test answers or scoring result during its lifetime. Entity/context labels have no rule-specific meaning. Queries identify the quantity to predict: routing between hidden task families is not tested.

The common event representation has five mutually exclusive categories: voluntary decline, voluntary failed attempt, voluntary successful attempt, assigned failed attempt, assigned successful attempt. A decline supplies no execution outcome. The parser and counting representation are identical in every condition.

## Heritable programs and selection

Each of two prediction channels has five ternary instructions: ignore an event, count it as positive evidence, or count it as negative evidence. A sixth gene selects pooling across settings or counting within the queried setting. All estimates start with Beta(1,1) pseudocounts. Thus there are 486 possible programs per channel and 236,196 two-channel genotypes. A pooled program's evidence includes both observed settings; an unobserved local setting remains at 0.5. No theory-correct program is inserted into the initial population.

Compare:

1. **Evolved flexible transfer:** two independently selectable pooling bits and ten event instructions.
2. **Evolved tied transfer:** ten independently selectable event instructions, but one pooling bit shared between channels. The two channels still have separate states and can learn different evidence routing. This isolates differentiated transfer; it is not an intentionally crippled one-estimate alternative.
3. **Random search:** flexible programs with the same 2,560 candidate evaluations as evolution.
4. **Fixed functional pooling:** the original supplied correct evidence gates, pooling both quantities.
5. **Adaptive Bayesian pooling:** supplied correct evidence gates; separately infer shared versus local structure for each channel, with equal prior hypothesis weights and Beta(1,1) rates. All observed partners inform each channel's world-level sharing posterior. This is a strong structured baseline, not a generic neural learner.
6. **Regime-informed reference:** supplied correct gates and the true sharing structure; an informative benchmark, not a guarantee of the best realized finite-sample score.

Evolution uses population 64, 40 scored generations (2,560 candidate evaluations), four elites, tournament selection of size three, uniform crossover, and mutation probability 1/12 per independent gene. The tied condition has eleven independent genes; its copied pooling bit is not a separate mutable parameter. All founders are uniformly random. Candidates minimize mean squared probability error on 64 selection worlds, averaged equally across exposure checkpoints 2, 8 and 24 and both query types. This is expected Brier loss minus its candidate-independent irreducible term. The simulator uses latent rates to evaluate fitness exactly; no latent rates enter an individual's updates. It is evolutionary optimization of predictive fitness, not a strategic game or a claim about ancestral fitness.

The candidate class factorizes across channels. Cache the 486 single-channel program losses on the selection worlds; all searches see only the fitness of candidates they query. Report this precomputation explicitly. After search, compute the exact best selection-set score in each candidate class as an optimization diagnostic. This finite-class check makes it possible to distinguish a weak search from a weak rule class. Do not present the speed gained by caching as a biological or neural compute advantage.

## Evaluation and identification controls

Eight independent paired selection runs in each of four ecologies (32 run/ecology combinations). Each run has 64 selection worlds and 256 different evaluation worlds; all methods within a run receive the same data. Selection/evaluation world seeds are fixed in the manifest, disjoint, and not reused from the API pilot. Freeze the selected genotype before generating evaluation data. No holdout score selects generations, hyperparameters, seeds or reruns.

Primary exploratory contrast: tied-transfer minus flexible-transfer evaluation MSE, averaging exposure checkpoints 2, 8 and 24. Compare this advantage between heterogeneous ecologies (only one quantity shared) and homogeneous ecologies (both shared or both local). Eight complete paired evolution runs are the replication unit. Report run-level means and paired bootstrap 95% intervals; the many within-run queries are not independent replications. Report all seeds and failures. No accuracy gate blocks completion.

Secondary outcomes: learning curves at 0, 2, 8, 24 and 96 observations per partner; held-out-setting error; selection versus random search; exact program recovery; evolutionary optimization gap; selected-program performance in the opposite ecology; swapping only the two transfer bits; swapping complete channel programs. A full-program swap confounds evidence routing and transfer, so the pooling-only swap is the cleaner diagnostic of differentiated transfer. Neither intervention establishes a physically localized module.

A single shared contextual interpreter can execute exactly the same two selected programs by conditioning on the queried quantity. Verify this equivalence numerically and report it. Therefore even a successful result cannot establish that separate physical learning mechanisms are necessary, or that different mathematical learning-rule families evolved. This experiment tests selected evidence gates and transfer structure within one fixed counting algorithm. The flexible class has one extra independent bit; any advantage is conditional on this specified representational difference, not a parameter-matched architecture result.

## Compute, preservation, and next decision

Selection budgets are matched in candidate evaluations and lifetime observations. Both evolved conditions use the same counting state and prediction kernel. Record wall time, candidate evaluations, cached rule evaluations and unique genotypes; no FLOP-equivalence claim. Data generation, caching, optimization and evaluation costs are all included in elapsed time. No maintenance penalty or asymmetric error cost is introduced, so unused flexibility is not expected to disappear in homogeneous ecologies. Such disappearance would require a separately motivated cost or constrained developmental budget.

Freeze source, imported world generator, protocol, dependency version, configuration and seed plan before running. Save each completed run immediately, including all selected programs and generation traces. An exclusive ledger prevents accidental duplicate launches. This local pilot uses zero API credit. Results remain exploratory; do not tune and rerun on its evaluation seeds.

The next decision is whether differentiated transfer produces the predicted held-out ecological interaction and whether evolution reliably discovers it relative to random search. A positive result motivates extending the ecology to different computations and comparing an expressive shared contextual learner. A null or failure motivates diagnosing the specified search space before extending it. Neither outcome alone proves evolutionary necessity or novelty.

```bash
python -m pip install -r experiments/rule-selection-v1/requirements.txt
python -m unittest discover -s tests -p test_rule_selection.py -v
python experiments/rule-selection-v1/experiment.py freeze --out runs/rule-selection-v1
python runs/rule-selection-v1/experiment.py run --out runs/rule-selection-v1
python runs/rule-selection-v1/experiment.py report --out runs/rule-selection-v1
```
