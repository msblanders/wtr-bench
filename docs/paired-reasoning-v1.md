# Fixed reasoning extensions of the ordinal social pilot

Status: prospective follow-up specified after inspecting Sonnet run
[36216737006](https://github.com/msblanders/wtr-bench/actions/runs/36216737006)
and Qwen run [36278388351](https://github.com/msblanders/wtr-bench/actions/runs/36278388351),
before collecting either new condition. This is a response to the observed
non-replication, not an unplanned replacement for it. The Git commit and
`protocols/paired-reasoning-v1.json` freeze precede the new collection.
The six scenarios are reused, not newly held out for this follow-up.

## Launch once on GitHub

Use the existing repository Actions secret **DEEPINFRA_API_KEY** and a funded
DeepInfra account. Open **Actions → Paired reasoning extensions v1 → Run workflow**
on `main`, choose **collect**, and enter **COLLECT_290**. The default `generate`
is offline and needs no key. One dispatch starts both fixed conditions, regardless
of the other's results. Download both artifacts and retain the run link.

Each condition has one technical canary plus 144 social requests: at most **290
calls total**, including 288 social responses. The canary is described below.
There are no hidden pilot calls, automatic retries, output repairs, alternative
models or adaptive settings. Do not use Re-run jobs or dispatch another collection
of these conditions. A new dispatch cannot be prevented by a local output lock;
the researcher must keep this one-dispatch commitment. A failed technical or
transport attempt must be preserved and reviewed before a separately documented
future protocol. Do not replace partial data or a negative result.

This new follow-up does not reopen either completed protocol. All original source,
freezes, data and conclusions remain unchanged. GitHub CI and generation never
call an inference API. No paid call was used to develop the extension.

## What was already observed

Sonnet selected unable/tried on giving in 48/48 responses and able/refusing on
same-task ability in 46/48, with 2 D responses. Both net directions occurred in
all six scenarios; 46/48 matched forms had the predicted crossover.

Qwen3-14B with FP8, reasoning disabled, temperature 0, a 256-token cap and strict
JSON produced **144 valid, untruncated responses**. Thus output truncation was
not an observed explanation of the result. All 144 original responses remain
in the completed replication, including:

| Probe | Unable/tried | Able/refusing | Equal (C) | Insufficient (D) |
|---|---:|---:|---:|---:|
| Giving | 4 | 4 | 2 | 38 |
| Same-task ability | 6 | 4 | 0 | 38 |
| Different-task ability | 0 | 0 | 1 | 47 |

There were 0/48 predicted crossovers and 0/6 scenarios with both predicted signs.
Giving disagreements were 6/24 name, 10/24 order and 0/24 repeat; same-task ability
was 10/24, 10/24 and 0/24 respectively. Some explanations described the distinction
but failed to apply it consistently. These are limitations of this configuration's
elicited behavior, not evidence that Qwen lacks a representation of regard or ability.
The earlier 402 funding failure in run 36274679302 yielded no model answers.

Original artifact SHA-256:
`1261d195415cddc7562ac551abb2517f733e01fd05a8b5964c9d73309f4da83c`.
The earlier v3.2 known-answer validation was on Sonnet; it does not validate Qwen.

## Fixed conditions and rationale

| Condition | Served model | Reasoning request | Sampling | Total output cap |
|---|---|---|---|---:|
| 14b-thinking | Qwen/Qwen3-14B | high | temperature 0.6, top_p 0.95, top_k 20, min_p 0 | 32,768 |
| 32b-thinking | Qwen/Qwen3-32B | high | same | 32,768 |

Both use DeepInfra's OpenAI-compatible endpoint, FP8, one completion per request,
no streaming, and the original strict JSON schema. These are larger allowances,
not requirements to produce long answers. Provider reasoning tokens count as
output tokens. Each request has a 600-second timeout; each workflow job has a
six-hour limit. Timeouts leave an incomplete batch, with no automatic resumption.

The 32B model is a larger dense model from the same Qwen3 generation. It was
selected for current availability, structured output plus reasoning support,
and a closer comparison with 14B. It is not a 70B/235B substitute with equivalent
capacity. The catalog lists the original Qwen3-235B-A22B and its Thinking-2507
successor as deprecated/replaced. No model was selected by testing these items.
The prospective family has exactly two new conditions; no further models are
added conditional on their scores.

Qwen's model cards recommend temperature 0.6, top_p 0.95, top_k 20, min_p 0 and
adequate output length for thinking, and advise against greedy decoding. We use
those settings in both new conditions. The comparison with the previous 14B run
therefore changes **reasoning, sampling and output allowance together**. It does
not identify a causal effect of reasoning alone. The 14B/32B contrast also bundles
model size with learned weights; it is not a clean scaling law or a monotonic
capability gradient. FP8, hosting and strict JSON remain in place. A negative
follow-up still would not settle whether these factors constrain the behavior.

There is no fixed sampling seed. Both scheduled passes are retained. Name/order
mismatches now contain sampling variation as well as possible presentation effects;
they cannot all be attributed to presentation. Repeat disagreements are reported
alongside them, with no pseudoreplication across the six selected scenarios.

The catalog snapshot and upstream reference revisions are in
`protocols/paired-reasoning-v1-provider.json`. Reference revisions do **not** verify
the provider's weight bytes. At launch, a fresh catalog entry must match the model,
FP8, reasoning and structured-output tags, with no deprecation/replacement. The
runner preserves provider IDs and any fingerprint; observable changes stop the
batch. An absent fingerprint does not prove an unchanged backend.

At setup, 14B costs $0.12/$0.24 per million input/output tokens and 32B costs
$0.08/$0.28. At 145 calls per model, each reaching 32,768 output tokens, output
cost is about $1.14 + $1.33; roughly 80,000 input tokens per condition add $0.016.
Thus **about $2.50 total** is a conservative planning estimate at these prices,
not a billing guarantee or an account deposit minimum. Actual output may be much
shorter. Both social and canary usage/cost are reported separately and together;
missing provider usage remains unknown.

## Fixed stimuli and scoring

All 144 original social item objects, IDs, texts, order, names, repetitions,
three probes, and evidence clarifications are identical. Item stream SHA-256:
`8544ce8f81447f4074e21efa8b8af013409c11eba4940640765f03f608a1890e`.
No prompt requests social reasoning steps or supplies a hint about the hypothesis.
The API setting enables reasoning without adding `/think` to the prompt. The
system instruction and final `brief_basis` then `answer` schema are unchanged.
Every call starts a fresh conversation; neither canary nor earlier responses
appear in later contexts. Only the provider request wrapper/settings differ.

Separate `reasoning_content` or `reasoning` strings are preserved in the original
HTTP bytes. They do not enter answer scoring. Final content must independently
pass the original strict decoder: exactly the two fields in order, nonempty basis,
uppercase A/B/C/D. No stripping of inline think tags, markdown, field reordering,
letter inference from rationales, or repair is allowed. Truncated content is invalid
even if a plausible answer is present. C, D, invalid and missing remain distinct.
Social content invalids continue collection and never trigger a retry.

The original descriptive analysis applies: 18 scenario/probe cells, eight answers
per cell, pass splits, 48 matched crossovers, six scenario-level giving and
same-task ability nets, and all 216 overlapping name/order/repeat pair comparisons
with scheduled and comparable denominators. Net is (unable - unwilling) / 8,
including the full scheduled denominator. Giving should be positive and same-task
ability negative. Different-task ability remains exploratory because some tasks
blur skill and diligence; its wording is not repaired after inspection.

### Prospective outcome interpretation

Report the full distributions before the following descriptive cross-tab. For a
condition with all 96 primary answers valid and present:

- **D lower:** primary D count < 76, the old 14B count; report its magnitude too.
  A decrease of one response is descriptive, not evidence of a reliable change.
- **Six-scenario directional criterion met:** giving net > 0 AND same-task ability
  net < 0 within every one of the six scenarios. Also report all 48 crossovers;
  this criterion alone does not imply Sonnet-like strength or consistency.

Cross those two indicators, preserving all four outcomes: lower D with or without
the six-scenario pattern, and D not lower with or without that pattern. If any
primary answers are missing/invalid, report an uninterpretable-primary category
instead of letting failed output masquerade as reduced abstention. Report C and
wrong-direction choices separately: fewer D responses alone is not an improvement.
The third probe's D count is reported separately; total D is not the primary
abstention endpoint. No null-hypothesis tests, population generalization, scientific
PASS/FAIL label or post hoc success threshold is introduced.

Reasoning requested is distinguished from reasoning observed. Report the number
of social envelopes containing a separate nonempty reasoning string and all stop
reasons. Missing traces do not invalidate otherwise valid final answers, but
we cannot verify the thinking treatment on those items. This technical limitation
accompanies, rather than changes, the descriptive outcome category.

A positive result identifies a candidate open configuration for later study; it
does not show an internal WTR, the model's own preference, or a maintained valuation
variable. A mechanism study must reproduce behavior on its actual local checkpoint
and serving configuration before intervention. These two choices cannot establish
the *smallest* successful open model. A second negative result does not prove the
absence of the psychological distinction. Report both extensions and both earlier
models regardless of outcome, and treat this follow-up as motivated by prior data.

## One technical canary per condition

Before social collection, the runner sends one fixed arithmetic multiple-choice
prompt, asking for `(17 * 23 - 19 * 7) + 26` with options 284, 294, 304, 314, using
the identical request settings and final response schema. It is an API compatibility
check, not a psychometric validation or additional social scenario. Its exact body
is frozen and saved. Passing requires a successful, correctly identified envelope,
valid final JSON, and a nonempty separate reasoning string. **Arithmetic correctness
does not gate collection.** The answer and trace are preserved even on failure.

If the host suppresses reasoning under strict JSON, returns a malformed canary,
or rejects the settings, collection stops before the social items. There is no
fallback prompt, weaker schema or second canary. One absent trace cannot prove
the model never thinks; it means this fixed technical check failed. This boundary
is preferable to claiming a thinking manipulation we could not observe. Social
items themselves are not selected or excluded based on reasoning text or answers.

## Audit and offline reproduction

The new source freeze includes both earlier freezes and their complete source,
the new runner, tests, workflow, plan, provider snapshot and dependency lock.
The old freezes must still verify. Tests use programmed fixtures only. Each raw
HTTP response is saved, flushed and fsynced before parsing. Non-200 HTTP, invalid
envelopes, model/ID/fingerprint mismatches or canary failure produce an integrity
stop and no scientific summary. Transport failures preserve attempted requests,
received prefixes and unknown delivery status. All artifacts upload even on failure,
including complete source workflows, raw records, metadata, hashes and reports.
Credentials never appear in saved headers.

From an extracted condition artifact (Python 3.11+), substitute its condition:

```bash
sha256sum --check SHA256SUMS.txt
PYTHONPATH="$PWD/frozen-source/src" python -m wtrbench.paired.reasoning_extension check --condition 14b-thinking
PYTHONPATH="$PWD/frozen-source/src" python -m wtrbench.paired.reasoning_extension report --condition 14b-thinking --out "$PWD"
```

An offline generation artifact contains no model answers and should not be reported
as a collection. Neither configuration gets an automated explanation-content audit.
Generated reasoning and brief bases are reports, not direct evidence of computation.

## Primary setup references

- <https://huggingface.co/Qwen/Qwen3-14B>
- <https://huggingface.co/Qwen/Qwen3-32B>
- <https://deepinfra.com/Qwen/Qwen3-14B/api>
- <https://deepinfra.com/Qwen/Qwen3-32B/api>
- <https://api.deepinfra.com/models/list>
- <https://api.deepinfra.com/openapi.json>
- <https://docs.deepinfra.com/chat/reasoning>
- <https://docs.deepinfra.com/chat/structured-outputs>
