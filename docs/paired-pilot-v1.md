# Paired social pilot v1: prospective plan

Prepared 25 September 2026 (America/Los_Angeles), before social-pilot collection.
Protocol identifier: `paired-pilot-v1`. This is a dated repository specification,
not an external preregistration. The source baseline is
`8adf2fb47174209ab6988693704fa7685f8d7343`. The associated decision is recorded
in `paired-pilot-v1-decision.md` and bound by the same freeze.

## 1. Question and scope

Does this model distinguish two people who failed to help for different reasons:
one tried but could not, whereas the other was able and free but refused?
The predicted pattern is opposite directions across two comparative judgments:
greater giving likelihood for the unable-but-tried person and greater same-task
success likelihood for the able-but-unwilling person under stipulated effort.
Different-task success is a transfer comparison, with no required answer.

Exactly 144 requests: six existing scenarios x three probes x two independent
name assignments x two presentation orders x two prespecified passes. There are
72 distinct requests, each presented twice, and 18 scenario/probe cells with
eight responses each. There are no new validation cases, extra cause pairs,
second allocation payoff, aggregate-history family, or adaptive follow-ups.
The unit for describing breadth of the finding is six selected scenarios,
not 144 independent observations, participants, or social situations.

## 2. Basis for proceeding

Paired natural v3.2, run 36200022149 at the source baseline, met its unchanged
prospective gate: 240/240 control answers correct; 40/40 ungated deeds answers
in the predicted direction; all 280 usable. No observed name, order or repeat
disagreements were found. Its original artifact SHA256 is
`79af87fdbf892338a51e22c84965d3dc43ce34e2f602323916dad8d8bddf77d8`.
The audited review supplied in this conversation independently reproduced the
results and recommended this pilot. See the decision record for source links.

That pass establishes limited premise-following performance on those controls,
not accuracy on unstipulated social judgments. Its D cases tested absent or
explicitly irrelevant evidence, not all relevant-but-inconclusive evidence.
v2 remains a failed, different numerical procedure. These sequential development
results do not isolate the causal effects of arithmetic, wording or any repair.

## 3. Materials and the conversion to paired evidence

`protocols/paired-pilot-v1-scenarios.json` copies the help, unwilling, unable,
failed-outcome, same-task and different-task fields for couch, faucet,
spreadsheet, translate, dog and presentation from the existing `TASKS` material
in `src/wtrbench/inference.py` at the baseline. The debug-only boxes scenario is
excluded. Neither historical source nor earlier freeze is overwritten.

The two accounts are rendered as two separate occasions, each involving only
the person named in that account. This explicit common wrapper avoids implying
that two people were present at the same event or that the two identical failure
outcomes happened to the same request. Both people are acquaintances and both
accounts retain their matched failure outcome. Swapping display order changes
the order of accounts, not a stipulated chronology.

A second common sentence states that each person's task-relevant knowledge and
physical limitations remain as described in the future situations. It preserves
the inability manipulation without fixing a new success probability or stipulating
the future answer. Both wrappers appear identically in all three probes.
These are disclosed paired-presentation adaptations, not verbatim original
single-person prompts. Complete sample prompts for all six scenarios and all
three probes are committed in `paired-pilot-v1-samples.md`; the full schedule
is committed as `protocols/paired-pilot-v1-items.jsonl.gz`.

The original scope called these the held-out scenarios: held out from the
recorded development calls in the supplied project record, not claimed absent
from pretraining. Reading and auditing the stimuli while preparing this plan
is not a model-facing development run. No pilot responses were collected to
choose these materials, order, scoring rules or wording.

## 4. Probes and response protocol

The pilot calls the validated `natural.render_pair` unchanged. Its common
preamble and A/B/C/D options are not copied into a divergent renderer:
A/B select a person; C means evidence supports equal likelihood; D means
insufficient evidence to support either an ordering or equality. Invalid
or truncated replies are separate from either legitimate response.

- **Valuation:** predict who gives you 10 points rather than keeps 5. This is
  a comparison at one tradeoff, not a recovered WTR or ordering at all payoffs.
- **Same-task ability:** predict success in the specified related task next
  month, with genuine effort and enough time. The continuing limitation stays
  in force. This is not willingness to make the effort; that effort is supplied
  by the question.
- **Different-task ability:** the same conditional success question about the
  existing different-task description. An ordering, equality or insufficiency
  is a reportable outcome; no C/D answer is required.

No exception-free allocation rule, numerical success probability, explicit
ability ordering or equality from the controls enters these stories. The
historic evidence already describes ability/refusal; this design tests judgments
from those descriptions, not spontaneous discovery of the causes. A positive
result need not uniquely distinguish the theory from other semantic or social
reasoning accounts. Same- and different-task ability differ in the task asked;
all three probes otherwise receive exactly the same evidence within a form.

Pinned model: `claude-sonnet-4-5-20250929`; temperature 0; 256 output tokens;
fresh context per request; the v3.2 system instruction and structured-output
schema unchanged. JSON must contain a nonempty `brief_basis`, then uppercase
`answer` A/B/C/D; exactly one text block and `end_turn`. Duplicate fields,
wrong field order, extra fields, truncation and refusal are unusable. The shared
strict decoder never repairs an answer using its explanation.

## 5. Counterbalancing and prospective sequence

Names attach to semantic people before choosing display order. Each scenario
and probe crosses Sam/Priya assignment with which cause's account/answer appears
first. Evidence order and A/B option order vary jointly: their separate effects
are not identified. C/D keep fixed positions. Each pass contains 72 requests in
its own deterministic hash order; two passes are the plan, not optional reruns.
Item IDs include the full stimulus metadata and repetition; private semantic
maps and metadata never enter the API request. A model does not see the other
probes' responses or another request's history.

## 6. Analysis fixed before collection

**No natural response has a correctness key, and there is no scientific
PASS/FAIL gate for this pilot.** A successful workflow means code completion;
COMPLETE means 144 records, not support for the prediction. All outcomes remain
in the report, without selecting favorable scenarios, names, orders or passes.

For every scenario/probe, display the eight individual semantic answers and
counts of unable, unwilling, equal, insufficient, invalid, and missing.
Also display each pass separately and pooled counts per probe (48 scheduled
each). These are descriptive denominators, not independent binomial trials.

A secondary directional index is `(n_unable - n_unwilling) / 8` within a cell.
It is a difference of scheduled response proportions, not a person's probability
of giving, a WTR, or a latent estimate. C/D/invalid/missing contribute zero to
the directional numerator but are never merged in the underlying table.
Missing or unusable data must not be interpreted as evidence for a null effect.
For each scenario, show valuation net, same-task ability net, and their difference.
The predicted pair of signs is valuation > 0 and same-task ability < 0; a positive
net difference alone is insufficient. The number of scenarios with both signs
is a descriptive count, not a threshold for declaring the theory confirmed.

Additionally pair the valuation and same-task answers for each identical
scenario/name/order/pass form: predicted crossover (unable, unwilling), reverse
crossover (unwilling, unable), same person on both, includes C or D, or invalid/
missing. There are eight scheduled forms per scenario. C and D remain separate
in the cell-level and item-level files even where this auxiliary table groups them.
These matched forms are separate API requests, not paired responses from an
independent human participant. Do not filter to fully invariant or valid forms
before calculating the main scheduled-denominator counts.

For order, name and repeat checks, report semantic disagreements over comparable
(two usable) pairs and also show the full scheduled denominator: 72 per factor,
24 per probe. Missing/invalid pairs cannot improve apparent agreement by being
silently discarded. These factor comparisons overlap and are not independent.

No request-level significance tests, confidence intervals based on 144 independent
trials, or population-generalization claims are planned. This small pilot is
reported descriptively across six selected scenarios. After collection, audit
raw explanations for explicit premise contradictions and answer mismatches,
retain exact text, disclose unblinded assistant/human review and duplicate reuse,
and never use explanations to change the recorded answer. Such annotations are
post-collection text review, not access to hidden model reasoning.

## 7. Collection, stopping, and provenance

Collect the 144-request fixed schedule once regardless of content. Zero SDK
retries, no fallback model, no answer-dependent extra requests, and no automatic
resume. A transport or integrity failure stops collection and records the attempted
request and preserved responses. Do not use GitHub Re-run jobs or start a fresh
workflow to replace partial or unfavorable data. A fresh dispatch is not technically
a global lockout; the one-batch restriction is also a research procedure.

The workflow defaults to offline `generate`. The researcher launches paid collection
by choosing `collect` and typing `COLLECT_144`. It uses the existing secret
`ANTHROPIC_API_KEY`, without exposing or replacing it. Credit balance and price
are not verified by this plan. Checks and generation precede any model calls.
No push, PR or merge automatically initiates collection.

Record raw requests and full API responses, model/request/message IDs, token
usage, SDK/Python environment, actual GitHub source SHA/run/attempt and start time.
Write each raw reply before integrity checks. Freeze the plan, decision, scenario
text, sample prompts, packed full schedule, source, shared renderer/decoder,
tests, workflow, items and order-preserving request-body hashes. Save frozen source
copies alongside the run so the exact analysis can be reproduced later.
The workflow preserves artifact checksums even on failure where feasible.
An integrity failure is not rescued by issuing an ordinary report from corrupt
records; retain the raw artifact for investigation.

## 8. Review and launch

Software tests must pass before publication to main. Tests use programmed
fixtures clearly separated from model data: predicted and reverse crossover,
same-person strategies, constant letters, C, D, partial/invalid responses,
transport interruption, altered metadata and frozen artifact reproduction.
They establish scorer/runner behavior, not that the social predictions are true.

After merge, Actions -> **Paired social pilot v1** -> Run workflow -> main ->
mode `collect` -> confirmation `COLLECT_144`. Launch once and save
`paired-pilot-v1-<run ID>-1`. Commands from a checkout:

```bash
uv run python -m wtrbench.paired.social check
uv run python -m wtrbench.paired.social generate
# Researcher launches the one batch only after reviewing this plan:
uv run python -m wtrbench.paired.social run --confirm 144
uv run python -m wtrbench.paired.social report
```

This plan replaces neither the successful validation nor the paused historical
888/816-request pilots. Report the new pilot regardless of direction, including
mixed, null, reversed or presentation-sensitive findings. No new validation
instrument is a prerequisite created by this implementation.

## 9. Pre-collection implementation completion

The interrupted source-only commit was completed with offline software tests,
all 18 canonical sample prompts, the deterministic 144-item schedule, and the
manual workflow. Packaging corrections include the package initializer and the freeze manifest at
`frozen-source/protocols/paired-pilot-v1.json`, in addition to the run-root
`freeze.json`. This makes the archived source directly checkable and prevents an installed
repository package from taking precedence over the snapshot. No prompt,
request order, response convention, scientific scope or old freeze changed.

For reproduction, use Python 3.11+ and the saved source snapshot. No model
access or SDK is needed for `check` or `report`. From the artifact's
`frozen-source` directory, with `/absolute/path/to/artifact` replaced by the
actual extracted run directory:

```bash
PYTHONPATH=src python -m wtrbench.paired.social check
PYTHONPATH=src python -m wtrbench.paired.social report --out /absolute/path/to/artifact
```

The report verifies the run freeze and item/request hashes and rejects corrupt
response metadata. It reproduces report JSON/Markdown, answer CSV, and pair
audit from saved raw responses. The snapshot carries the pilot tests for
provenance; the full test suite runs from the repository checkout, where the
historical inference module used in the scenario-preservation test is present.
Artifact checksums use paths relative to the artifact root, so after extraction
`sha256sum -c SHA256SUMS.txt` works from that directory.
