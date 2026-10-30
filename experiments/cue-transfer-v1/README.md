# Cue-transfer-v1: learned social estimates under misleading context cues

Prospective version cue-transfer-v1.0, specified after the earlier neural-update and memory-ecology pilots. No study outcomes were available when this document was frozen.

## Question

Can theory-specified evidence routing improve learning efficiency and transfer when contextual cues change, compared with a full-history learner that discovers its own organization? Does the imposed pooling rule fail when willingness is truly context-specific?

The accompanying cue-spec.md defines the functional commitments and their limits. The equations retain the earlier functional-learning-v1 social world. This implementation vectorizes fresh single-partner lifetimes and changes exposure sampling; it is not the identical old event schedule or dataset. The study trains neural parameters from observed future behaviors, whereas earlier controlled-memory work supplied externally computed beliefs.

## Design

Eight independent paired replicates × two ecologies × three learners = 48 models. Each ecology has separately trained models; no ecology tag enters an input.

Shared ecology: one w and one a per new partner, independent Uniform(0,1).
Boundary ecology: independent w for each of three contexts, with one a shared across contexts.

For each lifetime, one context is selected uniformly to have no history. History episodes occur in the other two, with equal sampling probability. All three contexts appear across lifetimes, including as query contexts. Thus no embedding or receiving readout is withheld from training. Targets are fresh partners; partner identifiers and hidden parameters never enter inputs.

Canonical assignment probabilities by context are [.1, .9, .5]. Test suites:
- canonical: same schedule on fresh partners;
- reversed: [.9, .1, .5], the primary transfer test;
- assigned only: [1,1,1], a secondary forced-action stress test;
- voluntary only: [0,0,0], a secondary choice-only stress test.

Conditional behavior follows the cue specification. All five event types and all context/instruction combinations can occur during training. Rates and assignment are independent. The reference's posterior is unaffected by the assignment schedule because assignment contains no trait evidence under this generator.

## Learners and resources

History learner: one GRU with 16 hidden values reads the full six-field event stream: voluntary, attempt, success, and three context indicators. A two-layer readout sees its final state and the query context and predicts willingness/ability. It can learn local or pooled estimates, cue filtering, and interactions.

Functional learner: eligible observations are compacted into two ordered streams. One shared GRU (hidden width 8, binary observation plus fixed two-element bank identity) processes both streams, with independent state banks and scalar readouts. Bank identity identifies the prediction component, not the hidden ecology. The recurrent update rule and readout weights are learned from scratch. There is no hardcoded Beta update or monotonicity constraint. Predictions pool across contexts.

Wrong-rules learner: identical architecture/initialization to the functional learner, but every attempt flag updates its willingness stream and every delivery flag updates its ability stream. Assignment status and no-attempt versus failed-attempt information are discarded within those streams. It has no correct-routing shortcut. No required performance gap or zero-error gate is imposed.

All have 16 total persistent hidden values. History has 1506 parameters; functional and wrong-rules each have 330. The history rival is deliberately more generously parameterized. Matrix arithmetic per padded history position is approximately 1056 for history and 528 for the two filtered banks together. Readout matrix MACs for all three query contexts are 1008 and 16, respectively. Compacted streams are still computed to the padded length and gathered at the valid final position; we do not claim an implemented sparse-compute saving. Counts exclude nonlinearities, gathering, backward passes and optimizer operations. This is an inductive-bias comparison, not exact parameter/FLOP matching.

Critically, the functional architecture itself shares recurrent weights. A win would support the usefulness of specified cue handling, not the necessity of physically separate update networks.

## Training

Each model receives the same fresh histories, lengths and observed future targets within a regime/replicate, verified by a hash. Adam .003, default betas/epsilon, no weight decay, gradient norm clip 1; 1024 batches of 64 fresh partners. History length is independently sampled from {0,2,8,24}. Maximum padded length 24.

Each partner supplies independent future binary voluntary-choice and guaranteed-attempt success outcomes in all three query contexts: six observed targets, not latent trait or posterior labels. Training minimizes their mean binary cross entropy. This is 65,536 lifetimes and 393,216 future binary targets per model. History-state resets each lifetime; learned weights persist. No early stopping, tuning or checkpoint selection.

Save weights at updates 0,64,256,1024. Rotate method order and alternate regime order across replicates. PyTorch 2.5.1+cpu, NumPy 1.26.4, Python 3.11, one Torch thread, deterministic algorithms. No API use or secrets.

For replicate r and regime index e (shared=0, context_specific=1):
- initialization = 101000000 + 1000r + 100e;
- training = 102000000 + 1000r + 100e;
- evaluation = 104000000 + 1000r + 100e;
- matched-history diagnostics = 105000000 + 1000r + 100e.

Development tests use distinct seeds beginning at 111000000. No study seeds are used to tune or test implementations.

## Evaluation and primary estimand

All six models in a replicate finish training before evaluation data are generated. Each suite uses 1024 fresh partners with full 24-episode histories, evaluated at prefixes 2,8,24. Suites reuse random draws to pair underlying traits and contexts while changing assignment; history prefixes are also paired. The reference is the exact known-regime Beta posterior from the observable history. It knows the world's equations and sharing regime; it is a performance reference, not a learned rival.

Primary score E: squared prediction discrepancy from this reference, averaged over willingness and ability predictions in the never-observed context, 1024 partners, history prefixes {2,8,24}, and trained checkpoints {64,256,1024}, in the shared ecology under the reversed assignment schedule. This is expected excess Brier loss and a prespecified average over data budgets, not a continuous AUC.

Single primary contrast: E(history) − E(functional), positive favoring the functional cue bias. Compute within each complete replicate, then mean and percentile paired bootstrap 95% interval from 10,000 draws of eight whole replicate indices, RNG seed 106000000. Lifetimes, channels, prefixes and checkpoints are not independent replications.

- Positive interval excluding zero: conditional data-efficiency/transfer advantage for the supplied cue rules in this world.
- Interval spanning zero: unresolved advantage; report magnitude and uncertainty.
- Negative interval excluding zero: evidence favoring the full-history learner on this outcome.

A positive result is expected to some extent because the world and functional bias agree. It is not itself a discovery of the correct theory. Report the gap size, the final-checkpoint gap and all boundary/stress conditions. Eight runs yield exploratory uncertainty, not a broad architecture ranking.

## Secondary measures and diagnostics

Prespecified secondary outcomes: all canonical and stress-suite curve means; the same reversed-schedule comparison in the context-specific ecology; their interaction; wrong-rules comparisons; final-checkpoint comparisons; channel-specific and observed-context error; latent-parameter MSE; and voluntary-delivery probability error using identical product readouts.

Data-to-criterion is the earliest tested checkpoint among 64,256,1024 with reversed-schedule transfer error (averaged across prefixes/channels) <= .002. If none qualifies it is right-censored; do not substitute 1024 or interpolate.

Final models undergo matched-history tests on 512 new partners. Append a specified episode in an observed context and query the unseen context:
1. voluntary failure versus refusal;
2. voluntary success versus voluntary failure;
3. assigned success versus assigned failure;
4. assigned failure versus unchanged history;
5. refusal versus unchanged history.

Report predicted versus reference changes, direction accuracy where the reference change is nonzero, and absolute change in channels whose reference update is zero. No directional threshold is used as an execution gate. The imposed masks guarantee some invariances in the functional learner; that is not independently discovered mechanism evidence. Also swap the first two context labels in history and query, reporting prediction changes.

No secondary test replaces the primary result. Secondary intervals are descriptive and not corrected for multiplicity.

## Execution, safeguards and interpretation

Freeze this protocol, cue specification, source, dependencies, config hashes and seeds before study training. A single exact-message launch starts eight bounded jobs; reruns do not automatically launch. Preserve partial results on technical failures. Do not alter the protocol based on study outcomes.

Development checks verify the vectorized oracle against the earlier independent scalar estimator, eligibility masks, padding/future-event causality, context coverage and holdout identities, matched data/targets, actual learned-weight changes, matched wrong-rule parameters and contrast arithmetic. Tests do not require models to achieve the hypothesis.

Report every run, diagnostics and learning curves. A wrong-rules failure demonstrates a cost of lossy cue handling; it does not validate every aspect of the functional account. A boundary failure demonstrates the cost of imposing the wrong pooling assumption. The full-history learner might itself discover functional differentiation; predictive accuracy alone cannot identify its mechanism. This experiment does not establish evolved learning rules, WTR identification or broad knowledge-domain performance.
