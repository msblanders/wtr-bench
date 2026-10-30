# Memory × ecology: when does tying update weights cost prediction accuracy?

Version: memory-ecology-v1.0. Prospective follow-up to neural-update-v1, whose shared contextual learner won the primary data-efficiency comparison with greater memory and active arithmetic. This follow-up is designed after seeing those results and uses fresh seeds. It is not an independent confirmation of an originally specified hypothesis.

## Question and scope

Does heterogeneous evidence create an additional cost of tying recurrent update weights, and is that cost greater when memory is small? This is a controlled resource follow-up, not a search for a task on which separate networks win. Preserve and report all conditions irrespective of direction.

The two architectures have identical recurrent state size, input format, readouts, gating, initialization behavior, data and optimizer-step budgets at each width. Untying weights increases the number of trainable parameters. We therefore isolate a tying constraint at fixed state and forward matrix arithmetic, not at equal parameter capacity. A shared contextual function can implement different effective rules; sharing parameters is not absence of functional specialization.

This is supervised meta-training of recurrent learning dynamics, not evolutionary selection or several domains of knowledge. It retains the previous two temporal problems so that the follow-up addresses a concrete limitation of the previous comparison. No API calls or credentials are used. No claim about human psychological modules or necessarily separate neural loci follows.

## Environments

Each lifetime contains a sequence of observed binary outcomes. Predict the next observed outcome after each prefix. Three separate training ecologies:

- Stable: a new rate theta ~ Uniform(0,1) per lifetime; observations IID Bernoulli(theta).
- Changing: an initial fair binary hidden state, switching between observations with probability .08; each observation equals the hidden state with probability .85.
- Mixed: exactly half of each training/evaluation batch comes from each family, shuffled in order. Family remains constant within a lifetime.

Homogeneous ecologies use the same stable/changing generators. There are no task labels, family tags, hidden states, rates, reliability or hazard inputs, oracle targets, or external routing hints. Each model sees one stream independently; no batch normalization or cross-lifetime state. The known ecology defines the evaluation reference, not an input supplied to the learner.

The exact Bayesian reference integrates unknown rates/states and, in the mixed ecology, the unknown family with prior .5. Homogeneous references use family priors 1 or 0. Independent latent-state enumeration verifies the reference on every binary prefix through length four in all three ecologies. The reference knows the generating distributions; models learn from observations alone. Its squared discrepancy measures expected excess Brier loss above the observable-history optimum, not a fair learn-from-scratch Bayesian baseline contest.

## Architectures and controlled resources

Two state banks, two scalar sigmoid readouts, and one softmax gate from their concatenated states. Both banks execute at every observation; the gate mixes outputs. Each recurrent bank receives the observation and a fixed two-element bank identity. Bank identity identifies an internal computational bank, is identical across lifetimes/ecologies, and does not identify the family.

Shared: the two banks execute the same GRU parameters. Separate: each executes its own copy. Both have two independently parameterized heads and the same gate. At initialization the separate GRUs are exact copies of the shared GRU, and heads/gate have exactly matching draws. Predictions therefore start equal within each pair. Training may differentiate the initially identical recurrent weights. There is no oracle routing or specialization supervision.

Widths per bank are fixed in advance at 2 and 12 (4 and 24 total state values). Width 12 recovers the previous separate model's state budget; width 2 deliberately constrains memory without setting it to a single scalar. No width is selected from outcomes.

| Branch width | State values, both | Matrix MACs/observation, both | Shared parameters | Separate parameters |
|---|---:|---:|---:|---:|
| 2 | 4 | 72 | 58 | 100 |
| 12 | 24 | 1152 | 688 | 1300 |

MAC counts are forward matrix products, excluding nonlinearities, elementwise operations and backward/optimizer work. Equal forward arithmetic is not identical elapsed time or total training FLOPs. Separate models require additional parameter/optimizer storage. The shared implementation batches banks, which can affect runtime. Record measured training time descriptively.

Homogeneous controls ask whether any benefit of untying is specific to a mixture rather than a general benefit of extra parameters. They do not remove every capacity/optimization explanation. Adam on tied gradients aggregates bank contributions; untied gradients are updated separately. This is part of the intervention and limits a pure representational interpretation.

## Training and holdout

Eight independent paired replicates × three ecologies × two widths × two architectures = 96 trained models. Replication unit is the complete 12-model training run, not observations or lifetimes.

For every model: 1,024 optimizer steps, batch 64, 32 next-observation targets per lifetime, Adam learning rate .003 with standard betas/epsilon and no weight decay, gradient norm clip 1.0. Thus 65,536 lifetimes and 2,097,152 prediction targets per model. No schedule, tuning, early stopping, retries for a poor score, or evaluation-selected checkpoint. CPU, one Torch thread, deterministic algorithms. Dependencies are pinned to NumPy 1.26.4 and PyTorch 2.5.1+cpu on Python 3.11.

Save checkpoint weights at steps 0, 64, 256, and 1024. Reset hidden states each lifetime; weights persist across lifetimes. Targets are actual observed next outcomes; binary cross entropy is the training loss.

For replicate r, ecology index e (stable=0, changing=1, mixed=2), branch width h:
- initialization: 81,000,000 + 1,000r + 100e + h;
- training: 82,000,000 + 1,000r + 100e;
- evaluation: 84,000,000 + 1,000r + 100e.

Within each ecology, both widths and both architectures see identical generated training streams and evaluation streams; hash assertions enforce matching. Across ecologies samples are independent. Condition order rotates by replicate; model order alternates. No study seeds overlap the preceding pilot.

All twelve models in a replicate complete training before its evaluation data are generated. Evaluation uses 1,024 new lifetimes with 64 prediction positions. First 32 positions are the main matched-length analysis; positions 33–64 are a secondary extrapolation test. Also report secondary symbol inversion on the same evaluation streams. No validation-set selection, expert assignment or routing search is performed in this follow-up.

## Primary estimand and decision rule

For each model, E is squared prediction error relative to the observable-history Bayesian reference, averaged across evaluation lifetimes and first 32 positions, then equally across trained checkpoints 64, 256, and 1024. This is an average at three prespecified data budgets, not an integral over time, a compute-normalized AUC or a final-convergence estimate.

Define P(e,h) = E(shared,e,h) − E(separate,e,h). Positive P favors separate weights.

Define D(h) = P(mixed,h) − [P(stable,h)+P(changing,h)]/2.

The single primary contrast is J = D(2) − D(12): does mixing problems penalize sharing more under limited memory?

Compute J inside each paired replicate, then its mean and a percentile paired bootstrap 95% interval using 10,000 draws of eight whole replicate indices (fixed RNG seed 85,100,000).

- Positive interval excluding zero: conditional evidence that memory scarcity amplifies the mixture-specific cost of tying in this setup. Also inspect the signs of P(mixed,2) and D(2); a positive J alone does not establish an absolute separate-model advantage.
- Interval including zero: this pilot does not resolve the proposed interaction. Do not substitute a favorable cell or checkpoint as the primary result.
- Negative interval excluding zero: evidence against the predicted direction in this setup.
- Independently report all cell means, paired differences and individual replicate contrasts. With eight replicates these are exploratory uncertainty estimates, not a definitive phase boundary.

Secondary: D at each width, all six P values, final checkpoint error, observed Brier loss, error by generating family, longer histories, inversion and runtime. Their intervals are descriptive and not multiplicity-corrected. Do not use them to rescue the primary hypothesis. No difference in predictive error by itself establishes independently specialized computational mechanisms.

## Integrity, execution and limitations

Freeze source, this protocol, dependencies, config hashes and seed plan before study training. The GitHub run uses only the frozen copy and validates hashes/dependency versions. Technical development tests use separate seeds and tiny training budgets. Those tests check reference correctness, causal inputs/state reset, matched initialization, the tying-gradient identity, resources, paired data and contrast arithmetic; no study accuracy threshold gates execution.

Launch once using the exact workflow commit message, with eight bounded jobs and no automatic rerun. Preserve partial artifacts on technical failure; document any correction before resuming. Retain all checkpoints, per-run metrics, hashes and reports. Do not change the protocol after observing study outcomes.

If the predicted pattern fails, report it as a boundary on this architecture argument. If it succeeds, the next study must separate parameter capacity/optimization from functional mechanisms and broaden the recurrent problems. This pilot alone does not establish novelty, an evolved portfolio of rules, or advantages across qualitatively different knowledge domains.
