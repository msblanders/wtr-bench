# Running the inference pilot

The code is ready for an exploratory API debug batch. Synthetic outputs are
programmed checks, not observations of an LLM. The study has not been
preregistered and no real-model results accompany this installation.

## Verify the installation

From the repository root, using Python 3.11 or later:

```bash
uv sync --frozen --all-groups --extra eval
uv run pytest -q
uv run ruff check .
uv run mypy src
uv run python -m wtrbench.pilot synthetic
```

This installation includes v0.4.1 plus three integration fixes: JSON-normalized
resume settings and separate inspection rows for both aggregate evidence
orders, plus compatibility with the installed Anthropic SDK. Haiku 4.5's
temperature setting is sent through the SDK's `extra_body` parameter.
Request settings are saved in each run configuration. The additional
regression tests cover those integration fixes, including an offline HTTP
request through the real SDK.

## Run the 196-item debug batch in GitHub

1. Open the repository's **Settings → Secrets and variables → Actions**.
2. Add a repository secret named `ANTHROPIC_API_KEY` containing your Anthropic
   API key. Keep the key out of source files and messages.
3. Open **Actions → Inference debug → Run workflow**, using the committed
   revision and the default `claude-haiku-4-5-20251001` model.
4. Download the `inference-debug-…` artifact. It includes raw responses, the
   report, inspection output, item sets and hashes, the git revision, and
   dependency versions. Partial results are uploaded if the API run fails.

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

Unexpected psychological orderings are findings. Changes to the prompts,
range, or measurement should address a specified measurement problem, not
produce the predicted ordering. Document every such change and keep earlier
debug runs. Synthetic success does not guarantee that the real model follows
a threshold.

## Freeze before the pilot

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

If preregistering, register that specification and pilot hash before examining
pilot responses. Merely committing a design document is not an OSF
registration. If preregistration is skipped, describe the run as exploratory.
Repeating a study is possible; do not tune on observed pilot results and then
describe those same cases as an untouched test.

## Run the 888-item pilot after the freeze

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
