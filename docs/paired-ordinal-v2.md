# Paired ordinal v2: prospective validation before an attribution pilot

Status: new, uncollected candidate. This document and its executable freeze must
be committed and reviewed before the first experimental request. A software-test
pass is not a model result. Neither old social pilot is enabled by this plan.
This is a dated repository analysis plan, not an external preregistration.

## Question and scope

The target is a model's **comparative social judgments elicited with brief
explanations** about two described people. It is not the responding model's own
social preferences. A prediction about giving rather than keeping at one stated
tradeoff is not a recovered WTR magnitude or a general ordering of latent weights.

The new instrument uses A/B for the two people, C for equal probabilities on the
stated evidence, and D for insufficient evidence. C and D are never collapsed in
reporting. Invalid/truncated output is a separate category. Explanations do not
repair final answers, and correct answers do not prove correct explanations.

All archived ladder plans, results and their criteria remain unchanged. The
keeping-only aggregate family is deferred, not declared meaningless and not
silently replaced by bracketing evidence. The two kinds of evidence answer
different questions. See `validation-before-pilot.md` and the original audits.

## What was changed from the uploaded v1 proposal

See `paired-v1-review.md` for the implementation audit and source checksums.
Names now bind to semantic identities before position changes. Known-answer
ability controls stipulate exact task-success probabilities, independently of
point-choice preferences. Prior faucet experience does not logically establish
equal competence. Validation uses new numerical parameterizations and five
non-pilot task descriptions, not the previous low/middle/high profiles or the
held-out faucet scenario. D now has a known-answer category of its own.

This is a separate prospective candidate, not a revision of a failed historical
gate. It changes the stimulus set and category-level rule before collection.

## One validation batch: 240 requests

There are 30 base cases: five new numerical parameterizations of each category
below. Each is crossed with two name assignments, two joint evidence/answer
presentation orders, and two scheduled passes: 30 x 2 x 2 x 2 = 240 requests.
There are 120 byte-distinct requests, each repeated once. These are six test
categories, not 30 independent reasoning domains or 240 independent observations.

| Category | Key | Purpose |
|---|---|---|
| Discriminating tradeoff | Giving person | Probe ratio is strictly between disjoint compatible weight intervals. |
| Both give | C | Different weights need not produce different choices at this tradeoff. |
| Both keep | C | Same check on the other side of both intervals. |
| Ability conflict | More skilled, lower-weight person | Do not choose the more generous person on every dimension. |
| Ability equality | C | Explicitly equal task-success probabilities despite different weights. |
| Underdetermined | D | Compatible weights allow different comparative answers; equality is not established. |

Each category contains 40 scheduled answers, 20 position-reversal pairs overall,
and 10 such pairs in each pass. At each name assignment, reversing position
preserves the person-name/history association. Switching names preserves the
underlying people, payoffs, skill evidence and semantic key. The evidence-block
order and A/B option order change together; their separate effects are not
identified. C and D keep fixed labels. History order varies across base cases,
not as a separately crossed factor; no history-order invariance claim is made.

Private P/Q identities, keys, case IDs, pass indices and category names never
enter the API request. Both recipients' payoffs, including zeros, appear in each
historical alternative and the current point-choice alternatives.

### Ground truth

Constructed cases stipulate a nonnegative, fixed weight and strict maximization
of `own points + w * your points`. A giving observation establishes a lower bound
on w; a keeping observation establishes an upper bound. Probe keys follow from
**all** compatible weights, not a private point estimate. No historical or current
choice is an exact value tie. For underdetermined cases this excludes the isolated
boundary value without removing either possible strict choice.

The special constructed-case instruction disallows inventing a prior over the
unknown weights. When compatible assignments imply different answers, the key is
D. This is a stipulated identifiability check, not a claim that a natural-language
observer can never make a probabilistic inference from incomplete evidence.

Ability controls give exact success probabilities for a genuine attempt with
sufficient time, explicitly independent of the point choices. These are deliberately
easy dimension-following controls, not an independent validation of social inference
about ability. The future natural stories supply no numeric weights or success
probabilities. Passing these controls is necessary supporting evidence, not
sufficient construct validation of those stories.

## Frozen development gate and denominators

A position pair succeeds only when **both** reversed presentations yield the
correct semantic answer. A wrong answer, invalid output, or missing response
makes that pair unsuccessful. Report single-answer accuracy, joint accuracy,
C and D counts, invalid/missingness, and position, name and repeat disagreement.
Every disagreement statistic includes its comparable-pair denominator and the
scheduled-pair denominator; missing pairs cannot silently improve agreement.

The batch passes only when all 240 responses have been recorded, and:

* In **each of the six categories, in each pass**, at least 9 of 10 position
  pairs are jointly correct (90%). No overall average can conceal a failed
  category or pass.
* D occurs on at most 10 of the 200 determined-answer presentations (5%).
  Correct D answers in the underdetermined category do not count as abstention errors.

The report also gives the number of base cases with all eight answers correct,
without making perfect base-case recovery an additional gate. A complete batch
is PASS or FAIL; a transport-interrupted batch is INCOMPLETE, not a favorable
reduced-denominator test. Raw records are retained in every case.

Ninety percent is a **chosen finite-set development tolerance**, not an established
validity threshold. It screens out a substantial rate of paired errors before
interpreting a small qualitative pilot. It does not establish a population error
rate below 10%, quantify the error on natural stories, or justify treating five
parameterizations and their repetitions as independent binomial trials. The old
proposal's inference from a 90% observed rate to an error probability below one
in six is not warranted. The intended pilot seeks a large, repeatedly expressed
dissociation; weak/mixed differences should not be rescued by this gate.

PASS means reviewable final-answer performance on these controls. It does not
authorize the pilot automatically. Review the raw explanations and item-level
audit, state any limitations and premise failures, and record the decision before
collecting social items. Explanation coding must be identified as unblinded
assistant/human coding as appropriate, not evidence about hidden model reasoning.

If the gate fails, stop this candidate. Report the failed category and all other
results. Do not rerun until it passes, select a favorable pass/order, or edit the
freeze after seeing answers. Any replacement is a separately disclosed study,
not another attempt to complete this one successfully.

## Transport, provenance and stopping

Retain `claude-sonnet-4-5-20250929`, temperature 0, 256 output tokens and fresh
context per request. The provider's structured output schema has `brief_basis`
followed by `answer` in A/B/C/D. Preserve this property order in serialization.
Accept exactly those keys in order, a nonempty string basis, one text content
block, an exact uppercase answer, and `end_turn`. All other output is unusable,
not recovered using a secondary parser or explanation-based answer.

Make all 240 scheduled requests once, regardless of correctness. Two passes are
part of the schedule, not optional reruns. Use deterministic hash ordering within
each pass, zero SDK retries, no model fallback, and no response-dependent extra
calls. A transport or integrity failure stops collection and preserves what was
received. Do not blindly retry an attempted request whose billing/completion is
unknown. There is no automatic resume. GitHub's Re-run jobs is blocked for
collection; a fresh Run workflow would still be a fresh experiment and must not
be used to repeat this batch.

The freeze binds this plan, source, tests, workflow, complete item JSONL and
**order-preserving request-body JSONL**. Record the actual source commit, workflow
run/attempt, SDK/Python versions, start time, raw request bodies, raw API objects,
returned model, request IDs and token usage. No secret is written to artifacts.
Save outputs before checking integrity. Artifacts include report.json, report.md
and an answer-audit.csv with every scheduled item. Synthetic tests are explicitly
marked `programmed_test_fixture`; their PASS is never counted as model evidence.

## Following pilot: proposed scope, not an enabled collection

Keep the six existing attribution scenarios out of model-facing development.
The intended minimal pilot is the user's focused design: six scenarios x one
cause pair (unable versus unwilling) x three probes x two orders x two name
assignments = **72 requests per pass**, or **144 with two prespecified passes**.
The three probes are point-choice prediction at keep 5 versus give 10, same-task
ability under genuine effort, and different-task ability under genuine effort.
The uploaded draft's extra valuation ratio and 192-request pilot are not silently
adopted. Any expansion must be decided before pilot collection, not after viewing
an unfavorable ratio. This module cannot generate or run either pilot.

The predicted dissociation is greater giving likelihood for the unable-but-tried
person, but greater same-task success likelihood for the able-but-unwilling
person. Different-task ability is a substantive transfer control with no truth
key. Equal, insufficient, reversed and inconsistent responses remain legitimate
results. Do not stipulate away the continuing task-specific incapacity when
asking about ability; do stipulate genuine effort and adequate opportunity.

A future frozen pilot scorer should report all eight semantic answers per
scenario/probe across the two passes. Both directional components must be shown;
an interaction-like difference alone can arise without the intended crossover.
Show scenario-level distributions and presentation sensitivity, not just an
all-correct filter or a request-level significance test. Retain C and D separately.
Any aggregate directional score must include unfavorable and unresolved cells,
with its convention explicit. The replication unit remains six selected scenarios.

Before collection, finalize and audit the natural prompts and scorer and record
the pilot decision. Do not call the same-task prediction a known-answer key. A
positive pilot supports only a described comparative-judgment dissociation under
this protocol, not recovered WTR magnitudes, human-equivalent mechanisms,
training-time modularity, or an internal persistent partner-value variable.

## Running after review

From the repository checkout:

```bash
uv sync --frozen --all-groups --extra eval
uv run python -m wtrbench.paired.ordinal check
uv run python -m wtrbench.paired.ordinal generate
# Only after the study owner accepts this plan and authorizes the bounded batch:
uv run python -m wtrbench.paired.ordinal run --confirm 240
uv run python -m wtrbench.paired.ordinal report
```

The manual **Paired ordinal v2** workflow defaults to `generate` (no model calls).
After merging the reviewed PR, select `collect` and type `COLLECT_240` only for the
one authorized validation batch. Download its artifact rather than pressing
Re-run jobs. No action in this plan schedules or automatically launches a pilot.
No current balance or cost quote has been checked; token usage is saved for a
later factual accounting. Authorization is still needed for paid collection.

## External context (not a validation result)

Wang et al. (ACL 2024), *Large Language Models are not Fair Evaluators*, document
position effects in LLM evaluation tasks; that motivates counterbalancing here,
not a numerical bias estimate for this instrument:
https://aclanthology.org/2024.acl-long.511/

Quillien, Tooby & Cosmides (Cognition 2023), *Rational inferences about social
valuation*, compare human predictions from sparse partner-choice evidence to a
Bayesian ideal observer. This supports treating the original incomplete-evidence
family as meaningful without giving it an unjustified deterministic key:
https://quillienlab.github.io/Quillien%20Tooby%20and%20Cosmides%202023.pdf

Provider structured-output documentation describes output_config.format and
notes that truncation/refusal can still produce unusable output. This runner
retains such responses rather than using the documentation's suggested retries:
https://platform.claude.com/docs/en/build-with-claude/structured-outputs
