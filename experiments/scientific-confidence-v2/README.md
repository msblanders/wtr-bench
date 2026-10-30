# Scientific confidence v2: representation and arithmetic

This follow-up addresses the output cutoff and two observed v1 errors: wrong associations
between hypotheses and predicted study effects, and incorrect normalization of evidence weights.
The protocol is frozen before any v2 API collection. The code is AI-assisted. It uses the same
public synthetic world generator as v1, with new disjoint random seeds and no case selection.

## Questions and comparisons

1. **Budget repair:** does the original contrastive audit outperform the original calibration
   checklist on fresh cases when each call may finish within 4,096 output tokens instead of 1,400?
2. **Primary representation question:** does preparing a source-linked table produce better
   confidence estimates than a calibration-checklist preparation when both use the same final
   worksheet schema and the same source-blind numerical calculator?
3. **Arithmetic question:** how much error changes when the model's own probability estimates
   are replaced by numerical calculations using exactly its own worksheet?

There are three preparation procedures: original checklist, original verbal audit, and a source
ledger. The ledger copies unique study IDs, design, context, estimate, SE, original priors, and
each hypothesis's predicted mean for that study's design/context. It also copies future-study
parameters. It does not calculate posterior probabilities during preparation.

Checklist preparation feeds two independent final calls: the original probability-only schema,
and a common worksheet-plus-probabilities schema. Audit preparation feeds only the original final
schema. Ledger preparation feeds the same worksheet-plus-probabilities schema as the checklist.
The checklist preparation is reused verbatim across its two final calls; final calls do not see
one another. Final-call order is randomized deterministically by case ID. This is seven calls per
case. Each individual two-call path has the same output-token ceilings, but actual tokens differ.

Each worksheet is scored twice: the probabilities stated by the model, and a deterministic
calculator's probabilities. These are two readouts of the SAME response, not independent LLM
conditions. The calculator has no access to the dossier, hidden generating mechanism, future
outcome, or correct posterior. Wrong means, priors, or data in a valid worksheet remain wrong.
Consistent duplicate study IDs count once; inconsistent duplicates make calculation invalid.
No source errors are repaired. Source fidelity is checked separately for evaluation only.

| Scored output | Preparation | Final output | Probability readout |
|---|---|---|---|
| checklist_verbal | Original checklist | Original probabilities | Model |
| audit_verbal | Original audit | Original probabilities | Model |
| checklist_manual | Original checklist | Common worksheet + probabilities | Model |
| checklist_calculated | Same response as above | Same response as above | Calculator |
| ledger_manual | Source ledger | Common worksheet + probabilities | Model |
| ledger_calculated | Same response as above | Same response as above | Calculator |

The primary contrast is **ledger_calculated minus checklist_calculated**, not the bundled
ledger+calculator versus a baseline without either feature. Negative favors ledger. The bundled
comparison, arithmetic readout comparisons, worksheet-output effect, and repaired original audit
comparison are prespecified secondary analyses. The manual ledger condition allocates preparation
to extraction rather than numerical reasoning, so it is not a pure formatting intervention.

## Sample and development check

Four development cases (one per design stratum), seed 90261031. Thirty-two main cases (eight per
stratum), seed 20261031. The v1 seed was 20261030; per-case seeds differ by 7919, so none overlap.
Case IDs are DEV000–DEV003 and TEST000–TEST031. The strata are replication, observational/randomized
contrast, unequal precision, and duplicate reports. They describe designs, not necessarily
observed contradictory findings. The main set is frozen before the development run and is never
selected, regenerated, or filtered by responses.

All calls use claude-sonnet-4-6, temperature 0, thinking disabled, 4,096 output tokens. The original
checklist/audit instructions and original final-answer schema are preserved for the budget repair.
Only the ceiling changes. The new worksheet instruction requests six decimal places for copied
non-simple numbers. Four concurrent workers; 28 development + 224 main = 252 planned API calls.

The development gate checks ONLY that all 28 calls complete, none is truncated, and tool outputs
are available. It does not require accurate probabilities, correct source mappings, or zero
normalization errors. A gate failure halts the main phase and is preserved. Any redesign needs a
new version/run; no automatic retries, rerolls, prompt tuning, or alternative-model fallback.
Successful development permits the already frozen main evaluation. Development cases are excluded
from main estimates. A passing small development check does not guarantee no main truncation;
all main truncation is reported and limits interpretation.

## Scoring and uncertainty

Known priors and independent Normal study likelihoods give an exact posterior and exact future
tail probability in this supplied-model world. Primary posterior regret is squared Euclidean
distance from the exact posterior: excess expected multiclass Brier loss. Unlike v1, the primary
analysis assigns invalid or missing probabilities a fixed loss of 2 (the global upper bound),
and invalid/missing future predictions a loss of 1. This prespecified composite penalizes failure
rather than obtaining an apparently better mean by dropping hard cases. Valid-only means and
valid-pair differences are also reported. An incomplete infrastructure run is not an efficacy result.

The original probability-sum tolerance of 0.005 is retained. Accepted vectors receive only the
corresponding small normalization adjustment. Calculator priors must be positive, finite, and sum
to one within 0.005; SEs must be finite and positive. All hypotheses must be present.

The independent sampling unit is the case. The primary paired difference gets a 10,000-resample
percentile bootstrap interval. Secondary intervals are descriptive, without multiplicity-adjusted
confirmatory claims. The 32-case study is exploratory and not powered for a chosen minimum effect.
Outputs/readouts and duplicated reports do not create additional independent samples.

Source diagnostics check IDs and design/context keys, every hypothesis-specific study/future mean
(absolute tolerance 1e-8), and copied input/prior numbers (1e-5). Numeric-copy error is also recorded
continuously. Diagnostics measure mapping fidelity and are never feedback to the LLM or calculator.

## Cost, freezes, and reproduction

The combined development+main ceiling is **$25**. The collector reserves a conservative cost before
each request using input UTF-8 bytes plus overhead and maximum output tokens at $3/M input and
$15/M output. Returned usage updates the ledger. Ambiguous failures retain their reservation;
infrastructure errors stop further sending. Phase markers prevent repeating a completed or partial
phase. The main phase restores the development spend ledger, so the cap does not reset between jobs.
Recorded dollar amounts estimate token charges, not the account invoice.

```bash
python -m unittest discover -s tests -p 'test_scientific_confidence*.py' -v
python experiments/scientific-confidence-v2/experiment.py generate --out /tmp/science-v2
# Explicit paid collection, with ANTHROPIC_API_KEY configured:
python /tmp/science-v2/experiment.py collect --out /tmp/science-v2 --phase development --budget-usd 25
python /tmp/science-v2/experiment.py collect --out /tmp/science-v2 --phase main --budget-usd 25
# Offline analysis:
python /tmp/science-v2/experiment.py report --out /tmp/science-v2
```

The freeze contains the exact runner, its v1 support file, protocol, model-visible cases, separate
gold, and file hashes. The inference task does not receive gold. Requests, responses, tool payloads,
usage, truncation, parsed records and scoring outputs are retained. GitHub Actions runs only from
the designated run branch and exact trigger message; run attempt >1 cannot make paid requests.
Development and main run in separate dependent jobs so the development artifact can be inspected.

## Scope and next decision

This isolates evidence bookkeeping and arithmetic in a closed, correctly specified model class.
Correct extraction plus an exact solver solves this particular inference task by construction;
showing that is not evidence of novel scientific discovery or a new training method. Both
calculator conditions may reach a floor, which would show the ledger adds little here.

Before training or claiming a residency-relevant operator, a later study needs repeated updates
to a readable state, stability with no new evidence, duplicate-source handling across updates,
genuinely new evidence, omitted hypotheses, and more realistic text. No weights are trained in v2.
The [v1 findings](../scientific-confidence-v1/PILOT_FINDINGS.md) explain why this experiment was chosen.
