# Exploratory response calibration

**Status:** This original protocol was run in
[36081054221](calibration-36081054221-review.md). Neither format passed.
The current next step is the separate
[structured-answer calibration](inference-calibration-structured.md).
The specification below is retained as the original pre-run record.

Prepared after [Sonnet debug 36077785515](debug-36077785515-review.md), before
any calibration responses. The question is whether the current protocol
can collect interpretable predictions, independent of their psychological
direction. This is separate from the inference pilot and uses no untouched
pilot cases.

## Batch and rationale

**72 API requests per model:** 48 known-answer controls and 24 questions
derived from six already examined debug cases. Each underlying case crosses
two option orders with two reply formats. Every API request has a fresh
message history; controls are not demonstrations placed before other items.
The generated calibration item hash is `299094bf02c5a1d1`. Request settings
and the source revision are recorded separately; the hash alone does not
freeze the system instructions.

| Kind | Underlying cases | Requests | Correct answer available? |
|---|---:|---:|---|
| Identify the option that pays a named recipient | 4 | 16 | Yes, stated in the options |
| Identify the larger number of points | 2 | 8 | Yes, by arithmetic |
| Predict an explicit deterministic choice rule | 6 | 24 | Yes, from the stated rule |
| Repeat selected debug judgments | 6 | 24 | No; assess response consistency only |

The explicit-rule controls state that Sam values an allocation as Sam's
points plus a specified weight times your points, and chooses the larger
value. Weights are 0.5, 1 and 2, with one offer on each side of each
threshold and no ties. These instructions supply ground truth for a control;
they do not make claims about ordinary human preferences or an LLM's own
valuation. Arithmetic and recipient lookup separately check simpler demands.

The six debug cases are boxes/unable and boxes/unwilling at ratios 0.1 and
1.0, plus the debug numerical set's LOW and HIGH T1 histories at ratio 0.5,
with the original evidence order. No psychologically preferred response is
designated correct. Source item IDs are recorded.

The **letter** condition uses the existing A/B-only system instruction and
letter decoding. Its debug prompts are byte-identical to their original
versions. The **recipient** condition retains the same displayed A/B
options, but asks for SAM or YOU to name the recipient in the chosen option;
its system instruction likewise specifies SAM or YOU. This compares two
complete reply protocols, not an isolated causal effect of a label token.
It does not add a rationale request or additional reasoning budget.

Within each reply format, the 24 known-answer controls are balanced: 12
correct SAM and 12 correct YOU; in A/B format, 12 correct A and 12 correct B.
An always-B responder is only half correct and disagrees semantically across
every option pair. An always-SAM responder agrees across option order but
is still only half correct. Agreement alone therefore cannot pass the
control check.

## Execution

In GitHub:

1. Open **Actions > Inference calibration > Run workflow**.
2. Select `main` and leave model `claude-sonnet-4-5-20250929`.
3. Launch once. The existing `ANTHROPIC_API_KEY` secret is used.
4. Share the run link or download the `inference-calibration-...` artifact.

This workflow calls only the 72 calibration prompts. It does not run the
196-item debug or 888-item pilot. Outputs include the exact items, response
configuration, raw answers, stop reasons, returned model, request IDs, token
usage, source revision, dependencies and inspection report. API usage is
billed to the supplied key. The 64-token output limit is a per-request
maximum, not a billed fixed amount.

Local equivalents:

```bash
uv sync --frozen --all-groups --extra eval
uv run python -m wtrbench.calibration generate
uv run python -m wtrbench.calibration run claude-sonnet-4-5-20250929
uv run python -m wtrbench.calibration inspect runs/calibration/claude-sonnet-4-5-20250929.jsonl
```

Generation is free and makes no API calls. Existing response files cannot
be overwritten. Add `--resume` to continue an interrupted run with the same
configuration; unparsed recorded responses are not retried. GitHub starts a
fresh run on each workflow launch, so recover a partial artifact locally to
resume rather than using Re-run jobs. Inspect old runs at their recorded
source revision; the item hash is checked before inspection.

## Interpretation fixed before this run

Read known-answer accuracy and completeness before the debug-case responses.
The controls are deliberately simple; investigate every error rather than
choosing a cutoff after seeing which format looks favorable. Check accuracy
separately for each control kind, reply format and option order. The report
uses all planned controls as the accuracy denominator and separately counts
missing/unparsed answers. Order-disagreement denominators include only
pairs with two parsed responses. There is one call per item, no retries for
an undesirable answer, and no inference from many items to many independent
scenarios.

- If a format fails recipient lookup or arithmetic, inspect the basic
  input/answer handling before interpreting social judgments in that format.
- If it passes the simpler controls but fails the explicit-rule controls,
  quantity recognition alone has not established reliable choice prediction.
- If it passes all controls but debug predictions remain order-sensitive,
  the control success does not validate those social-judgment measurements.
- If the recipient format passes controls and yields stable debug responses,
  it is a candidate for further measurement development. Repeat the full
  debug battery under a documented revision to assess ladder coverage and
  remaining inconsistencies before any pilot freeze.
- If both formats fail, retain that result and diagnose the specified
  failure. Do not search formats or models until the theoretical ordering
  appears.

Stable responses may still be censored or reflect a response heuristic.
These checks do not establish human-like valuation, validate transfer across
all scenarios, or identify a maintained/shared internal variable. Both
formats' results and all three earlier debug runs remain part of the record.
