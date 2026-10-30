# v2.1.1 stopped run: memory readout succeeds, payoff arithmetic remains unreliable

[Run 40982656128](https://github.com/msblanders/wtr-bench/actions/runs/40982656128) collected all 16 smoke requests and stopped before any of the 256 planned pilot requests. API cost: **$0.346452**. All outputs parsed, returned the requested model, and ended normally.

| Check | Observed result |
|---|---:|
| Memory probabilities reproduced exactly | 384/384 |
| Original decisions consistent with assigned memory | 240/256 (93.75%) |
| Smoke requests meeting every frozen requirement | 14/16 |
| Decisions matching the sign of the model's reported payoff | 256/256 |
| Event probabilities within .02 of the memory-derived event probability | 254/256 |

The failed requests were `smoke-s9002-shared-n24-functional` (14/16 decisions, below the required 90%) and `smoke-s9003-context_specific-n24-adaptive` (8/16). The latter emitted negative net values and declined all 16 options, even though eight were positive-value choices under its memory. The gate's failure remains the official result. The expanded schema issue from the preceding attempt was fixed; this stop reflects output behavior.

## Post hoc arithmetic diagnosis

An independent audit recomputed each original reference from the saved memory and payoffs and verified that the scorer was correct. It also verified that saved parsed values matched the original API responses.

Then, keeping **Claude's reported event probabilities unchanged**, it calculated `benefit * event_probability - fee` in Python and paid exactly when the result was positive. This produced memory-consistent decisions in **256/256 cases**, including all 16 originally mistaken choices. No probability, raw response, original decision, or acceptance threshold was changed. No further API request was needed.

Some outputs omitted fees; another output assigned negative net values to every decision. The independent recomputation locates the decision errors in the payoff calculation.

This post hoc calculation does **not** convert the frozen run into a pass. It identifies a practical remedy: use a deterministic calculator for payoff arithmetic, and evaluate learning-rule effects separately from arithmetic reliability. “Memory-consistent” does not mean optimal under the true generating parameters; a wrong memory can still produce a wrong real-world decision.

## Scope and next decision

The external-memory manipulation now has direct readout evidence on these fixtures, including the deliberately swapped memories. The pure-LLM decision reader failed the required criterion. Repeated prompt revisions to eliminate arithmetic mistakes would not test the research program's central claim about learning.

Keep the current pilot stopped. For subsequent work, compute payoff arithmetic in code and measure the accuracy, efficiency, and transfer of the update procedure itself. Most of this particular fixed-estimator comparison can already be computed without an LLM; copying its probabilities through Claude adds little evidence about how learning rules are acquired. A study of learned or selected update rules needs its own design and strong held-out comparisons.

## Reproduce

The original [workflow artifact](https://github.com/msblanders/wtr-bench/actions/runs/40982656128/artifacts/12945293432) preserves the raw responses and frozen smoke gate. A private reproducibility bundle also contains the exact archive and generated diagnostic results. The new raw archive is not committed to this public branch. The archive SHA256 is `faa415f6a13d641260275c329ef08bf9bd0d4a5e9a963e5656bb378a621eb460`.

From the repository root:

```bash
python3 experiments/controlled-memory-v2/audit_saved_run.py --archive /path/to/controlled-memory-v2-40982656128-1.zip --out diagnostic-analysis.json
```

The audit uses only the standard library, verifies the archive/source/request hashes, reads the saved data without executing the frozen code, and makes no network calls.
