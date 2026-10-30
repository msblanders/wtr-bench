# Provisional functional specification: willingness, ability and evidence

This specification implements the assumptions already used in the unable-versus-unwilling program. It is an explicit modeling commitment for this test, not a claim that the author has supplied a complete evolutionary theory of social valuation.

## Variables and operating assumptions

For a target partner, w is the probability of voluntarily choosing an attempt, and a is the probability of successful execution conditional on an attempt. Costs, benefits, recipient, knowledge of the request and available alternatives are held fixed. Each parameter has an independent Uniform(0,1) prior across new partners.

These are willingness and ability propensities in a synthetic world. A willingness probability is not itself a welfare-tradeoff ratio or an identified internal regulatory variable. The present study does not identify human anger, valuation or an LLM's internal scalar representation.

On a voluntary episode, attempt ~ Bernoulli(w). On an assigned episode, attempt is guaranteed regardless of w. If an attempt occurs, success ~ Bernoulli(a). A refusal has no execution outcome. The assignment mechanism and contextual sampling are independent of w and a. All cues are observed without measurement error; no lying, hidden coercion, cost variation or uncertainty about whether an attempt was voluntary is modeled.

| Observed evidence | Willingness estimate | Ability estimate | Reason |
|---|---|---|---|
| Voluntary attempt, success | Positive evidence | Positive evidence | A choice and a successful execution were observed |
| Voluntary attempt, failure | Positive evidence | Negative evidence | Choosing to try is distinct from being able to succeed |
| Voluntary refusal | Negative evidence | No direct update | No execution occurred |
| Assigned attempt, success | No direct update | Positive evidence | Execution reveals ability; compulsory action reveals no choice |
| Assigned attempt, failure | No direct update | Negative evidence | The assignment bypassed voluntary choice |

“No update” is exact under these stated independent-prior and generating assumptions. It is not a universal claim that observing assigned action can never inform willingness in richer worlds with correlated traits, strategic effort or uncertain assignment.

## Updating and downstream predictions

The functional learner uses two persistent state banks within each partner's history. Only voluntary choices enter the willingness bank, as binary attempted/declined observations. Only actual attempts enter the ability bank, as binary success/failure observations. Both banks use one shared recurrent update network, with a fixed bank identity, and separate scalar readouts. The numerical update function is learned from future observed behavior; Beta counts and posterior probabilities are not supplied as inputs or training targets.

Predictions are voluntary participation (w), execution when an attempt is guaranteed (a), and, as a secondary derived prediction, voluntary successful delivery (w times a). Product composition is applied identically to every learner; this does not test discovery of that algebraic rule.

In the shared ecology, evidence in one context should affect the corresponding prediction in another context for the same partner. In the boundary ecology, willingness is independently drawn for each context, whereas ability remains shared. Then evidence from another context should not update willingness in a never-observed context. The fixed functional pooling assumption is wrong in that boundary ecology.

## Misleading cues and predicted errors

Context labels predict whether episodes are usually assigned or voluntary during training. That correlation is reversed at test. Context alone does not change willingness or ability in the shared ecology. Every context/instruction combination has nonzero training support; the test changes their frequency rather than introducing an unseen symbol.

A learner treating all attempts as willingness evidence should overgeneralize from compulsory help. A learner treating every undelivered outcome as failed execution should undergeneralize ability after refusals. These are predicted tendencies, not imposed scoring outcomes: the wrong-rules learner can partially compensate through training.

The wrong-rules control feeds every episode into both banks, using attempted/not attempted for willingness and delivered/not delivered for ability. It discards assignment status and the distinction between unattempted and unsuccessful delivery within those streams. This is a lossy cue rule, not a permutation of two named heads that training could trivially undo.

Matched-history diagnostics compare failure with refusal, success with failed execution, and assigned outcomes with unchanged histories. They measure whether the appropriate prediction changes and the other remains stable, including transfer to a context with no history for that partner.

## What this test can establish

The test measures the efficiency and generalization consequences of supplying these cue rules. Their success in a world obeying them is expected. The useful quantities are the size of the learning-curve gap, whether it closes with more training, the behavior under cue-frequency reversal, and the failure of pooling outside its ecological assumptions.

It does not test whether evolution discovers these rules, whether the rules are unique, whether human learners use them, or whether functional specialization requires separate network weights. Those require additional studies.
