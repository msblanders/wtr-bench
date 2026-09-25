# Inference diagnostic runbook

**The payoff presentation diagnostic is complete and audited. No new run is
requested; both social pilots remain paused.** [Run 36115733552](https://github.com/msblanders/wtr-bench/actions/runs/36115733552)
returned 288 usable responses. Original wording scored 138/144 with 24/36
recovered fits; tables scored 139/144 with 28/36. The [audit](presentation-36115733552-review.md)
records paired gains/regressions, all explanation labels and the wrong
intervals that remain. Do not repeat this collection to seek a pass.

The [prospective plan](payoff-presentation-v1.md), [prompt examples](payoff-presentation-examples.md)
and original artifact files are unchanged. Verify the archive offline with:

```bash
python results/diagnostics/36115733552/audit/verify.py
```

## Payoff diagnostic: retained collection instructions

These are the historical instructions used for run 36115733552, not a request
to run again. The manual workflow remains available for reproduction.

1. Open **Actions → [Inference payoff presentation diagnostic](https://github.com/msblanders/wtr-bench/actions/workflows/inference-payoff-presentation.yml)**.
2. Click **Run workflow**, select **`main`**, and run **once**. There are no
   model, format or budget inputs. The existing `ANTHROPIC_API_KEY` secret
   is used and its account is billed for API usage.
3. Let the job collect **all 288 requests**: both presentations, both option
   orders, both history orders and two passes. Do not launch another job for
   pass 2. The model remains `claude-sonnet-4-5-20250929`, temperature 0,
   256 output tokens. The timeout is 60 minutes; progress logs every 12 replies.
4. Retain the artifact `inference-payoff-presentation-RUN_ID-ATTEMPT` and send
   the run link for review. It contains paired gains **and regressions**, all
   interval fits, order/repeat comparisons and the pending explanation packet.

This is a matched comparison with newly collected original requests; it does
not reuse old responses as its comparator or select previously failed items.
It makes 288 calls, versus 216 in the previous diagnostic, and table inputs
are longer. Output allocation is at most 73,728 tokens plus input usage;
this is not a dollar quote or a check of the account's remaining balance.
Preparation and verification make no model requests.

No SDK retries, fallback model, correctness-triggered stopping, extra batch or
pilot dispatch. Wrong and unusable responses remain in the data. A clear pass
on constructed controls alone does not release the original social pilot.

### Artifacts, labels and interruptions for this comparison

Items, plan, source revision, dependencies, freeze, raw request/API bodies,
reports, 72 overlapping fits, 576 pair records and review material are saved.
The programmed-oracle file is software verification, not model evidence.
Review all 288 explanations separately; correct choices can have faulty bases.
Copy the template to a separate labels file, retaining IDs and digests:

```bash
uv run --frozen python -m wtrbench.payoff_presentation inspect runs/payoff-presentation/responses.jsonl --labels explanation-labels.jsonl
```

Disclose the reviewer; assistant labels are not independent human coding.
Uncoded rows remain pending, and stale/duplicate/invalid labels are rejected.
Accepted labels are archived without overwriting the reviewer's file.

If a job fails, preserve its artifact and inspect the partial data first.
**Re-run jobs starts a new collection**, not a resume. An exact local resume
requires the original source, plan, response JSONL and `.jsonl.config.json`;
it skips saved responses including unusable ones. An unrecorded request may
have completed on the server and been billed before a transport failure.

```bash
uv run --frozen python -m wtrbench.payoff_presentation run --resume --out runs/payoff-presentation/responses.jsonl
```

Offline generation and targeted verification:

```bash
uv run --frozen python -m wtrbench.payoff_presentation generate
uv run --frozen pytest -q tests/test_payoff_presentation.py tests/test_recovery_run.py
```

`protocols/payoff-presentation-v1.json` binds exact prompts, bodies, plan and
source implementation. Do not edit frozen material after collection; record
findings in a separate audit. Do not rerun until a preferred result appears.

## Completed known-partner recovery diagnostic

**Run 36111049496 is complete and audited.**
Explicit weight: 72/72 correct, 18/18 recovered fits, all explanations
consistent. Choice history: 137/144 correct, six wrong, one truncated;
24/36 recovered fits. All 216 explanations were reviewed separately.
See the [audit, preserved evidence and next-step rationale](recovery-36111049496-review.md).
The frozen clear-pass rule was not met. Do not repeat that batch to seek a
preferred result. The completed matched display test is described above.

## Completed diagnostic: retained collection instructions

These are the historical instructions used for run 36111049496, not a request
to run it again. The [validation-before-pilot plan](validation-before-pilot.md)
and [frozen collection rules](known-partner-recovery-v1.md) remain in the record.

1. Open **Actions → [Inference recovery diagnostic](https://github.com/msblanders/wtr-bench/actions/workflows/inference-recovery-diagnostic.yml)**.
2. Click **Run workflow**, select **`main`**, then run **once**. There are no
   model, budget or format inputs to change. The existing `ANTHROPIC_API_KEY`
   repository secret is used and its account is billed for API usage.
3. Let the same job finish both passes: **216 requests total**, comprising
   72 explicit-weight and 144 choice-history questions. The model is
   `claude-sonnet-4-5-20250929`, temperature 0, maximum 256 output tokens.
   The job has a 45-minute operational timeout and logs progress every 12
   recorded responses. Do not launch another job for the second pass.
4. Download `inference-recovery-diagnostic-RUN_ID-ATTEMPT` and retain it.
   Send the run link for analysis. The summary reports final-choice accuracy,
   interval recovery, and option/history/repeat comparisons. Explanation
   review remains explicitly pending until the outputs are audited.

The run makes every planned request despite incorrect or unusable answers.
There are no automatic retries, outcome-driven extra calls or pilot dispatches.
The 816-request robustness workflow remains disabled, and the original
888-item social pilot remains on hold. Do not rerun to seek a preferred result.

## Artifacts and explanation review

The artifact contains `items.jsonl`, protocol, plan, freeze manifest, source
revision, dependencies, raw `responses.jsonl` with exact request/API bodies,
summary/report, all 54 fits, pair records and an explanation review template.
`programmed-oracle-check.json` is separately labeled software verification,
not a model observation. The historical bound audit is also included.

Review all returned bases for calculations, mapping and inference. In the
explicit-weight condition, the template supplies exact option values. In the
history condition it supplies feasible intervals; the hidden generating
weight is not the only compatible inference. Correct final choices and
correct explanations are separate outcomes. Follow the frozen rubric and
disclose the reviewer; assistant coding is not independent human coding.

Copy `responses.explanation-review-template.jsonl` to a separate labels file,
enter allowed labels and notes, and keep review IDs/response digests unchanged:

```bash
uv run --frozen python -m wtrbench.validation_recovery inspect runs/validation-recovery/responses.jsonl --labels explanation-labels.jsonl
```

Partial labels remain pending. Accepted labels are archived alongside reports;
the reviewer's file is not overwritten. The report never treats a choice pass
as automatic approval of the original social measure or a pilot.

## Technical interruptions and offline checks

If collection fails, keep the partial artifact and inspect its logs first.
GitHub **Re-run jobs** starts a fresh collection and does not resume saved
responses. An exact local resume requires the recorded source revision,
original response JSONL and its `.jsonl.config.json` together. Saved replies,
including unusable ones, are not reissued. Document any uncertainty about a
server-side completion after a transport error before resuming.

```bash
uv run --frozen python -m wtrbench.validation_recovery run --resume --out runs/validation-recovery/responses.jsonl
```

To generate the reviewable prompts and verify the freeze without API calls:

```bash
uv run --frozen python -m wtrbench.validation_recovery generate
uv run --frozen pytest -q tests/test_validation_recovery.py tests/test_recovery_run.py
```

The collection manifest is `protocols/known-partner-recovery-v1.json`. It binds
the ordered item JSONL, request bodies/settings and frozen analysis plan. Do
not edit the frozen plan after observing responses; add a separate audit.

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
