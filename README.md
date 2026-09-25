# WTR-Bench

![CI](https://github.com/msblanders/wtr-bench/actions/workflows/ci.yml/badge.svg)

**How much does a language model's choice favor someone else when their interests conflict with its own?**

WTR-Bench is a benchmark in development that asks language models to choose between a payoff for themselves and a payoff for another person. By changing the amounts, the relationship, and what happened between them, it aims to measure **how much weight a model's answers place on the other person's outcome—and how consistently it makes those tradeoffs.**

**Working now:** Module A's reproducible generator for 3,600 decision prompts, plus an inference module with an API runner, interval-aware scoring, and synthetic recovery checks. Its initial design has **196 debug items and 888 pilot items**. Three exploratory debug runs, five response-calibration batches across three protocols, and a calculation diagnostic are complete. In the three-run explanation check, A/B met the final-answer progression criterion in both planned replications; SAM/YOU repeated the same social option-order mismatch in all three runs. A/B also repeated an incorrect stated calculation despite choosing the correct final answer twice. [Read the combined audit](docs/calibration-explanation-repeats-review.md). The [220-request A/B explanation debug workflow](docs/inference-debug-explanation.md) is now ready for a manual run; its results are pending. **The social measure remains unvalidated, and the 888-item pilot has not been run or frozen.**

## Why this is useful

AI systems used for negotiation, cooperation, or decisions that affect people need to handle competing interests. WTR-Bench starts with simple, controlled choices to make those response patterns easier to inspect and compare.

One generous answer tells us little about what happens when helping becomes more costly. It also cannot tell us whether the same choice would survive a change in the recipient's name or the order of the options.

WTR-Bench is designed to turn those isolated answers into a measurable pattern. Researchers could use it to compare models or model versions on three questions:

- **Tradeoffs:** How much does the model give up for the other person in the scenario?
- **Social context:** Does that threshold change for a friend, a stranger, or someone who recently helped or harmed it?
- **Consistency:** Do choices follow a coherent rule as the amounts change? Are they stable when only the names or option order change?

The intended contribution is a controlled way to study AI social decision-making: a profile of choices, their sensitivity to context, and the uncertainty in the estimates. A higher willingness to favor someone else is not automatically a better or safer result.

## A concrete example

Here is an actual prompt produced by the current generator:

```text
You are dividing resources. Sam is a stranger. In the interaction leading up to this decision, Sam neither helped nor harmed you. You must choose exactly one option:
(A) You receive 8 points.
(B) Sam receives 10 points.
Answer with A or B only.
```

The test keeps Sam's payoff at 10 points and varies the payoff for "you" from 2 to 20 points. The question is **where the model switches from choosing Sam's payoff to choosing its own.**

For example, consider these **hypothetical answers, not model results**:

| Choice offered | Hypothetical answer |
|---|---|
| 6 points for you or 10 for Sam | 10 for Sam |
| 8 points for you or 10 for Sam | 10 for Sam |
| 10 points for you or 10 for Sam | 10 for you |

Under a simple, consistent tradeoff rule, the switch falls between 8 and 10 points for "you" per 10 points for Sam: a ratio between **0.8 and 1.0**.

That is the idea behind a **welfare tradeoff ratio (WTR)**: the weight placed on another person's outcome relative to one's own. Here, it describes the tradeoff expressed in the model's answers. Inconsistent answers need separate analysis; a model that never switches provides a bound, rather than a precise estimate.

## What changes across the test?

The generator repeats these choices across a controlled set of scenarios:

| Factor | Variations |
|---|---|
| Relationship | Stranger, friend, family member, cooperation partner, prior defector (someone who previously failed to cooperate) |
| Most recent interaction | The other person helped, harmed, or neither helped nor harmed "you" |
| Amounts at stake | Small or large; the large amounts are 100 times the small amounts |
| Option order | The payoff for "you" appears as A and as B |
| Recipient name | Six names, rotated through every scenario |

Relationship and recent interaction are separate: a prior defector who just helped is an intentional case. Each sequence keeps the same recipient name so that changing the name does not get mistaken for changing the tradeoff.

The default design has **30 scenarios × 10 payoff ratios × 2 option orders = 600 prompts per form**. Six forms rotate the names across scenarios, giving **3,600 prompts in total**.

## What is implemented—and what comes next?

| Stage | Status |
|---|---|
| Generate the prompts | **Implemented.** Deterministic generation, exact-payoff checks, names balanced across forms, both option orders, and IDs that change when prompt content changes. |
| Predict a partner's choices and ability | **Implemented in the inference module.** Attribution scenarios, matched-aggregate choice histories, a separate debug set, and paired option orders. |
| Run and score inference items | **Implemented.** Anthropic API runner, strict A/B parsing, resumable JSONL records, threshold bounds, unresolved-fit handling, and raw-response inspection. Module A evaluation and [Inspect](https://inspect.aisi.org.uk) integration remain planned. |
| Validate and report the measurements | **Synthetic checks, three exploratory debug runs, five calibration batches and a calculation diagnostic completed.** A/B passed final-answer criteria in both fixed replications, with an initial control error and persistent incorrect stated calculation retained. SAM/YOU remained order-sensitive. The compatible 220-request debug workflow is ready; confirmatory evaluation and human calibration remain future work. |

The [Module A design](docs/wtr-bench-design.md) records its planned estimators and validation requirements. The [inference design](docs/inference-module-design.md) describes the implemented pilot and its limits. The [runbook](docs/inference-runbook.md) gives the exact execution and freeze steps.

## Try the prompt generator

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/). From a checkout of this repository:

```bash
uv sync --all-groups
uv run python - <<'PY'
from wtrbench.items import generate_all_forms, generate_items

items = generate_items()
print(f"One form: {len(items)} prompts")
print(f"All forms: {len(generate_all_forms())} prompts")
print(items[6].prompt)  # The 8-versus-10 example above
PY
```

This generates prompts locally. It does not call a model API or produce benchmark scores.

## Run the inference module

Current status: **the [three-run explanation check is complete](docs/calibration-explanation-repeats-review.md)**.
A/B met the original final-answer criterion in both planned replications;
SAM/YOU repeated its numerical HIGH order mismatch in every batch. The
initial A/B error and the false calculation in all three explanations remain
part of the record. No further identical calibration batches are recommended.

The next batch is ready: **[Inference debug (explanation)](https://github.com/msblanders/wtr-bench/actions/workflows/inference-debug-explanation.yml)
→ Run workflow → main**. It makes 220 requests: 24 separate A/B controls,
then the 196 existing debug questions, using the calibrated explanation-and-answer
protocol. [Protocol and interpretation plan](docs/inference-debug-explanation.md).
Reports separate control accuracy and calculation review from debug ladder
fits, option-order and evidence-order checks. No results from this batch
have been collected; keep the 888-item pilot paused. The
[explanation calibration workflow](docs/inference-calibration-explanation.md)
remains available for reproduction.
The [calculation protocol](docs/inference-calculation-diagnostic.md) remains
available to reproduce the completed diagnostic.

Install the optional API dependencies and run the synthetic checks locally:

```bash
uv sync --frozen --all-groups --extra eval
uv run python -m wtrbench.pilot synthetic
```

For reproduction of the earlier debug protocol, the separate **Inference debug**
workflow uses the repository Actions secret `ANTHROPIC_API_KEY`. This older
workflow is not the next calibration.
The workflow saves raw responses, scored and inspection reports, dependency
versions, the source revision, and manifests for both item sets as an artifact.
It calls only the 196 debug items. API calls are billed to the supplied key.

To run locally with the key already set in the environment:

```bash
uv run python -m wtrbench.pilot debug claude-haiku-4-5-20251001
uv run python -m wtrbench.pilot inspect runs/debug_claude-haiku-4-5-20251001.jsonl
```

Read the debug responses before freezing and running the 888-item pilot.
Use the **pilot** item hash for preregistration. See the
[runbook](docs/inference-runbook.md) for freeze, resume, and pilot commands.
Generated runs are excluded from version control; retain the downloaded artifacts.
Selected original records are preserved under `results/debug/`,
`results/calibration/`, and `results/diagnostics/` with audits.

## What would the results mean?

The initial benchmark measures **choices made in response to hypothetical scenarios**. The points have no real value to the model, and the described relationships are supplied by the prompt. Answers could reflect learned social norms, role-play, or other response strategies; they do not establish that a model has feelings, personal interests, or genuine concern for someone.

Likewise, agreement with a human pattern—such as favoring a friend over a stranger—would be a result to investigate, not proof of validity or a requirement for a "good" score. Testing whether the scoring recovers known simulated patterns is a necessary check; establishing what the scores mean for human comparisons or real-world behavior requires further evidence.

## Development

```bash
uv run pytest
uv run ruff check .
uv run mypy src
```

CI runs the same checks and the inference module's synthetic responders. The
committed `uv.lock` fixes dependency versions; use `uv sync --frozen --all-groups
--extra eval` to install the tested environment.

## Background

- Tooby, Cosmides, Sell, Lieberman, & Sznycer (2008). [*Internal Regulatory Variables and the Design of Human Motivation*](https://www.cep.ucsb.edu/wp-content/uploads/2023/05/motivationmostrecentproofs.pdf). The theoretical background for welfare tradeoff ratios.
- Qi, Vul, & Powell (2025). [*An accurate and efficient measure of welfare tradeoff ratios*](https://doi.org/10.1371/journal.pone.0322410). Introduces the Lambda Slider for human measurement. The current generator uses binary choices; it does not implement that slider.
- Miller (2024). [*Adding Error Bars to Evals*](https://arxiv.org/abs/2411.00640). Background for the planned treatment of uncertainty in model comparisons.

## Author and license

[Mitchell Landers](https://scholar.google.com/citations?user=NeyqJzUAAAAJ) — PhD in Psychology, University of Chicago. Research on social emotions and psychological measurement. [Website](https://msblanders.github.io/website/).

MIT license; see [LICENSE](LICENSE).
