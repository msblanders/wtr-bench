# Explicit-rule calculation diagnostic

**Ready to run: Actions → Inference calculation diagnostic → Run workflow →
branch main.** No inputs need changing. The existing `ANTHROPIC_API_KEY`
secret is used. Launch once and share the resulting run link for review.

This is a 24-request follow-up to
[structured calibration 36085603717](calibration-36085603717-review.md).
That run collected all answers, but A/B missed one underlying explicit-rule
case in both option orders, while SAM/YOU answered YOU on every rule case.
The present diagnostic asks whether returned calculations are wrong or the
final choices disagree with the returned calculations. It does not run the
social questions, full debug battery or 888-item pilot.

## Design fixed before execution

- Same model: `claude-sonnet-4-5-20250929`.
- All six original explicit-rule cases, including those previously answered
  correctly, crossed with both option orders and both A/B and SAM/YOU labels.
- 6 cases × 2 option orders × 2 reply-label formats = **24 requests**.
- Same rule wording, allocations and question stem, in their original order.
- Fresh context per request; temperature 0; maximum output tokens 256.
- Protocol: `calculation-diagnostic-v1`; item hash: `7306b8fde1e80015`.
- Required JSON fields, in schema order: numeric `option_a_value_to_sam`,
  numeric `option_b_value_to_sam`, then string `answer`.
- Answer enums remain `["A", "B"]` or `["SAM", "YOU"]`, in that order.
  Enum order and value-field order are fixed, not experimentally crossed.

The model is asked to calculate each displayed option's value to Sam using
the stated rule, then return the values and its final answer. This changes
the system instruction, response schema, and reply instruction at the end
of the user prompt. No worked example, expected value, truth key, prior
response, feedback, or demonstration is included in the API request.
Original calibration and structured-calibration IDs are retained locally.

Scoring uses these independently specified values. Displayed A/B values
reverse with option order; the correct recipient does not.

| Weight on your points | Sam's points if chosen | Your points if chosen | Value to Sam of own allocation | Value to Sam of your allocation | Correct recipient |
|---:|---:|---:|---:|---:|---|
| 0.5 | 2 | 10 | 2 | 5 | YOU |
| 0.5 | 8 | 10 | 8 | 5 | SAM |
| 1 | 5 | 10 | 5 | 10 | YOU |
| 1 | 20 | 10 | 20 | 10 | SAM |
| 2 | 10 | 10 | 10 | 20 | YOU |
| 2 | 40 | 10 | 40 | 20 | SAM |

The test suite independently extracts the primitive quantities and weights
from the prompt text and verifies the scoring values. Within each format,
the truth keys are balanced: six SAM and six YOU answers, including both
orders. There are six underlying problems, not 24 independent problems.

## Scoring and interpretation

Assess the following separately for each format and option order:

1. **Both values correct:** each returned A/B value equals its true value.
   All true values are exact integers; JSON `2` and `2.0` are equivalent.
2. **Final choice correct:** the decoded recipient matches the true rule.
3. **Final choice follows returned values:** the selected option has the
   larger of the two returned values, irrespective of their correctness.
4. **Reported tie:** returned values are equal. Ranking consistency is
   undetermined for ties, not counted as a success or failure. There are no
   ties in the true values.

The report includes planned-item denominators, missing versus unusable
responses, a joint table of calculation and choice correctness, semantic
option-order disagreement among complete pairs, and every planned response
with both true and returned values. Ranking-consistency denominators include
only usable, non-tied responses. Errors are not retried or discarded.

| Observed pattern | What it establishes within this task |
|---|---|
| Wrong values; choice follows their ranking | Returned calculations are wrong and the final choice is consistent with those erroneous values. |
| Correct values; wrong choice | The final choice contradicts the returned correct values. |
| Wrong values; correct choice | A correct final choice does not establish correct returned calculations. |
| Correct values; correct choice | The model succeeded on this explicitly scaffolded control. |

These are descriptions of outputs, not identified internal causes. The model
might produce a calculation after implicitly selecting a response; schema
field order is not evidence about neural processing order. Requiring values
also changes the task. Success does not retroactively validate the prior
answer-only protocol, prove the proposed social dissociation, or establish
an internal shared valuation variable.

No automatic progression decision is made. Review the whole pattern before
designing a compatible follow-up calibration. Full debug and pilot remain
paused, even if this control-only diagnostic succeeds.

## Collection safeguards and artifacts

Only a normally completed (`end_turn`) single text block containing exactly
the three required JSON fields is usable. Numeric fields must be finite
JSON numbers; booleans, strings, nulls, NaN/infinity, duplicates, missing or
extra fields, prose and code fences are rejected. Case-only differences in
answer enums are normalized, matching the prior structured protocol.
Truncated/refused responses remain unusable even if the text looks complete.
If any field fails validation, the entire response is unusable; raw evidence
is preserved for inspection.

The workflow runs offline tests before the paid requests. Each record keeps
the full SDK response body, raw text, exact submitted request body without
credentials, request ID, returned model, stop reason, usage, returned values
and decoded choice. Prompts, protocol configuration, source revision,
dependencies and reports are included in the downloadable artifact named
`inference-calculation-diagnostic-<run>-<attempt>`.

API errors stop the batch. Automatic SDK retries are disabled; there is no
fallback to another schema, unconstrained prompt, or model. Partial artifacts
are uploaded when possible. A green workflow status means execution
completed, not that the model passed the substantive checks.

## Local use and interrupted runs

Generate items without model calls:

```bash
uv sync --frozen --all-groups --extra eval
uv run --frozen python -m wtrbench.calculation_diagnostic generate
```

With the existing API key supplied in the environment:

```bash
uv run --frozen python -m wtrbench.calculation_diagnostic run
uv run --frozen python -m wtrbench.calculation_diagnostic inspect runs/calculation-diagnostic/responses.jsonl
```

Each new GitHub workflow invocation starts a new batch. To resume a partial
run, use its recorded source revision, restore `responses.jsonl` and its
`.jsonl.config.json` sidecar, then run:

```bash
uv run --frozen python -m wtrbench.calculation_diagnostic run --resume
```

Recorded responses, including unusable ones, are skipped. Configuration and
record checks reject mixed models, protocols, item sets, schemas or request
bodies. A network failure can leave a server-processed request without a
local response; resume cannot recover that unrecorded answer automatically.

The output allowance is a maximum, not a fixed charge. Across 24 completed
requests the maximum is 6,144 output tokens; actual usage is recorded.
Input and output are billed through the existing API account.
