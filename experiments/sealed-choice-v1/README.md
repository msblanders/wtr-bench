# Does a later coin toss change the forecast of a sealed decision?

Two helpers privately spend equal amounts on different tasks. Each has grounds to expect a particular recipient will benefit. Both then seal an irrevocable decision about giving points to the same named recipient. Afterward an administrator uses a fresh fair coin, independent of both decisions, to retain or exchange the recipient assignments. The helpers believed the original assignments were final. The observer sees the toss result and never sees either sealed decision.

The primary prediction is invariance to the later draw. The identity of the helper who expected to benefit the target, the other helper, “equally likely,” and “insufficient evidence” are all admissible stable forecasts. Each draw produces a determinate factual answer about whose work actually benefited the recipient. There is no observed ground truth for either person's sealed choice.

## Fixed comparisons

The 12 matched forms comprise four counterbalances in each of the breakfast, camera, and archive settings. Each form is rendered with the original assignments retained or exchanged. The texts are identical apart from one sentence. Each of the 24 forecast requests runs twice in a fresh conversation with a byte-identical API payload. Each of the 24 factual requests runs once. Thus 72 calls contain 48 unique prompt texts. Trial IDs remain outside the messages and a deterministic hash orders all requests before collection.

Score the recorded answer field before reviewing any explanation. In each form, cross the two coin outcomes with the two repeats. Report the following descriptive counts by story and overall.

- A **stable forecast** gives the same semantic answer on all four requests, including consistent equality or insufficient evidence.
- A **reproducible shift toward the actual beneficiary** requires both stand forecasts to name the helper originally associated with the target and both swap forecasts to name the other helper. Also report opposite shifts, other reproducible changes, and forms on which identical repeats disagree.
- Report exact-repeat agreement over the 24 within-outcome comparisons. For across-outcome agreement, compare each stand response to each swap response within the same form. The 48 crossed comparisons are correlated. They describe the difference from ordinary repeat variation and are not independent cases.
- Count the 24 factual answers and show how many stable forecasts and reproducible outcome-following shifts also have both factual controls correct. Retain missing/invalid/refused/truncated outputs as separate statuses. Report usable denominators.
- Secondary directional contrast per complete form: code a forecast as +1 for the original helper, -1 for the other helper and 0 for either nondirectional answer. Subtract the mean swap score from the mean stand score and divide by two. A value of +1 means perfect outcome-following and 0 can include stability or cancellation. Report this alongside the categorical counts.

The strong evidence for outcome-following is a repeatable switch in the predicted direction accompanied by correct factual tracking. Consistent forecasts with correct factual tracking support stability on those forms. Unstable repetitions call for a weaker interpretation. Mixed patterns should be reported as such. There is no binary study-wide success cutoff or significance test over prompt permutations. These are three authored settings.

For the separate explanation audit, read each brief basis with the question and answer options, with the recorded answer hidden initially. Identify an explicit final endorsement of either helper, equality or insufficient evidence. Mark “unclear” for a genuinely ambiguous conclusion. A general statement that there is no basis to distinguish the helpers is compatible with either nondirectional answer unless the rationale explicitly distinguishes them. Flag clear conflicts with the recorded answer, give examples and denominators, and preserve all original answers for primary scoring. Explanations are observable text and do not establish mechanism.

## Collection

Use Python 3.11+ from this directory. Run `python3 run_study.py check` and `python3 -m unittest -v test_sealed` offline. `python3 run_study.py collect` uses the voucher pilot's no-retry transport, per-trial durable SQLite ledger, pinned Sonnet 4.5 model, explanation-then-answer protocol, temperature zero and 256-token output limit. `python3 run_study.py report` scores the ledger offline. One authorized branch push launches collection. Its 72 reservations total $0.718848 under the $1 guard. The workflow preserves all request bodies, raw model responses, usage and machine scores. Freeze digests in `freeze.json` cover the complete ordered request bank and scoring keys.
