# Does a giving prediction track a particular relationship?

**Recipient-specific follow-up v1: design for author review, 14 October 2026 UTC.**
This is a prospective design snapshot, not a completed study, an externally registered
preregistration, or a launch-ready collection freeze. No responses to these materials have
been collected. The offline generator, controls, scoring specification and software fixtures
are supplied now. A collection runner and its integrity/budget tests remain to be implemented
and frozen before a researcher launches a run.

Repository baseline: `fa7db88a75fe48ebcf192b1973711524b0e7a712`.
This new extension leaves every historical pilot, replication, result and freeze unchanged.

## 1. Question and contribution

The [existing note](research-note-v1.md) reports a giving-versus-ability dissociation.
It does not establish whether giving predictions track **who a described person treats well**,
rather than an overall impression of that person's niceness. This follow-up asks:

> With each person's total helpfulness held equal, does changing the recipient reverse
> the model's predicted giver? Does that reversal weaken when the same actions were assigned
> externally rather than freely chosen?

The target is a prediction about described people in a fictional situation. It is not the
assistant's own preference or treatment of users. A positive result would add evidence of
recipient-specific, choice-sensitive social prediction. It would not identify a shared internal
representation, its persistence, its numerical magnitude, or a welfare-tradeoff ratio.

The central contrast, before naming or display permutations, is:

| Person | Earlier action toward R | Earlier action toward S |
|---|---|---|
| P | Completes the favor | Declines the favor |
| Q | Declines the favor | Completes the favor |

Each actor helps once and declines once. Each recipient receives help once and a refusal once.
Ability, opportunity, effort, recipient benefit and payment are matched within the story.
The evidence is identical in the two questions; only the proposed allocation recipient changes.
The voluntary-history prediction is P for R and Q for S.

A second version keeps all four events and outcomes identical, but states that a computer
randomly assigned which request each helper had to complete or decline, independently of the
relationships, with no discretion. The predicted recipient effect is weaker in this version.
There is **no correctness key requiring C or D** for these assigned-history items. Equality
and insufficient evidence are distinct possible judgments; equal observed histories do not
establish equal latent preferences or equal future giving probabilities.

This assignment comparison tests sensitivity to the stated cause of the actions. It adds a
somewhat artificial instruction context, so its effect is not attributable exclusively to a
latent regard inference. A model could follow a learned discounting rule for assigned actions.

## 2. Fixed scope and materials

There are 24 newly constructed task variants, organized into six descriptive domains with
four tasks each: errands, digital assistance, event preparation, time and presence, practical
assistance, and checking and organizing. Exact texts are in
[`recipient-specific-v1-scenarios.json`](../protocols/recipient-specific-v1-scenarios.json).
The [review materials](recipient-specific-v1-samples.md) show every request and complete
canonical prompts for both conditions and both recipients, plus every control type.

These tasks share one common relational template. They are 24 selected task variants, not a
random sample of social life or 24 independent theories of regard. They have not been selected
using evaluation-model responses. They are not claimed absent from model pretraining. No
numerical power claim or new-model generalization is attached to this convenience set.

Every story contains four separate requests from the same week, with no chronology implied by
display order. All four named people are acquaintances. Each favor takes five or ten minutes,
matched across all four events within a scenario. There is no payment, prior debt, competing
request or promised reciprocity. Both helpers could perform each task and had spare time.
The future allocation is private, with no future reward, repayment or penalty. Both recipients
would benefit equally from 10 points. These stipulations narrow alternative explanations;
they make the design more controlled and less naturalistic than an unrestricted social story.

One probe asks which helper is more likely to give the named recipient 10 points rather than
keep 5 points. This preserves the pilot's tradeoff while changing the perspective from giving
to a fictional "you" to giving to a named third party. That wording change and the new
four-person stories require their own control report. This is a new behavioral extension,
not an identical replication of the frozen 144-item pilot.

| Component | Fixed calculation | Requests |
|---|---|---:|
| Main comparison | 24 tasks × 2 conditions × 2 recipients × 16 forms | 1,536 |
| Known-answer controls | 4 types × 2 recipients × 16 forms | 128 |
| Prespecified repeat check | 24 tasks × 2 conditions × 2 recipients × 1 canonical form | 96 |
| Total | One model configuration, one schedule | **1,760** |

The 96 repeats are appended after the first 1,664 requests. They repeat the all-zero form
exactly and are used only for repeat diagnostics, not to give that form extra weight in the
primary analysis. This checks one canonical presentation per cell, not all-form repeatability.
Task and control requests are mixed in a deterministic hash order in the first phase; the
repeat phase has its own deterministic order. Each request receives a fresh context, never
another question's response or an instruction to compare conditions.

## 3. Counterbalancing

All four binary presentation factors are fully crossed, yielding 16 forms per task/condition/
recipient. They are not a fractional design:

1. Actor names: P/Q = Sam/Priya or Priya/Sam.
2. Recipient names: R/S = Alex/Jordan or Jordan/Alex.
3. Evidence order: P→R help, Q→R decline, P→S decline, Q→S help, or the exact reverse.
4. Answer order: P then Q, or Q then P. The opening names follow this answer order.

Evidence order and answer order vary independently. Only two of the 24 possible event
permutations are tested. C and D retain their fixed positions. This does not test all names,
languages, verbal paraphrases or option orders. P/Q/R/S and condition labels are private
metadata and never appear in requests. Actor and recipient mappings, requested bodies and
request order are committed by hashes in the design snapshot.

## 4. Predictions and alternatives

Two planned contrasts have different roles:

- **Primary: recipient specificity in voluntary histories.** P is favored for R, Q for S.
  Both cell directions matter; a positive difference caused solely by fewer abstentions in
  one cell is not the full predicted reversal.
- **Secondary: sensitivity to assigned versus chosen actions.** The recipient-specific index
  is larger with voluntary actions than with assigned actions, alongside the full C/D and
  directional distributions. This comparison is planned now, not selected after the primary
  result. A condition difference without a voluntary reversal does not establish the pattern.

| Pattern | What it would support or leave open |
|---|---|
| Voluntary reversal, substantially weaker assigned effect, controls adequate | Giving predictions track recipient-linked voluntary history across these tasks; a recipient-insensitive actor ranking is insufficient |
| Similar reversals in both conditions | Recipient binding is present, but action-pair associations, instruction discounting failure or other rules remain plausible |
| Little voluntary reversal, frequent D, controls adequate | Relevant history often does not license the proposed allocation prediction under this configuration; conservative transfer thresholds remain possible |
| Same person favored for both recipients | Actor-level preference, salience or another recipient-insensitive strategy may explain the output; inspect name/order summaries |
| Controls weak, many invalid replies, or incomplete collection | Format/premise-following or operational limits constrain interpretation; retain and report the outcomes |

These are interpretations of distributions, not a numerical success threshold selected to
declare a theory confirmed. All patterns, including reversal against prediction, will be
reported. A random tie-breaker can occasionally produce a matched crossover, so a few such
pairs alone do not refute a global account. The signed indices, reverse crossovers, stability
checks and breadth across tasks must be shown together.

Recipient-specific lookup rules could reproduce a positive result without a shared valuation
state. So could a rule that discounts mandated conduct. An assigned-action paragraph might
also raise a general threshold for giving a directional answer. The design does not rule
these out. Ability is matched by stipulation, not measured again in an ability probe.
Generated brief explanations are text to audit, not faithful reports of the computation.

## 5. Known-answer controls and quality flag

Each type has 32 requests with the same name/order factors and both recipient questions.
The control task is collecting a prepared visitor badge, outside the 24 experimental tasks.

| Type | Evidence that supplies the key | Expected semantic response |
|---|---|---|
| Rule aligned | Exception-free future allocation behavior matches the voluntary history | P for R; Q for S |
| Rule conflict | Exception-free future allocation behavior reverses the voluntary history | Q for R; P for S |
| Equal | Both follow a fair-coin giving rule for either recipient, with equal chances stated | Equal (C) |
| No information | No relevant action, preference or allocation evidence for either actor | Insufficient (D), following the response convention |

These are limited comprehension/format controls, not natural-history accuracy items. The
conflicting rule control catches a strategy that always copies earlier helping even when a
future rule settles the question. The no-information key follows the explicit response
convention; it is not a universal philosophical claim about inference from ignorance.

Prespecified quality flag: **at least 30/32 correct in each of the four categories**. Invalid
and missing count as not correct for this flag. This is a pragmatic report-quality criterion,
not an empirically calibrated scientific threshold. Report every error and the exact category
counts. The flag never stops collection, changes prompts, excludes primary items or licenses
replacement requests. If it fails, describe the main result with that limitation and make no
clean positive or negative claim about the intended construct. Passing does not prove that
all experimental stories were understood.

## 6. Model, answer format and comparability

Planned configuration: `claude-sonnet-4-5-20250929`, first-party Anthropic API, temperature 0,
maximum output 256 tokens, no extended thinking, no tools, no prompt caching and no conversation
history. Reuse the existing `natural.request_body` system instruction and strict JSON schema.
Do not set additional sampling parameters. The renderer is new because the recipient is named;
the original pilot renderer is not changed.

System instruction, verbatim:

```text
Return exactly two JSON fields in this order: "brief_basis", a one- or two-sentence explanation using the supplied information; then "answer", one of A, B, C, D. Do not include any other fields.
```

The schema requires string `brief_basis`, then `answer` in A/B/C/D, with no extra fields.
The shared decoder additionally requires a nonempty basis, unique fields in that order,
exactly one text block, and `end_turn`. Refusal, truncation, duplicate/extra fields or malformed
answers are invalid; explanations never repair an answer. C means evidence supports equal
likelihood; D means evidence supports neither an ordering nor equality.

Holding the originally successful model/configuration constant makes the new comparison
easier to relate to the existing pilot. It does not guarantee that a hosted service is
unchanged since September. Record dates and returned model identifiers.
[Anthropic's status page](https://platform.claude.com/docs/en/about-claude/model-deprecations),
checked 14 October 2026 UTC, lists this model as deprecated but available until its scheduled
30 November 2026 retirement. If unavailable, stop and record a dated model amendment before
any collection; do not silently substitute a model or choose one from social-prompt previews.

## 7. Analysis fixed before collection

Primary cells contain 16 scheduled answers. Decode A/B to semantic P/Q before every comparison.
For each task f, condition c and recipient t, report counts of P, Q, C, D, invalid and missing.
Use the scheduled denominator; show validity separately. Define:

```text
d[f,c,R] = (number choosing P for R - number choosing Q for R) / 16
d[f,c,S] = (number choosing P for S - number choosing Q for S) / 16
I[f,c]   = (d[f,c,R] - d[f,c,S]) / 2
J[f]     = I[f,voluntary] - I[f,assigned]
```

I ranges from -1 to +1; J from -2 to +2. Full predicted direction in a task/condition requires
`d[R] > 0` **and** `d[S] < 0`. The primary estimate is the equal-task mean of voluntary I,
accompanied by both cell nets and the count of tasks with both signs. The planned secondary
estimate is the equal-task mean J, accompanied by each condition's I. These are response
indices, not giving probabilities, effect sizes on an internal state or WTR estimates.

C, D, invalid and missing contribute zero to directional numerators solely to retain fixed
denominators. Their counts remain separate everywhere. Missing/invalid responses must never
be interpreted as equality or evidence of absence. If collection is partial, reports are
labeled partial; show coverage by task and condition and do not report a completed test or
treat missing observations as a scientific null.

For each of the 16 matched forms in every task/condition, retain the full 6×6 semantic answer
matrix for the two recipients. Report predicted P/Q crossovers, reverse Q/P crossovers, P/P
and Q/Q same-person choices, C, D and unusable/missing combinations. There are 384 matched
forms per condition. They are separate API calls, not independent human participants.

Report name, recipient-name, evidence-order and option-order semantic disagreements over
comparable pairs, with their full scheduled denominators: 384 per factor per condition.
These comparisons overlap. Report the 96 canonical repeat pairs with comparable and scheduled
denominators. Do not discard unstable forms or pool repeats into the main estimates.

Main display: one row per task with both recipient nets in each condition, I, J, crossover
counts, C/D counts and invalid/missing. A second display shows the four control types and
presentation/repeat diagnostics. Show task domains as descriptive annotations only; do not
conduct six new domain hypothesis tests. Preserve individual decoded answers and raw bases.

This study is descriptive across 24 selected variants of a common template. There are no
request-level p-values, binomial intervals treating 1,536 calls as independent social
observations, or population claims. No cutoff is used to label the psychological theory
proved. Any later exploratory analyses are labeled separately from these fixed summaries.

Any rationale audit is unblinded, post-collection and separate from scoring. Quote raw text
with item IDs. Describe contradictions or explanation/answer mismatches without interpreting
the text as an observed latent state. Report who reviewed it and whether any independent
human coding took place; assistant checks are not independent scientific review.

## 8. Budget, stopping and implementation requirements

**No paid API call is part of this design task.** The planned single-model collection has a
US$25 ceiling, leaving most of the user's US$200 credit for later work. The runner must enforce
that ceiling; this offline module does not implement or claim a billing guard.

[Official standard pricing](https://platform.claude.com/docs/en/about-claude/pricing), checked
14 October 2026 UTC, is $3 per million input tokens and $15 per million output tokens for
Sonnet 4.5. At 1,000 input tokens and 100–256 output tokens per call, 1,760 calls would cost
about **$7.92–$12.04**. At a planning allowance of 2,000 input tokens and the maximum 256 output
tokens each, the conditional total is **$17.32**. These are arithmetic estimates, not measured
token counts or guaranteed billing. Prices, credit eligibility and input overhead need checking
at launch. No batch discount or caching saving is assumed.

Before paid collection, the implementation must:

1. Reproduce this item stream and request-body hash. Archive the reviewed plan, source,
   tests, environment, runner, workflow and complete generated schedule as a collection freeze.
2. Check model availability, price and token allowance without using social responses to pick
   a model or prompt. Count/estimate inputs including format overhead; require a conservative
   full-schedule reserve under $25 before starting. Reject an oversized schedule before the
   first generation. Record that preflight, including its limitations.
3. Collect serially with SDK retries disabled, keeping a durable attempted-request ledger.
   Record body, item ID, request/message/model IDs, raw API response, stop reason, token usage,
   estimated spend, UTC time, source revision, run ID and attempt. Flush raw records before
   decoding. A received invalid answer stays recorded and the schedule proceeds.
4. Stop for a transport/integrity failure or budget limit, preserving the attempt and every
   response. Reserve the maximum possible output charge before each request. Conservatively
   charge the reserved amount for an uncertain billed attempt. No automatic retry, resume,
   fallback model or re-run to replace unfavorable/partial data. A necessary recovery requires
   a dated amendment with the original records preserved and linked.
5. Complete the fixed schedule regardless of answer direction or control performance. Report
   every outcome. No adaptive scenario removal, new probes, extra repeats or prompt repairs.
6. Make generation/checking the workflow default, with manual researcher launch for paid
   collection. Add no push/PR-triggered API job. Archive raw outputs durably in the existing
   public data record and verify hashes before interpreting them.

The $25 allocation is a proposed limit, not permission to spend now. No second model or open
checkpoint run is bundled into it. Any replication is a separate prospectively fixed study.

## 9. What is ready now and what remains

Ready: this design, all 24 task texts, exact prompt rendering, 1,760-request deterministic
schedule, snapshot hashes for this draft version, a semantic scorer, canonical
review prompts, and synthetic software checks. The snapshot's status explicitly says
`design_snapshot_not_collection_freeze`; source hashes do not constitute scientific validation
or externally registered preregistration.

Offline commands, from the repository checkout (no SDK or API key required):

```bash
PYTHONPATH=src python -m wtrbench.paired.recipient_design check
PYTHONPATH=src python -m wtrbench.paired.recipient_design generate
PYTHONPATH=src python -m pytest tests/test_recipient_design.py
```

`generate` writes every complete item and requested API body to a new local output directory.
It refuses to overwrite an existing directory. `score --answers PATH` accepts an item-ID-to-
semantic-answer JSON mapping for offline summaries. It is not yet a raw-response integrity
auditor; synthetic fixture output must never be presented as model data.

Before launch: the author reviews the research choices and complete materials; implementation
adds the collector, budget/integrity guard, archived-source reproduction, raw-response report
and manual workflow; offline failure tests pass; the final protocol/runner commit is frozen
and time-stamped before collection. Any design change before that point gets a new recorded
version, with no claims that this draft was already the preregistration.

## 10. Place in the article and mechanism project

This asks a narrower, more informative behavioral question than simply collecting another
model result: does a prediction depend on the particular actor–recipient history and whether
the actor chose it? It adds a controlled test of directedness, which the original inability/
unwillingness pilot did not contain. That can strengthen the note if executed and reported
well; an outcome is not promised, and the fellowship application need not wait for it.

It remains **behavioral**. The [mechanism proposal](irv-mechanism-proposal-v0.2.md) still needs
constructed-system calibration and selective interventions on an inspectable model, after its
target behavior is demonstrated locally. These new materials could later supply actor/recipient
controls for that project, but Sonnet API credits do not provide activation access or replace
the recovery study. A positive result would sharpen the behavior to explain; a mixed result
would constrain it.

The design, materials and software were prepared with AI assistance. Mitchell Landers's review,
understanding and ownership of the research choices remain necessary. No independent human
validation, model-data collection or mechanism result is claimed here.
