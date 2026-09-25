# WTR-Bench Inference Module: Design Document
*Working draft, v0.4 (September 2026). Companion to `wtr-bench-design.md`.
Decisions are stated as decisions; open questions are listed per section.*

**Execution update (2026-09-25):** The researcher has requested validation
of the original measurement task before any pilot. The original 888-item
pilot remains unrun. The 816-request robustness proposal is preserved but
its collection workflow and CLI are disabled; it does not replace the
original research aim. See [validation before pilot](validation-before-pilot.md).

The [216-request known-partner recovery diagnostic](known-partner-recovery-v1.md)
is complete and [audited](recovery-36111049496-review.md). Explicit-weight
recovery passed (72/72 choices; 18/18 fits). History recovery was mixed
(137/144 choices; 24/36 fits), including option-order-sensitive errors and
incorrect explanations behind correct answers. These results do not release
either pilot. Original histories that only
show keeping impose upper bounds; LOW/HIGH separation is a theoretical
prediction, not a known-answer validation criterion. Null effects, reversed
effects and unresolved bounds must remain possible outcomes of an adequately
measured social test.

The original design below and all [development findings](measurement-36099597085-review.md)
remain unchanged. References to preregistration describe an intention;
no external registration has occurred. The [runbook](inference-runbook.md)
records the completed diagnostic, the pilot pause and historical procedures.

**Payoff presentation comparison complete:** the [288-request audit](presentation-36115733552-review.md)
records 138/144 correct original choices versus 139/144 table choices, and
24/36 versus 28/36 recovered fits. Tables reduced explanation errors in the
assistant audit from 38 to 11, but all five wrong table choices state correct
history bounds and current values. Some produce coherent but wrong intervals.
Both displays fail the frozen recovery rule. Stop display iteration; assess
the valuation readout and its error effects before any new collection. The
[prospective plan](payoff-presentation-v1.md) is unchanged and neither pilot
is released.

## 0. What this module adds, and what it does not

Module A (`items.py`) measures the model's **own** welfare-tradeoff behavior.
This module measures what the model **infers about a partner** from evidence
about the partner's behavior: the partner's valuation of "you" (inferred WTR),
the partner's willingness to help, and the partner's ability. Every probe asks
the model to predict the partner. None asks the model to decide for itself.

The first study answers a narrow question: **do models use the information in
someone's choices to predict that person's future behavior, distinguishing
evidence about valuation from evidence about ability or opportunity?**

**Decision:** each prompt supplies the evidence and the question together. The
module therefore measures judgment from supplied evidence. It does not show
that a model maintains and updates a partner-specific estimate across
interactions, and it does not identify whether one internal variable produces
the pattern. Those are the questions the mechanism-recovery study exists for.
Results here should be written up as "responses reflect X beyond Y," with the
rival simple rules named (section 7), not as evidence of a maintained
valuation estimate.

Implementation: `src/wtrbench/inference.py`; tests: `tests/test_inference.py`.

## 1. Evidence families

### 1.1 Attribution: same failed outcome, different causes

The partner was asked for help. Five causes, six scenarios.

| Cause | What the evidence supports | Couch scenario |
|---|---|---|
| `baseline` | Nothing (relationship sentence only) | "Sam is an acquaintance." |
| `unwilling` | Capable, refused: low valuation, competence intact | Was free that day and could easily have done it, but said no. |
| `unable` | Came and tried, failed for a standing reason: willingness demonstrated, competence low | Came and tried, but has a bad back and could not manage it. |
| `constrained` | Set out to help, interrupted: willingness demonstrated, competence uninformative | Was on the way over when their child got sick, and had to turn back. |
| `helped` | Positive valuation, competence demonstrated | Came over and carried it down with you. |

**Decision (v0.2 correction):** `unable` and `constrained` are not "no
valuation update" conditions. Showing up and trying is evidence of
willingness. The design therefore includes a no-evidence baseline, and the
predictions are stated relative to it (section 4). Every `unable` sentence
states that the partner tried and names a standing incapacity (bad back, does
not know the repair, does not understand spreadsheets, weak Spanish, allergic,
knows nothing about the subject), so the incapacity is expected to persist
into the same-task probe and not to bear on the different-task probe. A test
enforces both properties by keyword.

The three failure causes share the outcome sentence within a scenario. The
six confirmatory scenarios (couch, faucet, spreadsheet, translate, dog,
presentation) are independently constructed, with a same-kind and a
different-kind follow-up task each; scenario is the replication unit (section
6). A seventh scenario (boxes) exists only for debugging the pipeline and is
excluded from confirmatory generation by default; results on it are never
reported as held out.

Grid: cause (5) × scenario (6) × relationship (1 in the pilot) = 30 cells.

### 1.2 Constant-aggregate pairs: same totals, different tradeoffs

The partner made two mutually exclusive self-versus-you choices and chose
self both times. The **diagnostic ratio** (smallest gain:loss at which the
partner still chose self, which upper-bounds the partner's WTR toward "you"
under a deterministic utility model) is crossed with the **totals** (partner's
total gain, total denied to "you"). This is the logic of Quillien, Tooby, and
Cosmides (2023), in which partners with identical totals (per the paper, $60
gained and $35 denied) but different tradeoff patterns were judged differently
and elicited different anger.

Two independently constructed numerical sets, a scaling check, and a debug set:

| Set | Role | Diagnostic LOW / HIGH (min ratio) | Totals T1 / T2 (gained / denied) |
|---|---|---|---|
| set0 | construction | 0.5 / 1.0 | 60/35 and 80/75 |
| set1 | construction | 0.4 / 1.25 | 50/25 and 75/60 |
| set0x2 | scaling (set0 doubled) | 0.5 / 1.0 | 120/70 and 160/150 |
| debug | debug only | 0.5 / 1.5 | 40/20 and 90/50 |

**Decision (v0.3):** set0x2 is a stakes-sensitivity comparison against set0,
not a third replication; sets 0 and 1 are reported separately and no
population interval is computed over "three sets." Within a set, totals are
identical within each row and the minimum ratio within each column (tested).
The order of the two choices is counterbalanced. One partner per prompt.

**Decision (v0.3):** the name is held constant across all eight cells of a
set, including both choice orders, and across all five causes of a scenario
(tested). No within-set or within-scenario comparison crosses a name change.
Names rotate across sets, across scenarios, and across forms, with one
exception: a scaling set (set0x2) takes the same name as the set it scales
(set0), so the stakes comparison is not confounded with name.

The two simple rules make different predictions about where the inferred
ratio should sit, and they do not agree that totals are inert. The minimum-
ratio rule uses only the most diagnostic choice; a Bayesian observer with a
uniform prior on w in [0.05, 3] and logistic choice noise (k = 4) updates from
both observations, so in set1 the two HIGH cells differ (one of them has two
observations at 1.25, the other has one at 1.25 and one uninformative one at
5). Predicted switch points, computed from the implemented rules:

| Set | Diag. | Totals | Choices (partner vs you) | Min ratio | Min-ratio rule | Bayesian rule |
|---|---|---|---|---|---|---|
| set0 | low | t1 | 45 vs 5, 15 vs 30 | 0.50 | 0.45 | 0.41 |
| set0 | high | t1 | 30 vs 5, 30 vs 30 | 1.00 | 0.95 | 0.59 |
| set0 | low | t2 | 45 vs 5, 35 vs 70 | 0.50 | 0.45 | 0.41 |
| set0 | high | t2 | 10 vs 5, 70 vs 70 | 1.00 | 0.95 | 0.58 |
| set1 | low | t1 | 42 vs 5, 8 vs 20 | 0.40 | 0.35 | 0.39 |
| set1 | high | t1 | 25 vs 5, 25 vs 20 | 1.25 | 1.20 | 0.69 |
| set1 | low | t2 | 53 vs 5, 22 vs 55 | 0.40 | 0.35 | 0.39 |
| set1 | high | t2 | 25 vs 20, 50 vs 40 | 1.25 | 1.20 | 0.57 |
| set0x2 | low | t1 | 90 vs 10, 30 vs 60 | 0.50 | 0.45 | 0.41 |
| set0x2 | high | t1 | 60 vs 10, 60 vs 60 | 1.00 | 0.95 | 0.59 |
| set0x2 | low | t2 | 90 vs 10, 70 vs 140 | 0.50 | 0.45 | 0.41 |
| set0x2 | high | t2 | 20 vs 10, 140 vs 140 | 1.00 | 0.95 | 0.58 |

The aggregate prediction is therefore stated as **sensitivity to tradeoff
pattern at matched totals** (LOW below HIGH within each row). No ordering of
the totals effect relative to the diagnostic effect is preregistered; whatever
totals effect appears is compared with what each rule predicts.

## 2. Probes

| Probe | Format | Construct | Family |
|---|---|---|---|
| `p_infer` | Ladder: "Now {name} must choose: (A) {name} receives *x* points. (B) You receive 10 points. Which will {name} choose?" | Inferred WTR of partner toward "you" | both |
| `p_will_same` | Binary: you ask {name} for the same kind of task; {name} is free and would be able to do it. Agree or decline? | Predicted willingness (exploratory) | attribution |
| `p_will_diff` | Binary: same, different kind of task | Predicted willingness, transfer (exploratory) | attribution |
| `p_able_same` | Binary: {name} makes a real effort at the same kind of task, with enough time. Manage it or not? | Predicted ability (**required**) | attribution |
| `p_able_diff` | Binary: same, different kind of task | Predicted ability, transfer control | attribution |
| `p_own` | Ladder: Module A's prompt after the evidence | Model's own WTR | off by default |

`p_infer` is primary. It is the Module A ladder with the roles reversed: the
ratio at which the model's predicted choice for the partner switches from
"you" to the partner's own payoff estimates the WTR the model attributes to
the partner.

**Decision (v0.3):** the willingness probes condition on both opportunity and
ability ("{name} is free that day and would be able to do it"), because a
partner who tried and failed for a standing reason could reasonably decline
the same request out of self-knowledge rather than low valuation. The ability
probes condition on effort and time ("makes a real effort ... with enough
time"), so "would manage it" does not measure motivation. Even so, the
willingness probes are exploratory in this pilot; the required dissociation is
carried by `p_infer` and `p_able_same` (section 4).

**Decision (v0.2):** the earlier "ask {name} or ask someone else" probes are
replaced. They depended on assumptions about the unnamed alternative. The
model's own generosity (`p_own`) and costly support in a dispute are deferred:
they add reciprocity, fairness, and dispute-merit questions that the first
study does not need.

Counts, one form, one relationship: full ladder (10 rungs × 2 orders), 1,320;
pilot ladder (0.1, 0.2, 0.5, 1.0, 1.5, 2.0), **888**. The debug batch (boxes
scenario plus the debug set) is 196 items on the pilot ladder. The 0.1 rung
was added after the synthetic check showed every `unwilling` cell left-
censored on a ladder starting at 0.2.

## 3. Counterbalancing

- Option order: fully crossed within every probe; `keyed_option` records the
  letter carrying the partner's own payoff (`p_infer`), "your" payoff
  (`p_own`), or "would agree" / "would manage" (binaries).
- Names: one name per scenario (all five causes) and one per numerical set
  (all eight cells), with set0x2 sharing set0's name. With six scenarios and six names, each cause meets every
  name exactly once within a form (tested), so name is balanced across the
  cause contrasts without needing multiple forms.
- Aggregate choice order: crossed as a design factor.
- Evidence always precedes the probe within a prompt.

## 4. Preregistered predictions

**Two required comparisons, within scenario, both directions required:**

| Measure | Required ordering |
|---|---|
| Inferred valuation (`p_infer`) | `unable` > `unwilling` |
| Same-task ability (`p_able_same`) | `unwilling` > `unable` |

The pattern counts as present only if both hold. One direction alone is
reported as what it is. Both comparisons are between two failure causes with
the same outcome sentence, so nothing in the outcome distinguishes them.

Everything else is descriptive. Contrasts against `baseline` are reported
with intervals, and "unchanged from baseline" is never asserted from a null
difference: a preservation claim would need a stated tolerance, which this
pilot does not set. The exploratory table reports `unwilling` vs baseline
(expected below), `unable` vs baseline (expected at or above, since the
partner came and tried), `helped` vs baseline (expected above), the
willingness probes, and `p_able_diff` (expected flat across causes, as the
transfer control).

Aggregate: LOW below HIGH on `p_infer` within each totals row of each
construction set; set0x2 reported as a scaling comparison against set0.

Minimum effects of interest are set from the debug batch, before the held-out
run, and the debug scenario and set are never described as held out.

## 5. Elicitation and models

- Forced A/B, temperature 0, strict parsing; refusal and format-drift rules
  shared with Module A's runner.
- **One call per item.** Repeated calls at temperature 0 are not independent
  observations and do not count toward uncertainty. Where the API exposes
  token log-probabilities, record the "A" versus "B" log-odds at the answer
  position as well.
- Pilot panel: one or two instruction-tuned models. Reasoning models, if
  added later, are reported separately.
- Context isolation between items; no system prompt beyond format.

## 6. Scoring and the unit of analysis

- `p_infer`: a Guttman threshold fit per cell. Predicted keyed response
  (partner takes own payoff) iff ratio > w; candidates are the gaps between
  rungs plus one below the lowest and one above the highest; the fit keeps
  the candidates with the fewest misclassifications. Three outcomes:
  **identified** (one interior best candidate: interval = that gap, point
  estimate = its geometric midpoint); **censored** (one best candidate at an
  end: a one-sided bound, no point estimate); **unidentified** (several tied
  best candidates: interval = union of the tied gaps, no point estimate).
  Violations are reported per cell. An always-A responder is unidentified at
  every cell; it does not receive a number.
- **Contrasts between ladder cells are decided from intervals, never from
  point estimates.** `a − b` is positive only if a's whole interval lies at
  or above b's, negative only if the reverse, and otherwise undetermined. A
  censored cell therefore enters as a bound, and a bound can still decide a
  contrast: a refusal left-censored at 0.1 against an interior 0.5–1.0 is a
  determinate positive with a minimum magnitude of 0.4. Two cells in the same
  gap are undetermined, not equal. A point difference is reported alongside
  only when both cells are identified.
- Binaries: the keyed proportion per cell. With one call per item and two
  option orders, each binary probe has **two observations per cell**, so a
  cell proportion is 0, 0.5 or 1. The scenario-level contrast is what carries
  information; six scenarios give twelve observations per cause per probe.
- **Unit of analysis: the scenario (attribution) or the numerical set
  (aggregate).** Each summary reports, over units: how many contrasts carry
  the predicted sign, how many are undetermined, and the median point
  difference with a percentile bootstrap over the identified units. With six
  scenarios the intervals are wide by construction; the fix is more
  scenarios, not more calls.
- Only the preregistered comparisons carry a predicted sign and a consistent
  count. Totals effects, stakes (set0x2 vs set0), every contrast against
  baseline, the willingness probes, and the transfer control are descriptive:
  differences are reported, and equality is never scored as a successful
  prediction.
- Nuisance checks: option order and choice order are reported, not discarded.
- The scorer refuses duplicate responses for an item rather than silently
  keeping one.

## 7. Rival simple rules and the synthetic-responder check

Implemented in `synthetic.py`; run with `python -m wtrbench.pilot synthetic`.
The responders are **rival explanations**, not a validation target. The
minimum-ratio rule is a heuristic a model could follow without maintaining any
valuation estimate, and it passes the aggregate comparison by construction.
The Bayesian rule is restricted to the numeric family and has an explicit
prior, noise model and prediction rule (section 1.2). Attribution responders
are programmed profiles; recovering them validates the measurement pipeline,
not any psychological interpretation.

| Responder | Rule |
|---|---|
| theory + min-ratio | Attribution: the theory's profile. Numeric: threshold just below the smallest selfish ratio |
| theory + Bayesian | Attribution: same. Numeric: posterior predictive, both observations update |
| theory + totals | Attribution: same. Numeric: inferred ratio decreases in total denied, pattern ignored |
| cause-blind + min-ratio | Attribution: any failure lowers everything by the same amount |
| flat + min-ratio | Attribution: evidence ignored; every cause looks like baseline |
| order-follower | Always A |
| random | Uniform |

Recovery on the pilot ladder (888 items, deterministic responders):

| Responder | valuation `unable`>`unwilling` | ability `unwilling`>`unable` | LOW<HIGH per set |
|---|---|---|---|
| theory + min-ratio | 6/6 | 6/6 | 2/2, 2/2, 2/2 |
| theory + Bayesian | 6/6 | 6/6 | 2/2, 2/2, 2/2 |
| theory + totals | 6/6 | 6/6 | 0/2, 0/2, 0/2 |
| cause-blind | 0/6 (6/6 undetermined: same gap) | 0/6 | 2/2, 2/2, 2/2 |
| flat | 0/6 | 0/6 | 2/2, 2/2, 2/2 |
| order-follower | 0/6 (unidentified at every cell) | 0/6 | 0/2 (undetermined) |
| random | 1/6 | 3/6 | scattered |

The pipeline reproduces each rule's programmed orderings and does not
manufacture the dissociation from rules that lack it. An always-A responder
is reported as unidentified everywhere with every contrast undetermined; it is
not given a threshold. Two cells that land in the same gap (cause-blind) are
reported as undetermined, not as equal.

**Ladder resolution.** The pilot ladder separates LOW from HIGH under both
numeric rules, and it also separates the two implemented rules from each
other on set1's HIGH cells: the min-ratio threshold there is 1.20, above the
1.0 rung, and the Bayesian threshold is 0.69 / 0.57, below it, so the two
rules answer that rung differently. What the ladder does **not** resolve is
the Bayesian rule's small predicted totals difference within set1 (0.69 vs
0.57, both between 0.5 and 1.0). A null totals effect on this ladder is
therefore not evidence against the Bayesian rule; a finer ladder between 0.5
and 1.0 would be needed for that, and it is a follow-up, not a pilot
requirement.

## 8. Pilot plan and budget

Tooling: `run.py` (one call per item, temperature 0; the parser accepts only
a full-string `A`, `B`, `(A)`, `(B)`, `A.`, `B.` with optional quote or
asterisk wrappers, and records anything else as missing, never coerced; an
existing output file is refused unless `--resume` is given, in which case
only unanswered items are called, and a `.config.json` beside the output
records the model, generator settings and a hash of the item set, which must
match on resume),
`score.py` (Guttman threshold per ladder cell with censoring and violation
counts; cell proportions for binaries; the required and exploratory
contrasts; percentile bootstrap over scenarios), `synthetic.py`, and
`pilot.py` as the command line:

    python -m wtrbench.pilot synthetic          # recovery table, no API
    python -m wtrbench.pilot debug  <model>     # 196 items: boxes + debug set
    python -m wtrbench.pilot pilot  <model>     # 888 items: confirmatory, one form

1. Run `synthetic` and confirm the table in section 7 reproduces.
2. Run `debug` on one model. Read the raw responses in the JSONL, not just
   the report: check what the unparsed answers look like, whether ladders
   switch inside the range or sit censored or unidentified, and the violation
   counts. Set minimum effects of interest from these cells. These results
   are exploratory and are never described as held out.
3. Freeze: generator hash, the predictions in section 4, the scoring code.
4. Original proposal: run `pilot` on one or two models, **888 calls per model**.
   This remains unrun; both it and the later robustness proposal are paused
   pending measurement validation. Billing depends on the model and account.
5. Report: the two required contrasts per scenario (six rows each), the
   aggregate contrasts per set, exploratory contrasts, and the nuisance checks
   (option order, choice order). Two figures: `p_infer` by cause with one line
   per scenario; `p_infer` by diagnostic × totals with one panel per set.

## 9. Use in the essay

Add a short preliminary-results section before the mechanism proposal.
State what was measured (judgment from supplied evidence, one prompt per
item), show the two figures, and let the limitation motivate the mechanism
study: even a clean result here is compatible with the model computing each
prediction separately from the same prompt, which is why the recovery study
is needed. Mixed results serve that purpose as well as clean ones.

## 10. Open questions

- Add `friend` as a second relationship in the confirmatory run, or hold at
  `acquaintance`.
- A finer ladder between 0.5 and 1.0 if the numeric rules are to be
  distinguished from each other.
- A generous-partner mirror of the aggregate family.
- Paraphrase variants of the probe wording.
- Log-probability scoring for APIs that expose it, as a second measure
  alongside the sampled letter.
- Inspect integration, once the plain runner has produced a first result.
