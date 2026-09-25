# Brief-explanation response calibration

**Status:** Implemented in v0.4.6 and ready for a manual run; no model
responses collected under this protocol yet. Open
[Actions → Inference calibration (explanation)](https://github.com/msblanders/wtr-bench/actions/workflows/inference-calibration-explanation.yml),
choose **Run workflow → main**, and click the green **Run workflow** button
once. There are no model or budget inputs to choose. The existing repository
`ANTHROPIC_API_KEY` secret is used.

This returns to the original 72-question calibration after the
[24-request calculation diagnostic](calculation-36087344540-review.md)
returned correct values and choices throughout. The aim is to check whether
one brief-explanation-plus-answer protocol supports accurate controls and
stable social predictions. The full debug battery and 888-item pilot remain
paused; the pilot is unrun, unfrozen and unregistered.

## Fixed design and request settings

Exactly 72 requests are planned to `claude-sonnet-4-5-20250929`, one response
per item in fresh context, temperature 0, maximum output tokens **256**.

| Item family | A/B requests | SAM/YOU requests | Total |
|---|---:|---:|---:|
| Recipient lookup | 8 | 8 | 16 |
| Quantity comparison | 4 | 4 | 8 |
| Explicit numerical rule | 12 | 12 | 24 |
| Existing social debug judgments | 12 | 12 | 24 |
| Total | 36 | 36 | 72 |

Each case appears with Sam's option first and second, in both reply-label
conditions. The original stems, histories, payoff amounts, known-answer
control keys, six social cases and request sequence remain unchanged.
Only the user prompt's final reply instruction changes; the system
instruction and output schema also change. The model, temperature and
256-token allowance match the two most recent runs.

Protocol: `calibration-explanation-v1`; item hash: `838b96effb3ab30c`.
New item IDs retain a link to the original calibration item ID (original
hash `299094bf02c5a1d1`); social items also retain their source debug item ID.
The previous answer-only structured calibration hash is `ac2f89d22ce87380`.
Earlier protocols and saved results remain reproducible.

## Uniform brief explanation, then final answer

Every family receives this ending in the A/B condition:

> Return a JSON object with exactly two fields in this order: "brief_basis", a brief explanation (one or two sentences) for your answer using the supplied information; then "answer", whose value is A or B. Do not include other fields.

The recipient condition substitutes **SAM or YOU, naming the recipient in
the selected option** for **A or B**. The system instruction is
`For each question, ` followed by the same ending. No worked example,
expected answer, requested social ordering or scored result is sent.

The API-enforced schema is:

```json
{
  "type": "object",
  "properties": {
    "brief_basis": {"type": "string"},
    "answer": {"type": "string", "enum": ["A", "B"]}
  },
  "required": ["brief_basis", "answer"],
  "additionalProperties": false
}
```

The recipient condition uses `["SAM", "YOU"]`, in that order. Both fields
are required, with the explanation first in the schema and instructions.
Enum order is fixed, not independently counterbalanced. The API parameter
is `output_config.format`, as in the completed structured runs. See
Anthropic's [structured-output documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs).

**No numerical valuations or inferred utility coefficients are required
for social questions.** Those prompts do not supply a known weight; requiring
one would impose the representation this behavioral study aims to investigate.
A model may spontaneously use numbers in its explanation. That output is
preserved, not treated as an independently validated WTR estimate.

The returned explanation is observable generated text, not access to internal
reasoning. Its presence or field order does not establish a neural processing
sequence. This is a new elicitation protocol, not a clean isolation of the
cause of earlier errors. Explanations receive no automated correctness or
mechanism score, and no social judgment receives a psychological truth key.

## Parsing and scoring fixed before responses

A usable response must end normally (`end_turn`) and contain a single text
block with exactly two JSON fields in the specified order: a nonempty string
`brief_basis`, then a string `answer` with an allowed label. Answer labels
are case-normalized; surrounding spaces are not stripped. A one- or
two-sentence explanation is requested, but sentence count is not a parsing
criterion. Decimal points and abbreviations are not sentence-count errors.

Malformed JSON, duplicate/missing/extra fields, empty or whitespace-only
explanations, reversed field order, unexpected content blocks and non-normal
completion are unusable. A truncated response remains unusable even when
its JSON looks complete. Raw text and all SDK content blocks are retained.
Only the explicit final-answer field determines the scored choice; labels
inside the explanation cannot supply, override or rescue an answer.

Review known-answer completeness and accuracy first, by control family,
reply-label format and displayed option order. Missing and unusable responses
remain in the planned accuracy denominator and are also counted separately.
Semantic option-order agreement is computed only for pairs with two usable
answers; incomplete pairs remain visible and cannot pass the gate.

The progression criterion is unchanged, separately for each reply format:
**all 24 controls usable and correct, plus all six social pairs complete and
semantically consistent**. This makes a format a candidate for a compatible
full debug battery, not approved for the pilot. If both pass, carry both
into that comparison. Never select a format because it produces the favored
unable/unwilling or LOW/HIGH ordering. If neither passes, diagnose the saved
outputs and retain the run before modifying the protocol.

These six social cases reuse one boxes scenario and one numerical
construction; reversals and reply formats are not independent scenario
replications. Passing this small calibration does not establish ladder
coverage, threshold behavior, the social dissociation or a shared internal
variable. A compatible full debug battery must assess censoring, monotonicity
and remaining order effects before any pilot freeze. No next batch starts
automatically.

## Saved records and interrupted runs

The `inference-calibration-explanation-<run_id>-<attempt>` artifact contains
prompts, protocol settings, source revision, dependency versions, raw JSONL
responses, a configuration sidecar and reports. Each response saves the
request body without credentials, complete SDK response body, raw text,
stop reason, returned model, API request ID, usage, explanation and decoded
answer. Unusable responses retain their raw content even when decoded fields
are null. The job summary reports completeness, accuracy and pair agreement.
A green workflow status means execution completed, not that the calibration
passed its progression criterion.

Offline request/scoring tests run before paid calls. There are no automatic
SDK retries, model switches or unconstrained fallbacks. An API error stops
the batch; partial artifacts are uploaded even after failure.

Every new GitHub workflow invocation starts a new batch. **Re-run jobs does
not resume partial responses.** To continue an interrupted run, download its
artifact, check out the recorded source revision and restore `responses.jsonl`
and `responses.jsonl.config.json` under `runs/calibration-explanation/`.
Then use the local `--resume` command below. Every recorded response, including
unusable output, is retained and skipped. Configuration and record checks
reject a different item set, model, output protocol or request settings.
A network interruption can leave a service-side response unrecorded locally;
resume cannot recover such a response automatically.

## Local commands

Generate prompts and configuration without API calls:

```bash
uv sync --frozen --all-groups --extra eval
uv run --frozen python -m wtrbench.explanation_calibration generate
```

With the API key already supplied in the environment:

```bash
uv run --frozen python -m wtrbench.explanation_calibration run
uv run --frozen python -m wtrbench.explanation_calibration inspect runs/calibration-explanation/responses.jsonl
```

For a restored partial run at its recorded source revision:

```bash
uv run --frozen python -m wtrbench.explanation_calibration run --resume
```

A completed batch has at most 18,432 generated output tokens (72 × 256),
plus billed input and any API formatting overhead. The allowance is a ceiling,
not fixed usage or a price estimate. Review the saved model outputs and
usage after the run. Do not launch the older calculation-only or answer-only
workflows as the next diagnostic.
