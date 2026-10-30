# Learned shared versus differentiated recurrent updates

Prospective exploratory protocol, 29 October 2026. This follows the finite rule-selection experiment. It tests learned recurrent state updates across two temporal inference problems; it is not another selection run and does not establish the superiority of evolution.

## Question

Does permitting two independently trained update networks improve data efficiency over an expressive shared update network when the same agent must infer both stable probabilities and changing hidden states? All networks are trained from random weights on identical mixed streams. No model receives problem-family labels or hand-written update rules.

Stable-rate inference abstracts the earlier willingness/ability counting task. Hidden-state tracking adds a different computation requiring recency-sensitive nonlinear inference. This is a new minimal stream generator, not an unchanged replication of the social generator, and still not a broad benchmark of domains of knowledge.

## Generative problems and information access

Each lifetime contains binary observations. With probability one half, observations are independent Bernoulli draws from a new probability drawn uniformly on [0,1]. Otherwise, a binary latent state begins uniformly at 0 or 1, switches with hazard 0.08 between observations, and emits its state correctly with probability 0.85. All models receive only the observed binary stream, serialized identically. They predict the next observation after each input. Neither family labels, latent probabilities/states, hazard values, observation reliability, oracle predictions nor evaluation labels enter model inputs or training targets.

Training uses observed next outcomes and ordinary binary cross entropy. Both problems occur equally often in each training batch, in random order. Hidden state resets between lifetimes; learned weights persist across lifetimes. Thus outer training learns a recurrent within-lifetime update procedure. No within-lifetime gradient steps occur.

A Bayesian mixture over the two specified generators provides an evaluation reference using only the observed prefix and the known generative prior, not the true family or state. Its static component updates a Beta(1,1) posterior; its dynamic component filters the hidden Markov state; posterior family weights update through their marginal likelihoods. A short-sequence exhaustive enumeration test verifies this reference. The reference is not a trainable comparison model.

## Models

- Dense: one GRU with 18 hidden units and one sigmoid output; 1,153 trainable parameters, 18 state values.
- Routed updates: two GRUs with 12 hidden units each, separate sigmoid readouts, and a learned linear softmax gate reading both states; 1,156 parameters, 24 state values. Both branches execute on every observation. No sparse-compute benefit is assumed.
- Shared contextual update: one GRU with 17 hidden units, applied to two independent state banks. An internal two-valued bank indicator accompanies the same observation to each bank; it is not a problem-family label. The readout is shared, and a learned linear gate reads both states. This has 1,210 parameters and 34 state values.

The primary comparison is routed versus shared contextual update. The shared alternative has about 4.7% more parameters, more state, and more recurrent arithmetic, so it has ample opportunity to learn context-sensitive updates. Dense is a secondary approximately parameter-matched baseline. Data streams, update counts, optimizer and sequence lengths match; actual compute does not match exactly. Report parameters, state size, approximate forward matrix multiply-accumulate counts and measured training time. MAC counts omit nonlinearities, elementwise operations and backpropagation; do not label them total FLOPs.

This is a comparison of learned recurrent update functions. Unequal network weights alone do not demonstrate different mathematical learning-rule families or physically necessary modules.

## Frozen training and evaluation plan

Eight independent paired training seeds. Each model receives the same 1,024 batches of 64 new lifetimes with 32 prediction positions each: 65,536 lifetimes, 2,097,152 supervised prediction positions. Save checkpoints at 0, 64, 256 and 1,024 weight updates. Adam learning rate 0.003, default betas/epsilon, no weight decay, gradient norm clipping at 1.0. No schedule, early stopping, validation-selected checkpoint, model-specific hyperparameter tuning or accuracy gate. CPU, one compute thread, deterministic PyTorch algorithms. Rotate model training order across replicas. Record matching hashes of all training streams.

All models and checkpoints in a replicate finish training before its evaluation data are generated. One disjoint validation stream of 512 lifetimes can label the two experts for descriptive selectivity analysis after training; it cannot choose models, weights, training duration or hyperparameters. A separate evaluation stream of 1,024 lifetimes supplies 64 prediction positions. The first 32 positions are the main in-distribution evaluation; positions 33–64 test longer histories. Also test binary-symbol inversion on the same held-out sequences. Development tests use separate seed ranges and short unscored training runs.

Primary endpoint: mean squared deviation from the exact Bayesian mixture prediction, averaged over the 32 main evaluation positions and equally across training checkpoints 64, 256 and 1,024. Under the specified distribution this deviation is expected excess Brier loss over the optimal observable-history predictor. This is a fixed-checkpoint data-efficiency summary, not a claimed FLOPs-to-criterion estimate. Positive shared-minus-routed differences favor independently parameterized updates. Analyze eight paired complete training runs with a paired bootstrap 95% interval. Sequences and time steps are not independent replications. A small pilot interval is not a broad confirmatory result.

Secondary: final-checkpoint performance by true generating family, observed-outcome Brier loss, learning curves over both training and lifetime exposure, longer-history error, symbol-inversion error, dense comparison, and uniform-gate/forced-expert interventions. Report all outcomes including failures. No empirical ranking affects completion.

## Interpretation of routing and interventions

A gate that distinguishes generating families is descriptive evidence only. After training, choose an expert-to-family labeling on the validation stream, then report held-out forced-expert errors and gate weights. A full branch permutation, including its readout and gate columns, must preserve predictions; test this symmetry. Forced gates can reveal dependencies but may disrupt complementary representations, so they do not by themselves establish separate family-specific algorithms. There is no IRV inference here.

A routed advantage would support this finite-budget architecture under this ecology, subject to resource differences. A tie or shared advantage would challenge a claim that independently parameterized updates are needed for these problems. Failure by both to approach the Bayesian reference shows a limitation of this training setup, not a biological necessity. The comparison does not resolve broad multi-domain learning or select the best optimizer. No hyperparameters will be changed after inspecting these evaluation worlds.

## Provenance, runtime and budget

Source, protocol, dependencies, seeds and configuration are frozen before the experiment. Per-run training hashes, checkpoint weights, metrics, versions and timings are saved as GitHub Actions artifacts. Main experiment seeds are disjoint from development seeds and earlier studies. Jobs run on CPU with at most four training replicas concurrently and bounded timeouts; no API calls or credits. A new run or a changed protocol requires a new named output, preserving this run.

Implementation references: [PyTorch version installation](https://pytorch.org/get-started/previous-versions/) and [GRU definition](https://docs.pytorch.org/docs/main/generated/torch.nn.modules.rnn.GRU.html). The pinned dependency is PyTorch 2.5.1 CPU; the version is chosen for reproducibility, not claimed to be latest.

Commands after installing requirements:
    python -m unittest discover -s tests -p test_neural_update.py -v
    python experiments/neural-update-v1/experiment.py freeze --out frozen
    python frozen/experiment.py run --out runs/seed-0 --seed 0
    python frozen/experiment.py aggregate --inputs collected --out final
