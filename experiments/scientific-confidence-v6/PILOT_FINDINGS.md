# Scientific confidence v6: compact identity/status memory

Completed 2026-10-30. The compact-index policy passed all three prospective criteria for active-record accuracy and cost. It improved record maintenance over the active-only policy, met the specified five-percentage-point noninferiority margin against full history, and cost 25.61% less than full history. This supports the compact representation under the tested margins; it does **not** establish equivalent probability accuracy or calibrated scientific confidence.

## Design and completion

96 fresh paired main trajectories, three policies, 13 updates each, with identical verified starting records. Four separate development trajectories checked transport only. All 3,900 planned calls completed: 156 development and 3,744 main. All main readouts were valid, with no truncated responses or unknown-cost calls. Estimated token cost was **$89.398950**, below the $150 ceiling. Model: claude-sonnet-4-6, temperature zero, thinking disabled, maximum output 4,096 tokens. No weights were trained.

The compact state retains active numerical rows plus a small identity/status index for currently withdrawn evidence units. It stores canonical identity, latest revision, status and document references, without inactive numerical rows. All arms use the same calculator, which ignores the index and never repairs evidence. Hypotheses and likelihoods are supplied. All cases follow the same update order; event and position effects are not separated.

The main endpoint is each trajectory's incorrect-record fraction over reinstatement and the three following updates (steps 10–13). The four checkpoints per case are dependent; inference resamples 96 complete paired trajectories, not 384 independent observations.

| Policy | Correct records, steps 10–13 | Cases correct at every step 10–13 | Correct records, all 13 steps | Main API cost |
|---|---:|---:|---:|---:|
| Active-only instruction | 341/384 (88.80%) | 84/96 | 1,203/1,248 | $24.630333 |
| Compact identity/status index | 376/384 (97.92%) | 94/96 | 1,236/1,248 | $26.085450 |
| Full revision history | 380/384 (98.96%) | 95/96 | 1,239/1,248 | $35.067375 |

The remaining $3.615792 was development cost. Compact cost 5.91% more than the active-only instruction. Costs use recorded input/output tokens at $3/$15 per million, not an account invoice. All recorded cache-read and cache-creation token counts were zero.

## Prospective decision

All eligibility requirements and all three joint criteria passed. The sample was not expanded after seeing outcomes.

| Criterion | Estimate and interval | Decision |
|---|---|---|
| Compact superior to active-only | Error-fraction difference −9.1146 percentage points; paired 95% bootstrap interval [−15.8854, −3.1250] | Pass: upper endpoint below zero |
| Compact noninferior to history within 5 points | Observed degradation +1.0417 points; one of 96 cases worse; conservative one-sided 95% upper bound 4.8462 points | Pass: bound below 5, narrowly |
| Compact at least 10% cheaper than history | Cost ratio 0.74387; paired 95% interval [0.74098, 0.74683] | Pass: upper endpoint below 0.90 |

The cost saving is **25.61%**, with paired 95% interval **25.32–25.90%**. Cost inference uses the ratio of mean paired-case costs, not the mean of individual ratios.

The noninferiority bound is the preregistered exact Clopper–Pearson upper bound on the probability that a compact case has a higher post-window failure fraction than its history counterpart. Because the per-case degradation is at most the indicator of a worse case, that bound conservatively bounds mean degradation. Better compact cases do not offset worse ones. The five-point margin is a pragmatic design choice; the result does not establish equality or a tighter margin. Two worse cases would have failed this rule.

Compact had lower post-window record failure in 11 paired cases, higher failure in one, and equal failure in 84. No single case accounts for more than 9.31% of the absolute difference. History versus active-only also favored history: −10.1563 points, paired 95% interval [−17.1875, −3.9063]. That secondary replication is not multiplicity-adjusted.

## What failed and what improved

Ten new active-only errors appeared at reinstatement, versus zero new errors in either compact or history. Nine of those ten active-only failures persisted through correction, withdrawal and review; one recovered at the next correction. One additional active-only case failed at the later withdrawal. Compact's two failing trajectories both first failed when a new independent study was introduced, before reinstatement. Their identity/status indices were correct at that point.

Both compact failures assigned the wrong hypothesis prediction to the new study: a hypothesis with a constant predicted effect was given another hypothesis's context-dependent prediction. One of these failures also occurred under history; the other also occurred under active-only. The latter case generated the entire material probability-loss disadvantage of compact relative to history. The maximum post-window hypothesis-probability error was 87.80 percentage points for compact and active-only, versus 28.85 for history. A correct arithmetic calculation can amplify a wrong semantic input into a highly confident wrong conclusion.

History also had one earlier numerical-copy error that ceased affecting active-record correctness when the unit was withdrawn. The complete active-record trajectory was correct in 84/96 active-only, 94/96 compact and 94/96 history cases; history's post-window advantage is one additional case.

## Probability results are weaker than the record result

The secondary posterior loss is the sum of squared differences from the stipulated reference posterior, averaged across steps 10–13. It is not an empirical calibration score against observed scientific truth.

| Policy | Mean post-window posterior loss | Checkpoints within 0.5 percentage points on every hypothesis |
|---|---:|---:|
| Active-only instruction | 0.02194775 | 362/384 |
| Compact index | 0.01765145 | 376/384 |
| Full history | 0.00168723 | 380/384 |

Compact minus active-only posterior loss was −0.00429630, paired 95% interval [−0.01426912, +0.00336525]. Five cases materially favored compact, one favored active-only, and 90 were numerically negligible. This does not establish an improvement in mean posterior loss.

Compact minus history posterior loss was +0.01596423, paired 95% interval [approximately 0, +0.04789268]. One case accounts for all material disadvantage; excluding it descriptively removes the difference. That concentration is a limitation, not a reason to exclude the case. No probability-loss noninferiority criterion was specified or demonstrated. Full history's observed mean posterior loss was substantially lower despite only a one-case post-window record advantage.

History minus active-only posterior loss was −0.02026053, interval [−0.05787483, +0.00167898]. Its post-window future-probability loss contrast was −0.00663252, interval [−0.01932014, −0.000000919]. These are unadjusted secondary results; the complete secondary contrasts and concentration diagnostics are in results/summary.json.

## Adherence and limits

Compact retained no inactive numerical rows in any of its 1,248 main outputs, and its index met the diagnostic fidelity checks in 1,227/1,248. No condition exceeded the 120-word note allowance. Full-history output retained a completely faithful inactive-and-active history in 333/384 post-window checkpoints, even though active records were correct in 380/384.

The active-only instruction explicitly required an empty index, but the model populated it in **166/1,248 outputs across 70/96 cases**. The shared schema made that possible. These cases remained in the analysis as planned; no outputs were stripped or repaired. This is an assigned-policy comparison with imperfect adherence, not a clean contrast between strictly enforced memory contents. Its effect on the comparison cannot be quantified from this run. Free-form notes and references also permitted some historical information in every arm.

The experiment uses one model/configuration, short synthetic prose, five evidence units, at most two withdrawn-unit index entries and a fixed 13-update sequence. It compares retention representations together with maintenance instructions, without matching token use. The reference is the currently authoritative evidence record under stipulated amendment rules and supplied exhaustive hypotheses/Normal likelihoods. Real-paper ambiguity, unknown hypotheses, misspecified likelihoods, publication selection, empirical calibration and long-horizon reliability remain untested.

## Reproducibility and interpretation

All 43 scientific-confidence tests passed before collection. The exact offline audit in the original Python 3.11 runtime verified frozen hashes, identical regenerated fixtures, all 100 matched initial-request groups across three conditions, all 3,900 state handoffs and response-record pairs, and identical aggregate replay. The audit made no model calls. The downloaded original summary and audit matched the recorded run output exactly. Raw transport was authenticated and decrypted successfully; raw records and recovery materials are preserved in the private complete package. Public results contain aggregates only.

The supported result is a cheaper, more accurate evidence-maintenance policy relative to the active-only instruction, within an explicitly tolerated record-accuracy loss versus history. It is not yet a replacement for history when severe probability errors are unacceptable. A motivated next hypothesis is that checking the translation from each hypothesis into each study's predicted result before committing a record will reduce severe downstream probability errors. That follow-up has not been run; it should retain fresh cases, verified starts, cost accounting and a probability-sensitive endpoint.
