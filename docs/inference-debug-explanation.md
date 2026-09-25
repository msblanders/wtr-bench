# Exploratory full debug with brief explanations

**Status:** Completed in [run 36095971330](https://github.com/msblanders/wtr-bench/actions/runs/36095971330)
and [audited](debug-36095971330-review.md). All 220 answers were usable, all
24 controls correct and all twelve returned rule calculations correct.
The full battery exposed eight option-order disagreements, unresolved
ladder estimates and a conditional ability/willingness interpretation issue.
Keep the pilot paused; do not repeat this batch as the default next step.
The subsequent [156-request measurement diagnostic is complete and audited](measurement-36099597085-review.md).
Its fixed stopping rule has been reached; no repeat or further range expansion
is recommended. The proposed next work is an offline plan for a narrower pilot.
The fixed protocol below is retained as specified before collection.

For reproduction only, open
[Actions → Inference debug (explanation)](https://github.com/msblanders/wtr-bench/actions/workflows/inference-debug-explanation.yml),
choose **Run workflow → main**, then click **Run workflow** once. The existing
`ANTHROPIC_API_KEY` repository secret is used.

This follows the [three-run calibration audit](calibration-explanation-repeats-review.md).
A/B passed the final-answer criterion in both planned replications. Its
initial control error and persistent false calculation remain documented;
SAM/YOU repeated one social order mismatch in all three batches. A/B is a
candidate for this exploratory debug step, not a validated social measure.
The 888-item pilot remains unrun, unfrozen and unregistered.

## Fixed batch

Protocol: `debug-explanation-v1`; **220 planned requests**; batch item hash
`bfe1d39e753b7316`. The original 196-item debug hash remains
`43e45d7065200983`.

| Block | Requests | Purpose |
|---|---:|---|
| Recipient lookup controls | 8 | Identify the named recipient |
| Quantity controls | 4 | Select the larger allocation |
| Explicit-rule controls | 12 | Apply the stated numerical rule |
| Attribution valuation questions | 60 | Five boxes conditions × six ratios × both option orders |
| Attribution willingness/ability questions | 40 | Five conditions × four binary probes × both option orders |
| Numerical-history valuation questions | 96 | Four diagnostic/totals cells × both evidence orders × six ratios × both option orders |
| Total | 220 | 24 controls plus 196 original debug questions |

The 24 controls run first, in their original A/B calibration sequence. The
196 debug questions follow in their original generator sequence. Each
request has fresh conversation context: no earlier control, answer or
explanation is included in a later prompt. The controls serve as a separate
concurrent check, not demonstrations, and never enter debug ladder fits.

All control prompts are byte-identical to the A/B controls in the explanation
calibration. For the debug questions, only the final answer-format instruction
changes. Histories, questions, names, amounts, causes, all binary probes,
option reversals and evidence-order reversals remain unchanged. The ladder
is **0.1, 0.2, 0.5, 1, 1.5, 2**, with the recipient offered 10 points.
Only the boxes scenario and debug numerical set are requested. No pilot
scenario or construction/scaling set is called by this workflow.

Each new item contains the original source item, including its ID and full
metadata. New batch IDs hash the protocol, source item and actual prompt.
For controls, the original explanation-calibration and earlier calibration
IDs remain available in that source record. The generated artifact saves
both the actual prompt and its source; these are not interchangeable when
reproducing an API request.

## Response protocol

Use exactly the calibrated A/B settings:

- Model: `claude-sonnet-4-5-20250929`.
- Temperature: 0; maximum output tokens: 256.
- One fresh user message per request.
- The same user ending and system instruction as A/B explanation calibration.
- Required JSON fields in order: nonempty string `brief_basis`, then `answer`
  constrained to `A` or `B`; no additional fields.
- A brief explanation of one or two sentences is requested. Sentence count
  is not a parsing criterion.

The API request contains only model/settings/schema and the actual prompt.
It receives no item IDs, truth keys, audit values, prior answers, examples or
scored outcomes. No numerical valuation or utility coefficient is required
for any social question. The API enforces the JSON schema using
`output_config.format`; the local parser retains the existing stricter
completion checks.

A usable response must have stop reason `end_turn` and exactly one text
block containing the required fields in order. Answer labels are
case-normalized. Empty explanations, malformed JSON, duplicate/missing/extra
fields, reversed field order, unexpected blocks and non-normal completion
are unusable. Truncated responses remain unusable even if their JSON looks
complete. Labels mentioned in the explanation cannot supply or repair a
final answer. All raw text and full SDK response bodies are retained.

## Separate scoring and the known calculation anomaly

Only the final `answer` field determines the scored choice. For a control,
`keyed` denotes whether that choice is correct. For a debug valuation item,
it denotes the partner keeping the own payoff; for willingness/ability it
denotes agreeing/managing. These meanings are kept separate by block and
source metadata. Social and binary debug judgments have no correctness key.

The 196 debug responses map back to their source item IDs for the existing
interval-aware scorer. No estimator changes are introduced. Missing requests
and unusable responses remain missing in the full planned item set. Censored
ladders supply bounds, tied best fits remain unidentified, and fitted
violations remain visible. Controls cannot affect a threshold estimate.

The known anomaly is the A/B `rule_1_20` control with Sam's option second:
A gives you 10 points, B gives Sam 20, and the rule weights your points by 1.
The correct option values are **A = 10, B = 20**. All three calibration
explanations incorrectly stated a 20-versus-20 tie; the later two returned
the correct B label without correcting those values.

This run therefore saves `control-review.jsonl`, with all 24 control prompts,
expected choices, returned choices and explanations. The twelve rule controls
also include the true displayed option values. Those values are computed
offline from the recorded rule-case parameters, independently checked against
the prompt allocations in tests, and never sent to the model. The report
places them beside the returned explanation.

**The automated report marks calculation accuracy `pending_manual_review`.**
For the completed run, the [separate audit](debug-36095971330-review.md)
records the finished twelve-response review without altering that raw report.
Before claiming that rule performance improved in any run, review the checkable values and
payoff assignments in all twelve rule explanations, including any wrong
values attached to a correct final answer. If an explanation supplies no
calculation, record that it provides no checkable numerical statement;
do not infer a correct calculation from its final label. Retain final-answer
accuracy separately, with the original truth keys. Do not automatically
infer calculations from arbitrary prose or grade social explanations for
agreement with a favored theory. These outputs are not access to internal
reasoning.

## Reports and review before any pilot decision

The main report and machine-readable score include:

- Control final-answer accuracy against planned denominators, missing and
  unusable counts, option-order checks, and the separate calculation review.
- Collection and semantic option-order checks by debug family and probe.
- Each valuation ladder separately by evidence order, showing both option
  orders at every rung, complete-pair denominators, observed monotonicity
  violations, fitted bounds/gaps, censoring and missingness.
- Numerical-history evidence-order comparisons at the same payoff ratio and
  displayed option order, with planned and complete pair counts.
- Each willingness and ability pair, including same-task and transfer probes.
- The existing interval-based contrasts and complete score JSON. These remain
  exploratory comparisons; they are not preregistered results.

An observed K-to-G decrease is counted between consecutive available answers
within a displayed order as the partner's payoff increases; missing rungs
remain visible. It is distinct from the scorer's minimum number of threshold
fit violations. A single best-fit gap can still have violations, and a
numerically narrow gap does not establish stable measurement.

Review collection and controls first, then order stability and ladder
behavior, before discussing theoretical patterns. All 24 final control
answers are expected to be usable and correct; investigate each error and
any faulty stated calculation. Review every debug order disagreement and
unresolved or nonmonotone ladder. Censoring is a bound, not a precise point
estimate; assess whether available bounds address the intended comparisons.
Neither a desired unable/unwilling ordering nor a LOW/HIGH difference is a
measurement-quality requirement. Preserve contrary findings.

There is **no automatic pilot approval or follow-up dispatch**. This run
should reveal whether the existing ladder supplies useful bounds and whether
the explanation protocol works across ability and willingness probes, beyond
the small calibration subset. The one debug scenario and one numerical set
cannot establish broad validity. A later pilot decision must explicitly
address the observed limitations, freeze the model/protocol/items/scoring and
missing-response rules, and record the pilot hash. Registration, if used,
must occur before collecting pilot responses.

## Artifacts, failures and resume

The `inference-debug-explanation-<run_id>-<attempt>` artifact contains:

- `items.jsonl`: all 220 actual prompts with their source items.
- `protocol.json`, `git-revision.txt`, `dependencies.txt`.
- `responses.jsonl` and its configuration sidecar: complete SDK bodies,
  raw text, request bodies without credentials, request/message IDs, stop
  reasons, usage, decoded explanations and final choices.
- `responses.md` and `responses.inspect.md`: complete or partial report.
- `responses.score.json`: the existing scorer's 196-item debug results.
- `control-review.jsonl`: 24 control audit records, separate from debug scores.

Offline protocol/scoring tests and synthetic recovery checks run before paid
calls. The workflow has a 25-minute timeout and uploads partial artifacts
with `always()`. SDK retries are disabled; an API failure stops collection
without switching models or falling back to unconstrained text. Recorded
unusable responses remain recorded; a normally returned wrong control answer
does not stop collection or cause a replacement call. It is reported for
review alongside the rest of the exploratory batch.

Every new workflow execution starts a new batch. Re-running a GitHub job does
not resume a prior artifact. For a partial run, download its artifact, check
out the recorded source revision and restore the response file and matching
configuration sidecar to the original output directory. Local resume skips
every recorded response, including unusable output, and requests only missing
items. Changes to item content/source metadata, model, budget, instructions,
schema or schema property order are rejected. A network failure can leave a
service-side response unrecorded locally; local resume cannot recover it.

## Local commands and budget

Generate prompts and protocol without API calls:

```bash
uv sync --frozen --all-groups --extra eval
uv run --frozen python -m wtrbench.explanation_debug generate
```

With the API key already supplied in the environment:

```bash
uv run --frozen python -m wtrbench.explanation_debug run
uv run --frozen python -m wtrbench.explanation_debug inspect runs/debug-explanation/responses.jsonl
```

At the saved source revision, with a restored partial run:

```bash
uv run --frozen python -m wtrbench.explanation_debug run --resume
```

The output allowance is at most **56,320 generated tokens** across 220
requests, plus input and API formatting overhead. This is a ceiling, not a
usage or price estimate. The workflow uses the API account's normal billing.
