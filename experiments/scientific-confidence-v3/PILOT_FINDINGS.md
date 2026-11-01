# Fresh confirmation succeeds; the sequential test reaches a ceiling

The one-call evidence-table procedure replicated on 64 fresh cases, with about 60% lower
API cost than the two-call path. In the new sequential experiment, both procedures that
maintained an evidence state stayed accurate across all 12 updates in all 32 trajectories.
**The extra ledger instructions did not provide a meaningful advantage over the strong
checklist baseline.** The result supports the simpler structured workflow in this controlled
setting; it does not establish a novel improvement operator or general scientific reasoning.

## Completed run

- 1,360/1,360 calls; $23.622081 estimated from returned token usage.
- 80 development calls ($1.393758), excluded from main estimates; 1,280 main calls ($22.228323).
- Zero truncated calls, unknown-cost calls, missing outputs, or invalid calculated answers.
- Model: claude-sonnet-4-6, temperature 0, thinking disabled, maximum 4,096 output tokens.
- Frozen execution commit: `f0b2730b3d5136406f86846085e67cb9f0144323`.
- [Run 41004013922](https://github.com/msblanders/wtr-bench/actions/runs/41004013922).
- [Protocol](README.md) was written before collection; no prompt tuning or case filtering.

## A. Prespecified confirmation of the one-call finding

The first call constructs an evidence table. An external, source-blind calculator converts
that table into posterior and predictive probabilities. The second-call path reuses that
first table, asks the model to revise it, and calculates from the final table. Both readouts
use the same numerical code; neither receives source repairs or the oracle answer.

| Main result | One call + calculator | Two calls + calculator |
|---|---:|---:|
| Fresh cases | 64 | 64 |
| Source-faithful tables, within predefined tolerance | 64/64 | 64/64 |
| Mean posterior loss | 2.1253e-14 | 2.7712e-14 |
| Maximum hypothesis-probability error | 0.0000741 percentage points | 0.0000741 percentage points |
| API cost for all 64 cases | $0.882702 | $2.211999, including the shared first call |
| Cost per case | $0.01379 | $0.03456 |

The paired mean difference (one minus two calls) was -6.46e-15, with a descriptive 95%
bootstrap interval of [-2.25e-14, 2.65e-15]. Both paths are at the numerical/copying-precision
floor. The prespecified practical confirmation criterion passed: the interval's upper end
is below the 0.001 noninferiority margin, at least 95% of tables are source-faithful, and at
least 95% of cases place every hypothesis within half a percentage point of the oracle.
All 64 cases satisfy both absolute requirements. Recorded cost was **60.09% lower** for one call.

This converts the earlier post-hoc observation into a fresh-case, prespecified result on
this generator and configuration. It does not show that a second call is unnecessary on
other tasks or that a 64-case sample rules out rare failures.

## B. Sequential scientific evidence updates

32 independent trajectories, each with 12 checkpoints and six unique studies. Incoming
packets include new studies, repeated reports of existing studies, and reviews with no new
evidence. Source reports are short prose. All conditions produce the same structured state
and use the same source-blind calculator. The strong checklist baseline already receives
common instructions to retain original priors and all unique studies; only the added update
procedure differs between the two incremental conditions.

| Procedure | Source-faithful checkpoints | Entirely faithful trajectories | Mean posterior loss | Largest probability error |
|---|---:|---:|---:|---:|
| Checklist, maintain previous state | 384/384 | 32/32 | 7.21e-30 | 1.67e-12 percentage points |
| Explicit ledger, maintain previous state | 384/384 | 32/32 | 1.61e-15 | 0.0000276 percentage points |
| Explicit ledger, rebuild from original archive | 383/384 | 31/32 | 9.41e-6 | 4.31 percentage points |

The primary comparison uses 32 paired trajectory means, not 384 independent observations.
Ledger-state minus checklist-state loss was +1.61e-15, a negligible copying/rounding-scale
difference. Its interval is [4.29e-28, 4.45e-15]; a technically positive endpoint at this scale
is not a substantive superiority finding. **There is no meaningful added benefit from the
extra ledger instructions in this experiment.**

The secondary ledger-state minus archive-rebuild difference was -9.41e-6, with interval
[-2.82e-5, 3.90e-15]. One transient reconstruction failure drives this contrast. It does not
establish a general advantage for incremental state over access to the original archive.
The rebuild condition has different information access and input lengths, so it is a
diagnostic comparison rather than a matched estimate of the instruction's effect.

The sample was not selected for conflicting observations. Nevertheless, 24/32 trajectories
contained estimates with opposite signs; 85/128 new-study updates opposed the sign of at
least one previous estimate; and 71/128 new-study updates changed at least one correct
hypothesis probability by five percentage points. Thus the test included real updating
requirements rather than only repetitions of an unchanged answer. These sign conflicts
are descriptive; a context-specific hypothesis may predict them.

### No-evidence reviews and duplicate reports

Each condition has 224 duplicate/review transitions. Both state-maintaining conditions
showed no material probability movement at those transitions (squared movement threshold
1e-8), while correctly updating on new evidence. Their source tables remained faithful
throughout, within the frozen tolerances.

Rebuilding produced one source-mapping error on a duplicate-report checkpoint: two
hypothesis-specific predicted means were assigned incorrectly, despite correctly identifying
the unique studies and copying their observations. The calculator then faithfully computed
from the wrong table, producing a maximum probability error of 4.31 percentage points.
The next reconstruction, a review with no additional evidence, returned the correct table
and probabilities. All three conditions finished with negligible final-checkpoint error.

This illustrates why movement with no new evidence is not automatically a failure: one
transition introduced an error, and the next removed it. The rebuild model did not see its
previous wrong output, so this is a fresh reconstruction that corrected the result, not
evidence that it recognized its own mistake. One event is insufficient to infer a general
mechanism or frequency of failure.

Main sequential API costs: checklist-state $6.561399; ledger-state $6.790788;
archive-rebuild $6.664137. Equal call ceilings do not imply equal token costs.

## Interpretation and next useful experiment

The tested component is **source extraction into a readable state, followed by deterministic
probabilistic inference**. It is an inference-time workflow; no model weights were trained.
The confirmation supports removing the unnecessary second model call on this task. The
sequential result sets a useful baseline but reaches a task ceiling: a common table, a
calculator, and strong common instructions already suffice.

Translation to a symbolic representation followed by deterministic execution is established
prior work, including [Faithful Chain-of-Thought](https://arxiv.org/abs/2301.13379). Our evidence
here is about this workflow's accuracy, cost and short-horizon maintenance, not novelty of
that architecture.

The next useful challenge is **changing evidence provenance**: reports that use aliases for
the same study, corrected or withdrawn results that supersede old versions, and subgroup
findings whose scope changes which prediction applies. A versioned evidence record could be
compared with this now-strong baseline using the same calculator. That would test whether
an operator can preserve scientific meaning as evidence changes. It is a proposal, not an
experiment run in this version.

The current world supplies an exhaustive, correct hypothesis set and known Normal likelihoods.
There are only six unique studies, clear study IDs, short prose, no retractions, and 12
checkpoints. This does not establish real-paper interpretation, model-misspecification
detection, calibrated confidence in open-ended explanations, or Elicit's 1,000-plus-iteration
target. Elicit's [residency description](https://orion.elicit.com/careers/e04136b7-57e5-44d5-9a7c-cced3e2cb0f8)
emphasizes legible knowledge-state improvement over that much longer horizon.

## Verification and records

All 25 offline checks and repository CI passed before paid collection. Frozen input, runner,
support-file and protocol hashes were verified. Replaying the report locally reproduced the
original scores and summary with no structural differences; the largest numeric difference
was 4.62e-14, consistent with Python/runtime floating-point and accumulation differences.
The original archived outputs were retained unchanged.

Original run archive SHA-256:
`ec20562015dca1bda468df68d3b2fd3988ef51aa74e432ecd85b083b2a53ab4a`.

Aggregate summary is in `results/summary.json`. Complete raw requests, responses, cases,
gold, frozen code, and a supplementary descriptive audit are saved separately from the public
PR. The audit's case-level examples are not published here. No additional paid runs were made
after inspecting these results.
