# Fixed range and conditional-question diagnostic

**Status:** The fixed batch completed in [run 36099597085](https://github.com/msblanders/wtr-bench/actions/runs/36099597085)
and is [audited](measurement-36099597085-review.md). All 156 responses are
usable and all 32 final control choices correct, but one false calculation
recurred and the wider range/clarification did not establish a stable scalar
measure. The one-batch stopping rule has been reached. End this tuning loop;
no repeat or further expansion is recommended. The 888-item pilot remains
unrun, unfrozen and unregistered. The prospective specification below is
retained as written before collection.

For deliberate reproduction only, open [Actions → Inference measurement diagnostic](https://github.com/msblanders/wtr-bench/actions/workflows/inference-measurement-diagnostic.yml),
select **Run workflow → main**, and click the green **Run workflow** button
**once**. There are no model, range or budget inputs to choose. The existing
`ANTHROPIC_API_KEY` repository secret is used.

Protocol **`measurement-diagnostic-v1`**, **156 planned requests**, item hash
**`a23f46bf6a51a8c8`**. This specification fixes selection, prompts, range,
comparisons and stopping before collecting the new responses. It is not
a preregistration or a confirmatory test of the social hypotheses.

## Why these cases

The [previous full-debug audit](debug-36095971330-review.md) found correct
controls but no uniquely identified interior ladder fits, eight option-order
disagreements, and explanations overriding an explicit future-ability
condition. Another unchanged calibration would not address those findings.

The diagnostic selects already exposed debug cases for specific reasons:

- **Boxes: unable and unwilling.** These are the original focal contrast;
  they span the upper-range/order problem and the lower-censored end.
- **Numerical LOW and HIGH, T2, both history orders.** T2 contains the
  earlier option/history-order disagreements; the matched HIGH condition
  retains the intended comparison. Histories and totals are unchanged.
- **Same-task willingness and different-task ability, in both unable and
  unwilling.** This includes both flagged conditional probes and the
  opposite-cause comparison for each, preventing review of affected items
  without a matched comparison.

Baseline, helped, constrained, numerical T1 and other binary probes are not
sampled in this bounded batch. Their earlier findings remain unresolved;
success here cannot be generalized to all of them. No unexposed pilot
scenario or numerical construction/scaling set is used.

## Fixed request budget

| Block | Requests | Construction |
|---|---:|---|
| Original known-answer controls | 24 | All existing A/B controls, unchanged |
| Fractional-rule controls | 8 | Four explicit rules × both option orders |
| Range probes | 96 | Six evidence cells × eight ratios × both option orders |
| Decimal spelling anchors | 12 | Six cells × both option orders at the same 1-versus-10 allocation |
| Conditional probes | 16 | Two causes × two probes × original/clarified wording × both option orders |
| **Total** | **156** | One fixed batch |

The six valuation cells are two boxes causes plus LOW/HIGH T2 in each
history order. The 32 controls run first, then 96 range requests, twelve
spelling anchors, and sixteen conditional requests. Range requests follow
the original cells' sequence, increasing ratio within cell, with keyed-A
then keyed-B adjacent at each ratio. Conditional requests retain source
sequence, with original then clarified wording per displayed order.
The complete generated item list records the exact sequence.

There are **80 byte-identical request anchors** from run 36095971330:
24 original controls, 48 original valuation requests and eight original
binary requests. The report compares their new choices with archived
choices without pooling the old responses into any current estimate.
Every request has fresh conversation context: no control or earlier answer
is shown to the model in later questions.

## Wider range without changing the recipient's stake

The recipient remains offered **10 points**. The ratio is Sam's payoff
divided by the recipient's payoff. All histories, names and relationships
are preserved, and only the specified probe payoff changes.

| Ratio | Sam's points | Your points | Role |
|---:|---:|---:|---|
| 0.01 | 0.1 | 10 | New lower extension |
| 0.05 | 0.5 | 10 | New lower extension |
| 0.1 | 1 | 10 | Original anchor |
| 0.2 | 2 | 10 | Original anchor |
| 0.5 | 5 | 10 | Original anchor |
| 2 | 20 | 10 | Original anchor |
| 4 | 40 | 10 | New upper extension |
| 8 | 80 | 10 | New upper extension |

Fractional points avoid increasing the recipient's stake to 100 merely to
obtain smaller ratios. Exact decimal arithmetic constructs the amounts;
there is no integer rounding, zero payoff or duplicate rung. The 0.1/0.2
anchors retain both numerical mismatches, and ratio 2 retains the unable
order disagreement. This is a coverage diagnostic, not a dense precision
ladder: ratios 1 and 1.5 are not repeated in this batch.

New low ratios also introduce fractional notation. Two checks address that
limitation without treating it as solved in advance:

1. At ratio 0.1, each evidence/order cell is repeated with **Sam receives
   1.0 points** instead of **Sam receives 1 points**. Every other character,
   including the recipient's 10-point amount, is unchanged. These twelve
   comparisons isolate that spelling change at the same allocation and
   are excluded from all ladder fits.
2. Eight explicit-rule controls check fractional amounts in both option
   orders, balanced for selecting Sam versus you:

| Sam's payoff | Stated weight on your 10 points | Sam-option value | You-option value | Correct recipient |
|---:|---:|---:|---:|---|
| 0.1 | 0.005 | 0.1 | 0.05 | Sam |
| 0.1 | 0.05 | 0.1 | 0.5 | You |
| 0.5 | 0.02 | 0.5 | 0.2 | Sam |
| 0.5 | 0.1 | 0.5 | 1 | You |

The control rule explicitly says the unnamed recipient receives zero and
the greater stated value is chosen. No social question states a known
weight or demands a numerical valuation. Passing a 1/1.0 spelling check
and these rules cannot establish invariance for every fractional amount;
interpret the lower extension with that remaining limitation.

## Minimal clarification of the conditional probes

Both original and clarified questions retain their entire original history,
task, binary options, order reversal and answer instruction. The clarified
variant adds one sentence immediately before “Which is more likely?”

| Probe | Existing stipulated condition | Added sentence |
|---|---|---|
| Same-task willingness | Sam is free that day and would be able to do it. | For this question, take Sam's availability and physical ability at that future time as given, regardless of any earlier limitation. |
| Different-task ability | Sam makes a real effort to proofread a short document for you, with enough time to do it. | For this question, take Sam's effort and available time as given, regardless of any earlier willingness to help. |

The same addition is applied in both causes and both option orders. It does
not tell the model whether Sam will agree or manage the task. In particular,
real effort does not guarantee ability, and physical ability does not
guarantee willingness. The clarification reinforces the existing hypothetical
condition; it does not rewrite the past event or assign a social truth key.

## API, integrity and scoring

Keep the calibrated settings: `claude-sonnet-4-5-20250929`, temperature 0,
maximum output tokens 256, and the same API-enforced ordered JSON schema:
nonempty `brief_basis`, then `answer` constrained to A/B, no additional fields.
The existing strict decoder and API transport are reused. Numerical truth
values and item metadata are never included in the API request. The maximum
configured output allowance across the batch is 39,936 tokens; input tokens
are additional. This is an allowance, not a predicted bill or usage total.

Stop reason must be `end_turn` with exactly one text block and valid ordered
fields. A label mentioned in the explanation cannot repair an invalid final
answer. Raw text, full SDK response, request body, request ID, model ID,
usage, stop reason and parsed fields are saved for every returned response.
Unknown/duplicate items, duplicate API IDs, model mismatch or tampering fail
validation. Item IDs include protocol, actual prompt, seed and diagnostic
metadata; the batch hash includes sequence.

Each item retains the unmodified original **seed** and its debug ID for
provenance. For extensions and fractional controls, that seed's amounts
are historical. The wrapper's **actual prompt, `ratio`, `own_amount`,
`fixed_amount`, `rule_weight` and `expected_option_values`** describe the new
request. The new report uses those actual ratios, not the seed's old rung.
The original inference generator and pilot scoring are unchanged.

Only the 96 range requests enter ladder fits. Use the existing threshold-gap
estimator, preserving tied fits, censoring, violations and missingness.
Report each numerical history order separately, both displayed-order fits,
their pooled fit, all rungs and keep-to-give decreases. Report LOW-minus-HIGH
interval comparisons separately by history order. No new inferred-WTR point
is manufactured for a censored or tied fit.

Report original/fractional control accuracy separately; keep all 32 in
planned denominators. Review every checkable statement in all **twenty rule
explanations**, including correct final answers. If no calculation is given,
record that absence instead of inferring correctness. Expected values are
offline audit annotations. Social explanations are not graded against a
preferred numerical theory, and no explanation changes a scored answer.

## Interpretation and stopping fixed before collection

1. **Collection and controls:** inspect every missing/unusable answer,
   wrong control and erroneous stated calculation. Preserve failures; do
   not drop them to improve a denominator. No response-contingent stopping
   or additional sampling is used within the batch.
2. **Coverage and robustness:** an order-consistent cell requires all eight
   complete valuation pairs to agree. A monotone displayed-order sequence
   has no observed keep-to-give decrease. A uniquely fitted interior gap
   with zero violations is informative, but acceptable bounds can also
   address comparisons. Persistent endpoint censoring or tied/order-sensitive
   fits remain findings, not permission to assign a point estimate.
3. **Notation:** inspect all twelve 1/1.0 pairs and all fractional controls.
   Any notation mismatch is reported. A lower-range switch cannot be
   attributed solely to ratio sensitivity when representation problems
   remain. Do not merge spelling-anchor responses into range fits.
4. **Conditional fidelity:** manually read all sixteen binary explanations
   using `respects_condition`, `contradicts_condition`,
   `unclear_or_no_checkable_basis`, or `unusable_or_missing`. A willingness
   explanation that treats earlier physical incapacity as preventing the
   now-stipulated ability contradicts the condition. An ability explanation
   that substitutes refusal/lack of effort for the stipulated effort also
   contradicts it. Declining despite being able, or failing despite trying,
   can be consistent. Generic text with no checkable basis is unclear.
   Keep the basis text and a reviewer note; no keyword auto-grader is used.
5. **Matched comparisons:** distinguish option-order disagreement, history
   order disagreement, notation sensitivity, wording sensitivity and
   exact-prompt changes since the previous run. A changed answer after a
   wording change is not itself an error. Each has one response per prompt
   in a fixed sequence; these are not independent scenario replications or
   a causal decomposition of prompt and generation variability.

**Stop after this one fixed batch and audit every outcome.** There is no
automatic extra replication, range expansion, protocol selection or pilot
dispatch. A desired LOW/HIGH or unable/unwilling ordering is not a passing
criterion: stable null or contrary patterns are valid research outcomes.
If the diagnostic remains uninformative or unstable, consider narrowing
the study to response robustness instead of continuing to adjust prompts
until a favored latent-valuation result appears. Any pilot decision must
address excluded cases and limitations, then explicitly freeze its design
before collection; this workflow cannot approve it.

## Artifacts and reproduction

The artifact includes `items.jsonl`, `protocol.json`, `git-revision.txt`,
`dependencies.txt`, `responses.jsonl`, its config, two rendered reports,
`responses.diagnostic.json`, `control-review.jsonl` and `binary-review.jsonl`.
The report compares the 80 exact anchors with the archived run when available;
historical replies are never sent to the API. Reports and raw artifacts are
uploaded on completion or failure when files exist.

```bash
uv sync --frozen --all-groups --extra eval
uv run --frozen python -m wtrbench.measurement_diagnostic generate
# Paid calls, only when deliberately running the fixed batch:
uv run --frozen python -m wtrbench.measurement_diagnostic run
uv run --frozen python -m wtrbench.measurement_diagnostic inspect runs/measurement-diagnostic/responses.jsonl
```

The API transport has zero retries and no fallback. An API exception stops
further requests; successfully returned records, including unusable outputs,
remain saved. A local `--resume` requires the exact configuration and skips
every recorded item, including invalid outputs. An unanswered request that
failed in transit may have reached the provider; resumption cannot guarantee
exactly-once remote processing. The manual workflow does not resume across
fresh GitHub runners: **re-running a job creates another paid batch**. If it
fails, share its link for diagnosis before clicking Run again.
