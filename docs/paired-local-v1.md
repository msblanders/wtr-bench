# Pinned local checkpoint bridge: paired-local-v1

Status: prospective implementation; no Qwen3-32B local responses collected during development.
This is a portability/eligibility check before activation experiments, not the mechanism study.
The [behavioral note](research-note-v1.md) reports existing results; the
[mechanism proposal](irv-mechanism-proposal-v0.2.md) specifies the subsequent research.

## Question and fixed decision

Does a pinned, inspectable Qwen3-32B checkpoint reproduce the two primary directional
judgments seen in hosted run [36281301593](https://github.com/msblanders/wtr-bench/actions/runs/36281301593)?
There is one condition, one technical canary, and one pass through the original 144-item
schedule (including its two repetitions). No hyperparameter sweep, replacement model,
response repair, or result-contingent rerun is part of this protocol.

A complete, valid primary result is classified descriptively as:

1. **Primary pattern reproduced:** all 96 primary responses valid; each of six scenarios has
   positive unable-minus-unwilling net giving and negative same-task ability net.
2. **Primary pattern not reproduced:** all 96 primary responses valid; that six-scenario
   criterion is not met. Report abstention, equality and reversals separately.
3. **Incomplete or invalid primary:** any primary response missing or invalid. Retain and
   describe the technical/format failure; do not turn missing answers into abstentions.

This is an eligibility convention, not a significance test or accuracy threshold. Report
all counts, 48 matched crossovers, all 18 scenario/probe cells, pass splits and name/order/repeat
disagreements, regardless of category. Do not require equality with the hosted answer vector.
The different-task probe remains exploratory and cannot select the checkpoint. Six selected
scenarios are the substantive units; 144 responses are not 144 independent replications.

## What stays fixed and what changes

The item stream has SHA-256
`8544ce8f81447f4074e21efa8b8af013409c11eba4940640765f03f608a1890e`.
All original user/system messages, names, order, probes, evidence clarifications, final JSON
schema, scoring and presentation audits are reused. The one arithmetic canary is the same
as in the thinking extensions. Its arithmetic correctness does not gate collection.
It must produce nonempty thinking followed by valid final JSON before social items begin.

| Setting | Hosted 32B thinking | This local bridge |
|---|---|---|
| Model | DeepInfra Qwen/Qwen3-32B | Official Qwen/Qwen3-32B weights |
| Weight revision | Provider did not expose it | `9216db5781bf21249d130ec9da846c4624c16137` |
| Precision | Provider-reported FP8 | BF16, no quantization/offload |
| Reasoning | `reasoning_effort=high` | Official template `enable_thinking=True` |
| Sampling | temperature .6, top-p .95, top-k 20, min-p 0 | Same |
| Total output cap | 32,768 | 32,768, thinking plus final together |
| Seed | Not supplied | Canary 26092700; social item i uses 26092700+i (i=1…144) |
| Final format | Provider structured output | XGrammar after generated `</think>` token |
| Engine | Provider not fully specified | Transformers 4.56.2, PyTorch 2.8.0, SDPA, one GPU |

These are material implementation differences. This is not a bit-identical replay, a pure
precision experiment, or evidence that the provider served exactly this revision.
BF16 is selected to make the checkpoint directly usable with ordinary PyTorch activation
hooks later. Do not silently substitute a 4-bit/GGUF/MLX version or another model.

## Machine and launch instructions

Use **Linux x86_64, one otherwise idle 80 GB NVIDIA GPU with BF16 support** (e.g. A100 80 GB
or H100 80 GB), at least 32 GB host RAM (64 GB preferred), and 150 GB free persistent disk.
An ordinary laptop or GitHub's standard hosted runner is not the target. A rented GPU
machine under your control counts as local checkpoint execution. No DeepInfra key is needed.

Weights contain 65,524,246,528 bytes (~61 GiB), plus tokenizer/config files. A full 32,768-token
BF16 KV cache is roughly 8 GiB, before prompt cache and runtime overhead. The doctor requires
74 GiB free VRAM. These are planning estimates, not a completed 80 GB load test. The runtime
can still expose driver/kernel/memory issues; preserve the failure record if that occurs.
The lock installs CUDA runtime libraries; the machine needs a compatible NVIDIA driver
and an otherwise working PyTorch 2.8 CUDA setup. No CUDA toolkit build is required by this
runner. Download and hashing time are additional to inference time.

On that machine, install git and [uv](https://docs.astral.sh/uv/getting-started/installation/),
then run from a terminal (preferably inside `tmux` so disconnecting does not stop the run):

```bash
git clone https://github.com/msblanders/wtr-bench.git
cd wtr-bench
git checkout local-checkpoint-v1
bash experiments/local-checkpoint/run.sh setup
bash experiments/local-checkpoint/run.sh download
bash experiments/local-checkpoint/run.sh run --confirm 145
bash experiments/local-checkpoint/run.sh package
```

Use the published commit for this protocol and retain it with the results. `check` verifies
source hashes, so a modified runner fails closed. `setup` installs only the separate, locked
GPU environment and runs the hardware doctor; it does not generate answers. `download`
retrieves ~65.5 GB of checkpoint files and verifies SHA-256 for every required file; it does
not generate answers. `run` rechecks file hashes, loads the model once, runs the recorded
canary, then all social items in order. No automatic retries, fallback model or collection resume.
The runner prints progress every 12 social responses. No paid API requests are made.
GPU rental, if used, is billed by your chosen host while the machine is running.

The default locations are:

- `runs/checkpoint-cache/`: downloaded weights, reusable for the mechanism project.
- `runs/paired-local-v1/`: response records, exact inputs and output token IDs, checkpoint and
  source manifest, runtime identity, reports and audit CSV. Keep this directory even on failure.
- `runs/paired-local-v1.zip`: portable result bundle produced by `package`; excludes weights.

Download the ZIP before terminating a rented machine. Stop the rented GPU after collecting
and exporting the results. Upload the ZIP for review; do not paste the entire token log.
A different cache/output path can be supplied with `--cache` / `--out` consistently across
commands. Reusing an output folder is refused. A technical failure is not permission to rerun
until a positive result: diagnose it and record any amended configuration prospectively.

If a run fails after starting, these commands still produce a partial/failure report and ZIP:

```bash
bash experiments/local-checkpoint/run.sh report
bash experiments/local-checkpoint/run.sh package
```

A killed process or damaged partial JSONL line can require audit/recovery before packaging;
never discard or hand-edit the raw file to make the report pass. There is no automatic upload
or infrastructure creation in this package.

## Parsing, provenance and limitations

The pinned official template opens the assistant turn; the model generates its own thinking
tags. The parser requires one generated opening `<think>` token at the start and one closing
`</think>` token, with nonempty reasoning between them. One ordinary `generate()` call allows
unconstrained thinking; after the generated separator token 151668, a fresh XGrammar
processor restricts the remaining output to the original schema. No extra final-answer
prompt is inserted. Sampling and the combined token allowance apply to the entire generation.
Only the final JSON is scored. The strict original decoder requires a nonempty `brief_basis`
then one A/B/C/D answer, no extra/duplicate keys or repairs. C (equality), D (insufficient),
invalid and missing remain different categories. Social invalid responses are retained and
collection continues; a canary format failure stops before social collection.

The raw token stream, decoded raw text, parsed sections, rendered input, per-item seed,
wall time and CUDA memory peaks are stored. Responses are flushed and fsynced before parsing.
Full required checkpoint file hashes, source hashes, pinned dependency lock and runtime
hardware/software identity travel with the bundle. SHA-256 detects accidental alteration;
it is not an independent attestation of how a third party executed a run.

Repeat disagreements at temperature .6 include sampling variation; name/order disagreements
also include sampling variation and cannot isolate causal presentation effects. Fixed seeds
improve traceability, not guaranteed bitwise reproducibility across hardware/kernel stacks.
Known-answer validation conducted on Sonnet does not establish local Qwen's validity on all
other constructs. A successful bridge is a candidate-selection result, not proof of maintained
relational valuation, an estimated WTR magnitude, or the model's own preferences.

## Engineering verification

The ordinary repository tests exercise the fixed schedule, freeze, parser, scoring,
canary/failure handling, tamper detection and bundle creation without model calls.
`experiments/local-checkpoint/smoke.py` exercises the actual Transformers generation and
XGrammar handoff on a tiny randomly initialized Qwen3 network with the pinned real tokenizer
and programmed logits. It is an integration fixture, not a Qwen3-32B behavioral observation.
The dedicated CPU workflow runs that check. A full 32B load and 145-response GPU collection
remain for the operator; no such result is claimed by CI.

## Primary implementation references

- [Pinned official Qwen model card](https://huggingface.co/Qwen/Qwen3-32B/blob/9216db5781bf21249d130ec9da846c4624c16137/README.md)
- [Official Qwen Transformers inference guide](https://qwen.readthedocs.io/en/latest/inference/transformers.html)
- [Pinned XGrammar Transformers integration](https://github.com/mlc-ai/xgrammar/blob/v0.1.25/python/xgrammar/contrib/hf.py)
