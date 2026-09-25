# Running the inference pilot

**Pilot collection is paused at the researcher's request.** Focus first on
[validating the original measurement task](validation-before-pilot.md).
The original 888-item pilot is unrun. The 816-request robustness proposal is
retained but its collection job and CLI `run` command are disabled. No new
model calls are authorized by these instructions.

## Current offline validation work

```bash
uv run --frozen python -m wtrbench.validation_recovery
uv run --frozen pytest -q tests/test_validation_recovery.py
```

This creates a 216-request known-partner diagnostic draft and mathematical
checks under `runs/validation-recovery-draft/`. It makes no API calls and has
no collection workflow. See the plan for the gap in prior controls, the two
recovery arms, interpretation of original history bounds and the decision rule.

## Suspended robustness proposal: retained instructions

The material below documents the previous 816-request proposal. It is not a
current recommendation to run or resume it. The workflow is now named
**Inference robustness pilot (paused)** and skips collection even if manually
triggered. The CLI also stops before API-client creation. Its frozen plan and
manifest are preserved unchanged. Reopening any pilot requires a documented
measurement decision; a successful known-answer control alone is not complete
construct validation.

The sample contains six scenarios, two numerical sets, option and history
reversals, original/clarified binary questions and 48 total known controls.
The social source prompts were absent from archived development item files.
Incorrect controls, unusable answers and disagreements stay in the sample.
They do not stop collection or authorize additional calibration.

The artifact contains all planned items, the frozen plan/manifest, source
revision, dependencies, raw requests/responses, JSON summary, Markdown report,
pair records, per-order/per-pass ladder fits, control review and shuffled
condition-review template plus its separate metadata key.

## Review and technical interruptions

Read the raw responses and all 24 rule explanations, including both occurrences
of `rule_1_20` / Sam-second. A correct final answer does not prove a correct
calculation. Exact expected option values are in `responses.controls.jsonl`.

Copy `responses.condition-review-template.jsonl` to a separate file such as
`condition-labels.jsonl`. Code all 288 rows using the plan's four-category
rubric and supporting notes. Keep `review_id` and `response_digest` unchanged.
The template hides final choice and condition/pass metadata, but the actual
prompt reveals its wording; this is not fully blinded or independent coding.

```bash
uv run --frozen python -m wtrbench.robustness_pilot inspect runs/robustness-pilot/responses.jsonl --labels condition-labels.jsonl
```

The command rejects duplicate/unknown/stale labels, retains pending reviews,
and archives accepted labels alongside reports. Do not label a social yes/no
choice as correct merely because it matches a preferred theory. Preserve the
manual control-calculation audit separately, with supporting excerpts.

If the workflow stops on an API or integrity error, retain its partial artifact
and inspect the failure before any rerun. GitHub **Re-run jobs** starts a fresh
collection and would repeat calls; it is not a resume. The historical local
resume procedure uses the exact recorded revision and keeps the original
response JSONL and its `.jsonl.config.json` together. The command below is
currently blocked while pilot collection is paused. Document any uncertain
server-side completion after a transport failure first. Saved responses,
including unusable ones, are never automatically reissued.

```bash
uv run --frozen python -m wtrbench.robustness_pilot run --resume --out runs/robustness-pilot/responses.jsonl
```

The plan and ordered item JSONL are bound by
`protocols/response-robustness-pilot-v1.json`. Generate verifies the freeze and
writes local provenance without API calls:

```bash
uv run --frozen python -m wtrbench.robustness_pilot generate
```

The sections below preserve the original answer-only execution instructions.
They are historical reproduction procedures, not prerequisites or commands
for the current robustness pilot. Earlier calibration and diagnostic findings
remain part of the research record.

## Verify the installation

From the repository root, using Python 3.11 or later:

```bash
uv sync --frozen --all-groups --extra eval
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run python -m wtrbench.pilot synthetic
```

Version 0.4.2 keeps the v0.4.1 items and scoring. Following the first API debug,
requests now include a neutral A/B-only system instruction and a 64-token
output allowance instead of 4. These changes do not establish that a model
will obey the format. Prose remains unparsed even if it contains an answer.
API records now retain stop reason, returned model, request ID and token usage.
Inspection reports show answer-letter counts and use only complete pairs in
option-order disagreement denominators. Older records remain readable; absent
metadata is labeled as unrecorded. The tests include offline requests through
the installed SDK and protect against mixing response protocols on resume.

## Reproduce the earlier 196-item debug batch in GitHub

The following workflow retains the earlier answer-only protocol. It is not
the next run. The compatible explanation full-debug implementation was subsequently run
and audited; the calibration/range-tuning sequence is now complete.

1. Open the repository's **Settings → Secrets and variables → Actions**.
2. Add a repository secret named `ANTHROPIC_API_KEY` containing your Anthropic
   API key. Keep the key out of source files and messages.
3. Open **Actions → Inference debug → Run workflow**, using the committed
   revision and the default `claude-haiku-4-5-20251001` model.
4. Download the `inference-debug-…` artifact. It includes raw responses, the
   report, inspection output, item sets and hashes, the git revision, and
   dependency versions. Partial results are uploaded if the API run fails.

The Sonnet comparison using `claude-sonnet-4-5-20250929` is complete. Its
user prompts and request settings matched the second Haiku run, but the
valuation answers were strongly order-dependent. Retain all three runs.
The later explanation protocol made output collection usable, while
substantive calculation and social-response limitations remained. The existing API secret remains configured.

The manual workflow performs only the exploratory debug batch. A new workflow
execution starts a new run; it does not automatically resume an earlier
workflow's artifact. To resume an interrupted batch without repeating its
answered items, use the local procedure below with the downloaded files.

The model ID was checked against Anthropic's
[official model list](https://platform.claude.com/docs/en/models/overview).
Availability and billing depend on the API account; inspect any API error
before changing models.

## Run locally or resume an interrupted batch

Set `ANTHROPIC_API_KEY` in the local environment using your usual secret
management method, then run:

```bash
uv run python -m wtrbench.pilot debug claude-haiku-4-5-20251001
uv run python -m wtrbench.pilot inspect runs/debug_claude-haiku-4-5-20251001.jsonl
```

For a downloaded partial run, check out the saved git revision and restore its
JSONL file and matching `.jsonl.config.json` sidecar into `runs/`. Then:

```bash
uv run python -m wtrbench.pilot debug claude-haiku-4-5-20251001 --resume
```

Resume requires the same item set, model, generator settings, and request
settings. A recorded response with unparsed text remains recorded; it is not
silently retried until a preferred answer is obtained.

## Assess the debug batch

Read the inspection output and underlying responses. Check missing or unparsed
answers, agreement between option orders, agreement between evidence orders,
threshold violations, and whether the ladder supplies useful bounds.
Check API stop reasons for `max_tokens`, and check missingness separately by
family and option order. A threshold fit based on the surviving answers can
be misleading when format failures selectively remove one option order.

Unexpected psychological orderings are findings. Changes to the prompts,
range, or measurement should address a specified measurement problem, not
produce the predicted ordering. Document every such change and keep earlier
debug runs. Synthetic success does not guarantee that the real model follows
a threshold.

## Historical freeze procedure for the original 888-item design

Commit the chosen code and design. Record the source revision, exact model ID,
request settings, predictions, scoring rules, missing-response handling,
censoring and unresolved-fit handling, and intended comparisons. The
bootstrap summaries of midpoint differences do not include the uncertainty
within each threshold gap; inspect the interval-based comparisons as well.

Record the **888-item pilot hash**, not merely the debug hash. The GitHub
artifact contains both in `items-manifest.json`. To regenerate them locally
without making API calls:

```bash
uv run python - <<'PY'
from wtrbench.inference import DEBUG_TASKS, PILOT_LADDER, generate_inference_items
from wtrbench.run import items_hash
debug = generate_inference_items(ladder=PILOT_LADDER, tasks=DEBUG_TASKS, set_roles=("debug",))
pilot = generate_inference_items(ladder=PILOT_LADDER)
for name, items in (("debug", debug), ("pilot", pilot)):
    print(name, len(items), items_hash(items))
PY
git rev-parse HEAD
```

The item hash identifies generated user prompts. The system instruction and
output allowance are separate request settings, and must also be frozen in
the recorded source revision and run configuration.

If preregistering, register that specification and pilot hash before examining
pilot responses. Merely committing a design document is not an OSF
registration. If preregistration is skipped, describe the run as exploratory.
Repeating a study is possible; do not tune on observed pilot results and then
describe those same cases as an untouched test.

## Historical 888-item command (currently on hold)

```bash
uv run python -m wtrbench.pilot pilot claude-haiku-4-5-20251001
uv run python -m wtrbench.pilot inspect runs/pilot_claude-haiku-4-5-20251001.jsonl
```

Add `--resume` to the first command only when continuing that same interrupted
run. Save the JSONL, configuration sidecar, reports, revision and dependency
lockfile. Review both required comparisons within each scenario, including
undetermined cases; summarize their conjunction rather than treating either
comparison alone as the proposed dissociation.

A second model can be evaluated using the same frozen design after checking
API compatibility. Preserve and report the first model's results regardless
of whether they favor the hypothesis.
