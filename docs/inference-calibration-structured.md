# Structured-answer response calibration

**Status:** Run [36085603717](calibration-36085603717-review.md) completed.
All answers parsed, but neither format passed the fixed progression criteria.
The specification below is retained as the pre-run protocol. For reproduction,
use Actions → Inference calibration (structured) → Run workflow → main, with
the existing `ANTHROPIC_API_KEY` secret. This is not a recommendation to rerun it.

This follow-up addresses the response-collection failures in
[calibration 36081054221](calibration-36081054221-review.md). It is exploratory
measurement development; the 888-item pilot remains paused, unfrozen and
unregistered.

## What will run

- Exactly 72 planned requests to `claude-sonnet-4-5-20250929`.
- The same 48 known-answer controls and 24 questions from six previously
  examined debug cases as the original calibration.
- The same histories, payoff amounts, truth keys, request order, A/B display
  order reversals, and A/B versus SAM/YOU label conditions.
- Fresh context per request; temperature 0; maximum output tokens **256**.
- A required JSON `answer` field, constrained by Anthropic's
  `output_config.format` API parameter. No explanation is requested.
- No full debug battery or pilot calls; no follow-up run starts automatically.

The protocol is `calibration-structured-v1`, with item hash
`ac2f89d22ce87380`. Each new item records its original calibration item ID;
social items also retain their original debug item ID. Only the reply
instruction at the end of each user prompt changes. System instructions
and the output protocol also change and are saved separately in the config.

The schemas are fixed in advance:

```json
{
  "type": "object",
  "properties": {"answer": {"type": "string", "enum": ["A", "B"]}},
  "required": ["answer"],
  "additionalProperties": false
}
```

The recipient condition substitutes `["SAM", "YOU"]` in that exact order.
Schema enum order is fixed, not independently counterbalanced; this run
does not estimate its effect. Both displayed option orders remain crossed
with both reply-label conditions. The API sees no truth key or scored result.

Anthropic's [structured-output documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
lists Sonnet 4.5 support and the `output_config.format` interface. Structured
outputs add a formatting instruction and constrain decoding. Format and
budget are therefore a joint protocol change, not an isolated label-token
or token-budget experiment. Valid JSON alone does not establish correct
reasoning, order stability, or psychological validity.

## Parsing, provenance and interrupted runs

Only a normally completed (`end_turn`) single text block containing a JSON
object with exactly one string `answer` field and a permitted label is usable.
Enum labels are case-normalized because the API documentation notes a casing
limitation. Duplicate keys, extra fields, explanatory prose, code fences,
unexpected content blocks and all truncated/refused outputs remain unusable,
even if an apparent answer can be found in them. No answer is recovered by
guessing from prose.

Each record retains the complete SDK response body (including all content
blocks), raw text, submitted request body without credentials, stop reason,
returned model, request ID, usage and decoded answer. The artifact also
includes prompts, protocol settings, source revision, dependencies, and a
report. Reports separate omitted requests from recorded unusable responses.

The SDK is configured with zero automatic retries. An API rejection stops
the batch; it does not fall back to an unconstrained prompt or another model.
The workflow uploads partial artifacts even after a failed API step. The
actual account-level availability is first exercised when this workflow is
run; the code is tested offline beforehand.

Each new GitHub workflow invocation starts a new batch. **Do not use Re-run
jobs to resume partial responses.** Download the artifact, use its saved
source revision, restore `responses.jsonl` and its `.config.json`, and use
the local `--resume` command. Every recorded response, including an unusable
one, is retained and skipped; only omitted items are requested. Config and
record checks reject changes to model, items, schema, system instruction,
budget, decoding or recorded request bodies. A network interruption may
leave a request processed by the service but unrecorded locally; local
resume cannot guarantee recovery of such a response.

## Interpretation fixed before these responses

Read known-answer completeness and accuracy first, separately by control
type, label condition and displayed option order. Investigate every error.
The report uses planned controls as the accuracy denominator and shows
missing and unusable counts separately. A truncated answer is not evidence
of an incorrect calculation.

A format is a **candidate for full debug**, not approved for the pilot, only
if all 24 controls are usable and correct and all six social option pairs
are complete and semantically consistent. The social cases have no correct
psychological answer assigned. This criterion is independent of the
unable/unwilling and LOW/HIGH theoretical orderings.

- If collection still fails, diagnose the saved response or API error before
  modifying the protocol. Retain the failed run.
- If collection succeeds but controls are wrong, accurate forced-choice
  prediction is not established.
- If controls pass but social pairs disagree, the target measure is still
  order-dependent under that protocol.
- If a format passes, inspect it on the full debug battery with a documented
  compatible implementation before assessing ladder coverage and deciding
  whether to freeze the pilot. If both pass, carry both into that comparison;
  do not choose based on the desired psychological direction.

The six cases reuse one boxes scenario and one numerical construction.
Option orders, rungs and reply formats are not independent scenario
replications. Stable answers can still be censored or follow a heuristic.
No conclusion about an internal shared variable, persistent memory, or
human-like concern follows from passing this calibration.

## Commands and cost

Generate items and configuration without API calls:

```bash
uv sync --frozen --all-groups --extra eval
uv run --frozen python -m wtrbench.structured_calibration generate
```

With the API key already supplied in the environment:

```bash
uv run --frozen python -m wtrbench.structured_calibration run
uv run --frozen python -m wtrbench.structured_calibration inspect runs/calibration-structured/responses.jsonl
```

For a restored partial run at its recorded source revision:

```bash
uv run --frozen python -m wtrbench.structured_calibration run --resume
```

The 256-token allowance is a maximum, not fixed billing. A completed batch
can generate at most 18,432 output tokens across its 72 requests; actual
usage and billed input depend on the replies and API formatting overhead.
The workflow uses the API account's normal billing. It includes an offline
request/scoring check before any paid calls. Model results should be
reviewed from the `inference-calibration-structured-...` artifact and job
summary, not from the green workflow status alone.
