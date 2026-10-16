# WTR-Bench

![CI](https://github.com/msblanders/wtr-bench/actions/workflows/ci.yml/badge.svg)

**Testing social inference in language models: distinguishing inferred regard from ability.**

The completed study asks what a model predicts about two people in a story: one
tried to help but could not; the other could help but refused. Does the model favor
the person who tried when predicting future giving, while favoring the capable
refuser when predicting success at the same task?

That contrast appeared in two of four tested configurations. The record includes
the negative and partial replications, earlier measurement failures, fixed plans,
raw responses, and reproducible analysis. These are judgments about fictional
people, **not measurements of the assistant's own preferences or an internal
welfare-tradeoff variable**.

## Start here

- **[Research note](docs/research-note-v1.md):** question, methods, all four configurations,
  limitations, and the distinction between behavioral results and mechanism claims.
- **[Data and provenance](docs/data-record.md):** original collection archives, raw responses,
  source revisions, checksums, and earlier diagnostic records.
- **[Reproduce one result offline](#reproduce-the-sonnet-pilot-offline):** regenerate the
  Sonnet pilot report from archived responses using the hash-verified protocol code.
- **[Mechanism proposal](docs/irv-mechanism-proposal-v0.2.md):** future work on calibrated
  causal interventions; no mechanism result is reported as completed.

## What was tested and found

Six selected scenarios contrasted attempted but unsuccessful help with a refusal
by someone described as capable and available. Each scenario had three questions:
future giving, same-task ability under stipulated effort, and different-task ability.
Two name assignments, two display orders, and two repetitions produced **144
responses per configuration**, including 48 for each question. Presentation variants
are checks within the six scenarios, not 144 independent social situations.

The prospectively fixed primary prediction favored the person who tried on giving
and the capable refuser on same-task ability. Equality and insufficient information
were separate permitted answers. No social judgment had a known-answer accuracy key.

| Tested configuration | Giving: person who tried /48 | Same-task ability: capable refuser /48 | Matched predicted crossovers /48 |
|---|---:|---:|---:|
| Claude Sonnet 4.5 | 48 | 46 | 46 |
| Qwen3-14B, reasoning disabled | 4 | 4 | 0 |
| Qwen3-14B, reasoning enabled | 5 | 43 | 4 |
| Qwen3-32B, reasoning enabled | 48 | 41 | 41 |

A matched crossover means the same scenario/name/order/repetition form selects the
person who tried for giving and the capable refuser for ability. Sonnet and thinking
Qwen3-32B showed both predicted net directions in all six scenarios. Non-thinking
Qwen3-14B returned insufficient information on 123/144 responses. Thinking Qwen3-14B
primarily recovered the ability judgment, while usually abstaining on giving.

The thinking extensions changed sampling settings and token allowance as well as
reasoning. They do not isolate a causal effect of reasoning. All Qwen runs used
hosted FP8 weights. The different-task probe was mixed and sometimes blurred
ability with diligence; it does not establish domain-general ability transfer.
See the [note](docs/research-note-v1.md) for the full distributions and configuration details.

## What remains unmeasured

- **The model's own welfare-tradeoff ratio or social preferences.** The original
  [Module A design](docs/wtr-bench-design.md) concerns the model's choices between
  its own described payoff and another person's payoff. That objective remains unmeasured.
- **The magnitude of an inferred valuation.** The completed social pilot tests an
  ordering at one allocation tradeoff, not a numerical WTR.
- **A maintained internal representation.** Separate learned rules could produce
  the giving/ability pattern without a shared valuation state. Explanations are
  model outputs, not faithful measurements of the underlying computation.
- **Relationships with the assistant itself, real-world behavior, or general safety.**
  The study concerns predictions about described people in six selected scenarios.

WTR-Bench retains its original project name. The completed social-inference study
is a narrower contribution than the benchmark's original measurement goal.

## Why measurement came first

Earlier formats produced position sensitivity, answers clustered below the payoff
ladder, and arithmetic or explanation–choice mismatches. These failures are part
of the record, not discarded pilots:

- [Terse-answer diagnostic](docs/debug-36077785515-review.md): 151/156 valuation
  answers selected the second option.
- [Recovery diagnostic](docs/recovery-36111049496-review.md): supplied weights
  yielded 72/72 correct choices and 18/18 recovered intervals; history-derived
  weights yielded 24/36 recovered intervals.
- [Natural-language validation](docs/paired-natural-v3.2.md): the later ordinal
  format returned 240/240 correct known-answer control responses on the tested
  Sonnet configuration, before the social pilot. That does not validate every model
  or establish correctness on unstipulated social judgments.

The [data record](docs/data-record.md) links these audits to their raw records.
Historical numerical pilots remain paused; their plans are preserved in [docs](docs/).

## Reproduce the Sonnet pilot offline

Requires Python 3.11+ and a checkout or downloaded copy of this repository.
After obtaining the repository, the commands below use only local files and the
Python standard library: **no API key, GPU, model download, or paid request**.
They extract a working copy of the committed archive, then run the repository scorer
after checking its frozen source hashes.
Run from the repository root, using a fresh output directory:

```bash
python3 -m zipfile -e \
  results/archive/paired-pilot-v1-36216737006-1.zip \
  runs/readme-sonnet-reproduction

PYTHONPATH=src python3 -m wtrbench.paired.social check
PYTHONPATH=src python3 -m wtrbench.paired.social report \
  --out runs/readme-sonnet-reproduction
```

Read `runs/readme-sonnet-reproduction/report.md` and `report.json`. Expected results:
144 recorded responses, giving 48/48 toward the person who tried, same-task ability
46/48 toward the capable refuser, and 46/48 matched predicted crossovers. The report
also retains the different-task answers, abstentions, and presentation diagnostics.

This reproduces analysis of saved outputs; it does not rerun model inference.
The scorer checks the source freeze, stimulus/request hashes and response metadata.
The [archive manifest](results/archive/manifest.json) records ZIP hashes, and the
[data record](docs/data-record.md) describes archive verification. Generated reports
are written only to the extracted working copy; committed ZIPs stay unchanged.

Use the repository-root commands above rather than running inside the extracted
`frozen-source` directory: the original ZIP omitted a hidden workflow file needed
for that directory's standalone source check. The repository contains the required
file, and its protocol freeze is checked before reporting.

## Current next steps

- **Local checkpoint bridge:** [prepared for operator launch](docs/paired-local-v1.md)
  on a pinned Qwen3-32B BF16 checkpoint. It targets a Linux machine with an 80 GB
  NVIDIA GPU. The full GPU collection is not reported as completed.
- **Recipient-specific follow-up:** [draft design, PR #8](https://github.com/msblanders/wtr-bench/pull/8)
  tests whether giving predictions change with the recipient and whether earlier
  actions were voluntary or assigned. It is an uncollected design with offline
  generation/scoring checks, not a completed finding or launch-ready collector.
- **Mechanism study:** the [proposal](docs/irv-mechanism-proposal-v0.2.md) specifies
  calibration on constructed systems followed by selective interventions on an
  inspectable model. A local behavioral replication alone would not establish mechanism.

## Contributions and AI assistance

[Mitchell Landers](https://scholar.google.com/citations?user=NeyqJzUAAAAJ) initiated
this project to connect his research interests in social emotions and psychological
measurement with empirical questions about AI. Research planning and development
have proceeded through collaboration with Claude and ChatGPT.

AI assistance has included study-design proposals and critiques, code implementation,
automated tests, analysis and audit tooling, and drafting and revision of research
notes and documentation. The repository should not be read as evidence that its
software or prose was produced unaided. Qualitative response audits identified as
assistant audits are **not independent human validation**. Documents marked as drafts
retain that status; software checks establish implementation behavior, not the truth
of a psychological interpretation.

[Website](https://msblanders.github.io/website/) ·
[Google Scholar](https://scholar.google.com/citations?user=NeyqJzUAAAAJ)

## Development and historical designs

To install the repository development environment and run its checks (dependency
installation may require internet access):

```bash
uv sync --frozen --all-groups --extra eval
uv run pytest
uv run ruff check .
uv run mypy src
```

The original [Module A design](docs/wtr-bench-design.md),
[inference design](docs/inference-module-design.md), and
[historical runbook](docs/inference-runbook.md) remain available. Historical collection
commands are not instructions to launch new experiments. The original README is
preserved in [repository history](https://github.com/msblanders/wtr-bench/blob/fa7db88a75fe48ebcf192b1973711524b0e7a712/README.md).

MIT license; see [LICENSE](LICENSE).
