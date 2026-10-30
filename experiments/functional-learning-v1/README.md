# Does a functional procedure improve learning from experience?

An exploratory EFLA experiment using Claude Sonnet 4.6. This is a separate experiment from the completed WTR-Bench pilot and the recipient-specific follow-up. The functional specification below is a provisional implementation to test, not an established evolutionary-psychological result.

## Question and scope

Does explicitly separating evidence about **choosing to help** from evidence about **executing help** improve an LLM's probabilistic predictions as experience accumulates? Does the benefit disappear or reverse when the proposed cross-setting generalization is wrong?

This measures inference and learning from supplied context. Each checkpoint starts a fresh API context with a nested evidence history. There are no weight updates, persistent learned memories between requests, evolutionary selection, or causal interventions on internal representations. A positive result would justify a subsequent test of a persistent learning system; it would not establish an evolved module or a unique EFLA mechanism.

## Candidate functional specification

For each partner, track two estimates:

| Estimate | Informative observations | Observations excluded | Prediction it feeds |
|---|---|---|---|
| Inclination to attempt | Voluntary attempts and declines | Externally assigned attempts | Probability of choosing an attempt |
| Execution reliability | Successes and failures following an actual attempt | Declines, which have no execution outcome | Probability of success conditional on an attempt |

Costs and recipient benefits are fixed. The inclination variable is a voluntary-attempt probability, **not a numerical welfare-tradeoff ratio**. The model is a deliberately simplified causal world: choice and execution reliability are independent latent quantities. Neither is inferred from a single successful outcome alone.

## Design

Four instruction conditions receive identical evidence and questions:

1. **General:** careful probabilistic learning instructions.
2. **Structured:** two-component summaries, with the model choosing their contents and update rules. This is the primary active control.
3. **Functional:** the specified evidence routing, with partner estimates pooled across settings.
4. **Wrong routing:** swap which evidence updates which estimate. This is a deliberately incorrect ablation, not a strong rival theory.

The conditions use roughly comparable instruction lengths, the same response schema and output-token limit, and an at-most-80-word reasoning request. Instruction token counts are not identical. Functional instructions supply additional substantive knowledge on purpose; equal evidence does not mean equal prior information. This first comparison tests routing and pooling jointly. It cannot separately attribute a benefit to either component.

Each world has four partners and three settings. Training histories cover two settings; predictions also include the third. Every partner has observations at **0, 2, 8, and 24 episodes**. Early histories are prefixes of later histories. Records distinguish voluntary from assigned attempts and distinguish declining from execution failure.

Two paired environments vary only the choice-rate structure:

- **Shared:** a partner's inclination and execution reliability carry across settings.
- **Context specific:** inclination differs independently across settings; execution reliability still carries across settings. Pooling inclination is therefore misleading. The optimal prior prediction in the unseen setting is 0.5.

All latent rates have independent uniform priors, apart from the sharing just described. The environment label and true rates are withheld from the API. Histories, assignment schedules, and random draws are paired where possible. Query order is shuffled consistently across conditions. Requests are collected in a fixed shuffled order.

Default pilot: **8 independent world seeds × 2 environments × 4 checkpoints × 4 conditions = 256 requests**. Each request returns 24 probabilities. Seeds, rather than individual probabilities, are the replication unit. Eight seeds make this an exploratory pilot, not a powered confirmatory study.

## Outcomes and interpretation fixed before collection

The main score is mean squared error against the known generating probabilities. It equals the reducible component of expected Brier loss, avoiding noise from one sampled future outcome.

The **primary contrast** is structured-minus-functional error, averaged equally over the three nonzero checkpoints, reported separately by environment. Positive values favor functional updating. Report paired world-bootstrap intervals, learning curves, and separate errors for seen-setting choices, transfer choices, and execution. The shared-minus-context-specific difference in the primary contrast is a secondary boundary-condition test.

Also report the first observed checkpoint attaining MSE ≤ 0.04 and remaining below it at all later observed checkpoints. This is a descriptive, arbitrary accuracy criterion; failures to attain it are censored beyond 24 episodes, not discarded. Do not interpolate unobserved learning budgets.

Invalid responses receive maximal squared error (1) in the primary utility score. Valid-only error and invalid counts are reported separately. Missing responses are not imputed; incomplete collections cannot establish the planned full contrast. There are no automatic response repairs or retries.

Deterministic references include a Bayesian estimator with the true environment structure, the proposed pooling rule, wrong routing, and outcome-only estimation. These are **computed reference results, not LLM observations**. The Bayesian estimator has privileged structural knowledge and is an optimal posterior predictor under the stated model, not a guaranteed best score in every finite sample.

- A benefit over the structured control in the shared environment, with a smaller benefit or harm when sharing is false, supports the value and cost of this supplied inductive bias.
- Beating only wrong routing is insufficient evidence for the useful claim.
- A null with strong control performance may indicate the model already infers the decomposition. A null with poor performance motivates examining instruction following and evidence use before scaling.
- No result here alone identifies an internal scalar, establishes an evolutionary origin, or demonstrates a unique advantage over all Bayesian or modular alternatives.

This is an exploratory protocol frozen with the run, **not an external preregistration**. One model, one wording per condition, and one completion per request limit generalization.

## Run

Python 3.11 or later; no additional dependencies are needed.

```bash
python3 -m unittest discover -s tests -p test_functional_learning.py -v
python3 experiments/functional-learning-v1/experiment.py generate --out runs/functional-learning-v1 --seeds 8
```

Generation freezes the source, exact requests, hashes, and reference predictions. It makes no API calls. The directory must be new. Only the request `body` is sent to the API; answer keys remain local.

With `ANTHROPIC_API_KEY` available securely in the execution environment:

```bash
python3 runs/functional-learning-v1/experiment.py collect --out runs/functional-learning-v1 --budget-usd 25
python3 runs/functional-learning-v1/experiment.py report --out runs/functional-learning-v1
```

Use the frozen copy for collection and reporting. Never paste credentials into chat or commit them. The manual `functional-learning-v1` GitHub workflow offers offline, read-only `check-access`, and collect modes using GitHub secret `WTR_BENCH` when present, otherwise `ANTHROPIC_API_KEY`. The selected value is passed to the collector as environment variable `ANTHROPIC_API_KEY`.

For the initial pilot, a push to the dedicated branch `run/functional-learning-v1-20261029` with the exact commit message `Run functional-learning-v1 pilot once` also launches collection. Ordinary code commits and pull requests do not launch paid collection. This permits the bounded experiment to run before merging its implementation. Do not repeat that launch message on the run branch to restart a partial collection.

The commit message `Check functional-learning-v1 API access` on that branch instead performs a read-only model-metadata request. It does not request a completion or collect experimental data.

The 256-request plan reserves approximately **$13.41**, using a deliberately conservative byte-based input allowance and the full output limit at [$3 input / $15 output per million tokens](https://platform.claude.com/docs/en/models/sonnet-4-6/overview), checked October 29, 2026. Actual costs come from recorded usage. The collector refuses planned spending beyond $25 and stops on missing usage or an exceeded allowance. This is a local spending guard, not a provider-enforced billing cap.

Collection is single-pass. An exclusive ledger blocks reruns of the same directory, and transport failures stop without retrying because an uncertain request may have incurred a charge. Inspect preserved artifacts before arranging recovery; generating a new directory does not reset provider spending. GitHub reruns of paid jobs are disabled. Raw responses, usage, attempts, status, and report files are retained in the run artifact.

## Initial launch status — October 29, 2026

- [Repository CI](https://github.com/msblanders/wtr-bench/actions/runs/40957205530) passed lint, type checks, the test suite, and the existing synthetic pilot. The new experiment's 13 offline tests passed separately as well.
- [Initial collection](https://github.com/msblanders/wtr-bench/actions/runs/40957490711) stopped on an HTTP rejection of the first request. No model responses were collected. Frozen inputs and the attempt ledger were preserved in the workflow artifact.
- A separate [read-only access check](https://github.com/msblanders/wtr-bench/actions/runs/40957786680) returned HTTP 401, `authentication_error`, `invalid x-api-key`. No completion was requested in that check.
- The replacement was saved as GitHub secret `WTR_BENCH`. The workflow now supports that name. A [read-only check](https://github.com/msblanders/wtr-bench/actions/runs/40969613278) returned HTTP 200 for `claude-sonnet-4-6`.
- The [completed collection](https://github.com/msblanders/wtr-bench/actions/runs/40969709564) returned all 256 responses for $3.511197. The request stream was unchanged (`a28acac7eeffb1087581d6cb4cdc1d669f82bd4dcc6396e9acc8f91dba5a34e8`). Earlier rejected attempts remain in the run history.

## Completed pilot results

See [the full results and limitations](results/run-40969709564/README.md). The exact raw artifact, original scores, post hoc analysis, and reproducible analysis script are included.

The strict parser accepted 109/256 responses. All 256 contained complete probability predictions; extracting the JSON objects without changing probabilities yields an explicitly post hoc analysis. Functional instructions reduced mean error by 27.4% versus the structured control in the shared environment and increased it by 15.9% in the context-specific environment. However, the wrong-rule condition behaved much more like correct routing in all 48 nonzero-history cases, so the intended manipulation failed. This is exploratory evidence about pooling assumptions, not a clean validation of the proposed update rule.
