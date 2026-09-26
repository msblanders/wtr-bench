# Fixed second-model replication: Qwen3-14B

Status: prospective second-model plan, fixed after the Sonnet pilot was observed
and before any Qwen social responses. One collection, 144 requests. Report both
models regardless of outcome. This is not a new instrument or a search for a
model that reproduces the desired result.

## Launch on GitHub

1. Create a DeepInfra API key in your own account and add credit if required.
   Store the key as repository Actions secret **`DEEPINFRA_API_KEY`** under
   Settings → Secrets and variables → Actions → New repository secret.
2. Open Actions → **Paired open-model replication v1** → Run workflow on `main`.
   `generate` is the offline default and needs no key. For the one paid batch,
   choose **`collect`** and enter **`COLLECT_144`**.
3. Save the artifact `paired-open-v1-RUN_ID-1`, including its checksums and raw
   records. The run summary shows the descriptive tables. Send the run link
   for the comparison with Sonnet.

Do not use **Re-run jobs** or start another collection to fix an unwanted result.
The CLI refuses a repeated GitHub attempt or an existing started output directory.
A new workflow dispatch has a fresh directory, so the researcher must also avoid
starting a second dispatch. A transport/integrity failure requires review of the
preserved artifact before a separately documented decision about further work.
A timeout can mean the provider processed a request whose response was not received.

Only `run --confirm 144` makes model calls. CI and `check`, `generate`, `report`
use no model API. Collection also makes one unauthenticated catalog lookup.
No local GPU, Hugging Face token, Anthropic key or new Python package is required.
The key appears only in the collection step's environment, never in artifacts.

## Model selection and scope

- Provider: DeepInfra; endpoint `https://api.deepinfra.com/v1/openai/chat/completions`.
- Fixed served model ID: **`Qwen/Qwen3-14B`**, catalog precision **FP8**.
- Open upstream weights: <https://huggingface.co/Qwen/Qwen3-14B>, Apache 2.0;
  dense 14.8B parameters. This is a manageable candidate for a later local
  intervention study, although this hosted behavioral run exposes no activations.
- Setup-date upstream repository revision:
  `40c069824f4251a91eefaf281ebe4c544efd3e18`.
  This is a reference for future local work, **not verification that DeepInfra
  serves those exact bytes**. The hosted endpoint does not expose a pinned weight
  revision or tokenizer/serving-stack revision. Do not describe this as a
  bit-reproducible checkpoint experiment.
- The earlier Qwen3-8B suggestion was not listed in the checked host catalog.
  Qwen3-14B was selected for availability, open weights and structured-output
  support, without testing either model on these social items.

The setup catalog entry is committed in `protocols/paired-open-v1-provider.json`.
At collection the runner saves a fresh entry and requires the exact model,
FP8, structured-output/non-reasoning tags, and no deprecation or replacement.
It stops on a returned-model mismatch or a change in any supplied
`system_fingerprint`, including appearance/disappearance. Absence of a fingerprint
is recorded and is not proof that the backend stayed identical. These checks
reduce observable drift; they cannot verify undisclosed provider changes.

Prices checked 2026-09-26: $0.12 per million input tokens and $0.24 per million
output tokens. At roughly 80,000 input tokens and at most 36,864 output tokens,
144 calls would cost about **$0.02** at these rates; tokenizers and prices can
differ, and account minimum deposits are separate. The artifact reports the
provider's actual usage and estimated cost when supplied, otherwise unknown.

Primary references checked at setup:

- Model/API and pricing: <https://deepinfra.com/Qwen/Qwen3-14B/api>
- Catalog: <https://api.deepinfra.com/models/list>
- Structured output: <https://docs.deepinfra.com/chat/structured-outputs>
- Reasoning switch: <https://docs.deepinfra.com/chat/reasoning>
- Upstream model/modes: <https://huggingface.co/Qwen/Qwen3-14B>

## What is identical, and what changes

The baseline is commit `ff507473ff7fcdd229f7f8c7e23a52fb7b24a605` and Sonnet
run [36216737006](https://github.com/msblanders/wtr-bench/actions/runs/36216737006).
The original pilot freeze, source, workflow, scenario pack and analysis plan
remain unchanged. `social.verify_freeze()` must pass before any replication work.

All **144 original item objects**, IDs, texts, maps, schedule positions, two passes,
three probes, name assignments and display orders are identical. The item stream
SHA-256 remains
`8544ce8f81447f4074e21efa8b8af013409c11eba4940640765f03f608a1890e`.
The two evidence clarifications about separate occasions and persistent knowledge
and limitations remain. There is no change to the mixed different-task questions.

The system instruction and two-field schema are identical. Each request contains
one system message and one user message, no conversation history, examples or
correctness labels. Temperature remains **0**; maximum output remains **256**
provider tokens. The host's tokenizer and chat template differ. We set
`reasoning_effort: "none"`, `stream: false`, `n: 1`, and translate Anthropic's
schema wrapper to DeepInfra's `response_format.json_schema` with `strict: true`.
Other sampling settings use host defaults, as they did in the first pilot;
we do not claim those defaults or schema constraints are identical across hosts.
The request stream therefore has its own hash and freeze.

Qwen recommends sampled settings for non-thinking use; this replication retains
temperature zero for continuity with Sonnet. It evaluates this fixed configuration,
not the best attainable performance of Qwen or of open-weight models generally.
No setting, schema fallback, model fallback, token budget or prompt is adjusted
based on pilot outputs. The reasoning control is supplied through the API, without
adding `/no_think` to the frozen prompt.

## Scoring and interpretation fixed before collection

The original [analysis plan](paired-pilot-v1.md) applies. The descriptive prediction
is more unable/tried selections on future giving and more able/refusing selections
on same-task ability, within each scenario. Both signs matter; a positive difference
alone is insufficient. Report all 18 scenario/probe cells, all eight answers per
cell, pass splits, 48 matched crossovers, and name/order/repeat disagreement counts
with their comparable and scheduled denominators. Do not replace this with a
pooled success rate. Six scenarios remain six scenarios, not 144 independent cases.

The scoring adapter maps a single successful assistant text completion to the
original strict decoder. It does not change model identity or fabricate Anthropic
provenance. Valid answers require exactly `brief_basis` then `answer`, a nonempty
basis and uppercase A/B/C/D. No duplicate fields, markdown stripping, key reordering,
answer repair from explanations or substitution of reasoning text is permitted.
Truncation, tool use, refusal, nonempty separate reasoning, malformed content and
incorrect field order are invalid and retained. C, D, invalid and missing stay
separate. Content-format invalids do not trigger a retry or end collection.

Non-200 HTTP responses, an unparseable response envelope, wrong model, duplicate
message/request IDs, or changed provider fingerprint stop collection after saving
the offending raw bytes. These are integrity failures, not social answers; the
offline reporter writes `integrity-report.json` and refuses a scientific summary.
Transport failures preserve the recorded prefix and attempted request; that prefix
can be reported with the remaining scheduled responses marked missing. A complete
batch can contain invalid answers and is never labeled scientific PASS/FAIL.

This is **144 social requests only**. The existing v3.2 known-answer validation was
run on Sonnet; it is not automatically validation on Qwen. No extra control batch,
control-based exclusion, or adaptive selection is included here. A weaker result
would leave task/format comprehension among the explanations; it would not prove
absence of social inference or an open-versus-closed model difference. A positive
result would extend this behavioral dissociation to a second model/configuration,
not establish a scalar WTR, the model's own preferences, or an internal valuation
variable. Hosted quantization and prompt processing limit model-only comparisons.

The prior different-task ambiguity, dog abstention, and all contrary or ambiguous
Qwen responses must remain visible in the write-up. Rationales are generated text,
not direct access to computation. This scorer does not review their content.
Publish the two-model comparison even if the prediction fails or the batch stops;
label incomplete or uninterpretable collection accurately.

## Preservation and offline reproduction

The new freeze binds the adapter, copied scoring function, original frozen sources,
workflow, analysis plan, provider snapshot, tests and dependency lock. Scoring code
is copied from the frozen pilot because changing that pilot would invalidate its
collected source freeze. Tests verify semantic scoring equivalence and validate
transport error preservation with programmed fixtures, never empirical model data.

Artifacts contain `items.jsonl`, model-specific `requests.jsonl`, `freeze.json`,
`collection-started.json`, `provider-preflight.json`, exact response bytes encoded
in `responses.jsonl`, descriptive reports, answer CSV, pair audit, environment
versions and a complete `frozen-source/` snapshot. The upload explicitly includes
the snapshot's `.github` workflow files; the first pilot's upload had omitted that
hidden directory. Auth headers are never recorded. HTTP inference redirects and
automatic retries are disabled. The raw response is flushed before validation.

After extracting an artifact, run from its directory (using Python 3.11 or newer):

```bash
sha256sum --check SHA256SUMS.txt
PYTHONPATH="$PWD/frozen-source/src" python -m wtrbench.paired.open_replication check
PYTHONPATH="$PWD/frozen-source/src" python -m wtrbench.paired.open_replication report --out "$PWD"
```

The generated files alone do not contain model data. An offline `generate` artifact
has no collection metadata and should not be passed to `report`. A failed integrity
report is an audit outcome, not a reason to modify the freeze and recollect.
