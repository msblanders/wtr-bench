# Paired natural v3.2: frozen validation plan

Specified 25 September 2026 UTC, before any collection with this instrument.
Prospective GitHub specification, not an external preregistration. v3.0 and
v3.1 were reviewed before collection and revised into this plan; neither was
collected and neither has results. v3.2 differs from v3.1 in three
pre-collection corrections recorded in section 11. paired-ordinal-v2 (run 36190042216) **failed** its gate
and remains recorded as a failure of that numerical inference-and-response
procedure. Nothing here reinterprets it.

**280 scheduled requests, once, after this plan, its freeze and its workflow
are committed and the plan is approved. A PASS makes the social pilot
eligible; it does not authorize it (section 7).**

## 1. What v2 did and did not show

v2's two ability categories supplied explicit numerical success probabilities
and were 40/40; that shows premise-following, not qualitative ability
inference. Its discriminating category required the same interval inference
as the categories that failed, and passed. Row 207 (both certain to keep,
answered "insufficient") is an error under the stated task; whether wording
contributed was not tested. Rows 80 and 125 are coherent under a uniform
posterior over each interval, an assumption the task excluded; that is a
useful distinction between an arithmetic slip and an unstated inference rule,
not a reason to change any v2 score. Quillien, Tooby and Cosmides (2023) use
an empirically derived prior and a noisy choice model; they do not license a
flat-prior key.

So: v2 is a failure of that numerical procedure. It is neither evidence that
computation explains every v2 error nor evidence that qualitative inference
works. This plan makes no claim about qualitative inference until it is
tested.

## 2. What this instrument measures, and what the gate can check

The response is a **comparative social judgment elicited with a brief
explanation**: which of two described people is more likely to make a stated
choice (give you ten points rather than keep a smaller amount) or to manage a
stated task. No weight is recovered and no internal representation is
established.

A gate can check only what a prompt entails. Every gated key in v3.2 follows
from an explicit **stipulation** in the prompt: a standing rule for the
allocation, stipulated equal or unequal chances at the task, or stipulated
absence or randomness of information. Descriptions of past helpfulness or
neglect appear in the gated categories only as **distractors** (regard cues
that align with, conflict with, or are absent from the stipulated key). The
inference from deeds to a prediction is not a key anywhere; it is carried as
an ungated exploratory category with an expected answer (section 3).

Passing therefore shows: the model follows a stated rule to a comparative
answer, preserves stipulated equality, abstains under stipulated
insufficiency, and follows the requested dimension when regard and ability
cues conflict. It does not validate the natural-scenario construct or show
that the model infers regard or ability from unstipulated events.

## 3. Materials

Seven categories, five base cases each. Regard cues are short warm or cold
sentences about the person's past treatment of you.

| Category | Gated | P | Q | Probe | Key |
|---|---|---|---|---|---|
| policy_determined | yes | exception-free rule: always gives; cue warm (cases 1–2), cold (3–4), none (5) | exception-free rule: always keeps; cue cold, warm, none | valuation | P |
| policy_equal | yes | same exception-free rule as Q (always gives, cases 1–3; always keeps, 4–5); cue warm | same rule; cue cold | valuation | C |
| insufficient | yes | no information (1–3) or a badge number stipulated random (4–5) | same form, different number | valuation | D |
| ability_conflict | yes | cue warm | cue cold; joint stipulation: Q far more likely to manage the task, attitudes irrelevant | ability | Q |
| ability_equal | yes | cue warm | cue cold; joint stipulation: equal chances, attitudes irrelevant | ability | C |
| valuation_distractor | yes | exception-free rule: always gives; cue warm | exception-free rule: always keeps; cue cold; joint stipulation: Q far more likely at the task | valuation | P |
| regard_deeds | **no** | costly deed plus statement of regard | chosen neglect plus statement of indifference | valuation | none (expected P) |

The allocation rules are stated as exception-free ("whenever offered the
exact choice described below, always gives / always keeps, without
exception"), so opposite rules entail opposite actions and identical rules
entail equal giving likelihood, including equal at zero. "Reliably follows a
rule" was rejected because two reliable followers need not have equal
compliance. This wording is confined to the constructed controls; it never
appears in the exploratory items or the pilot.

ability_conflict and valuation_distractor share the regard cues and the
ability stipulation; the valuation category additionally supplies the two
allocation rules. They are complementary dimension-following controls, not a
matched-evidence, question-only contrast: answering "who is nicer" on every
probe fails the first, answering "who is more capable" fails the second.
policy_determined cases 3–4 put the warm cue on the person stipulated to
keep, so "who is nicer" fails there too. policy_equal and ability_equal put
differing cues on people stipulated equal, so regard leaking into the answer
produces a false ordering. The matched-evidence, question-only comparison
belongs to the pilot, where both probes read the same social evidence.

The insufficient category stipulates absence or randomness rather than
relying on background facts an observer might treat as cues. Regard cues and
deeds use no numbers; the only digits in any prompt are the fixed 5 and 10
and the badge numbers stipulated random (enforced by a test). None of the six
held-out pilot scenarios or their follow-up tasks appear (enforced by a test).

The regard_deeds category is the bridge to the pilot: it asks the model to
generalize from events whose implications are not stipulated. Its answers are
reported with the same position, name and repeat comparisons, against the
expected answer, and can never affect the gate.

## 4. Prompt and options

Preamble: "{first} and {second} are two people you know. Answer using only
the information given below. Choose A or B if the information supports one
of them being more likely. Choose C only if the information supports their
being equally likely. Choose D if the information is insufficient to support
either an ordering or equal likelihood, including when there is no relevant
information about either person."

Options: (A) first-named; (B) second-named; (C) "The information supports
their being equally likely."; (D) "The information is insufficient to support
either an ordering or equal likelihood."

C means supported equality, not failure to distinguish. D covers absent,
incomplete and conflicting information, so a natural-scenario answer of
"relevant but not enough" has a home. Precedence when nothing relevant is
given about either person is stated in the preamble: D. `render_pair` in
`src/wtrbench/paired/natural.py` builds this text; any later pilot must call
it unchanged.

## 5. Presentations and schedule

Name assignment (Sam/Priya to P/Q) × presentation order (named first and
option A), bound in that order. Two passes with the same 140 prompts in
different fixed hash orders. 35 base cases × 2 × 2 × 2 passes = 280 requests
(240 gated, 40 exploratory). **Distinct prompts: 132.** Six categories have
20 distinct prompts each, shown twice. The insufficient category has 12 across
its 40 requests: its no-information sentence is identical for both people, so
exchanging names and positions repeats the display, and cases with the same
payoff repeat each other; eight of its prompts occur twice, two four times and
two eight times. This is disclosed rather than counted as 140 distinct
problems, and repeated presentations are never treated as independent
evidence. Requests carry no key, category, gated flag or repetition index.

## 6. Gate (frozen)

Identical in form to v2. Unit: a question (both presentation orders within
one name assignment and pass); jointly correct means both orders returned the
keyed semantic answer. Over the **six gated categories only**:

- ≥ 9/10 jointly correct questions in every gated category in each pass;
- D on determined-answer presentations ≤ 10/200 (insufficient excluded);
- all 280 scheduled requests are accounted for: 240 belong to the
  six-category gate and 40 to exploratory reporting, whose answers never
  enter the gate. (The inappropriate-D denominator is 200 and the
  stipulated-equality denominator is 80 by design.)

Also reported, not gated: false strict orderings (A or B) on the 80
stipulated-equality presentations; position, name and repeat disagreements
per category; the exploratory category's agreement with its expected answer,
labelled `joint_as_expected`, never `joint_correct`.

Coverage limit: the gated D cases test absent or explicitly random
information. They do not independently validate the handling of relevant but
mixed or inconclusive evidence, which the pilot may elicit; that is reported
as a limitation, not answered by another control.

The 90% threshold is a **chosen development tolerance** for this instrument
and model. It is not a population error bound and says nothing about the error
rate on natural scenarios.

## 7. Decision rule, fixed in advance

- **PASS:** the social pilot becomes **eligible**. It is **authorized** only
  by a separate recorded decision after its own plan, complete prompts and
  scorer are committed as `paired-pilot-v1`. That plan is not part of this
  package. Its default scope is the last reviewed design: six held-out
  scenarios, the unwilling/unable pair, three probes (valuation at keep 5,
  same-task ability, different-task ability), name × position × two passes,
  144 requests. A second valuation payoff is not included unless the pilot
  plan justifies it and it is approved there.
- **FAIL:** this candidate and this round of development stop. The article is
  written as a methods account from the v2 and v3.2 records. A fail does not
  establish that every qualitative paired instrument fails; a pass does not
  establish the social hypothesis.

The scorer reports `pilot_authorized: false` under every outcome; eligibility
is stated separately.

## 8. Collection and stopping

Pinned `claude-sonnet-4-5-20250929`, temperature 0, 256 output tokens, fresh
context per request, the existing API-enforced JSON (`brief_basis` then
`answer` in A/B/C/D), strict acceptance, no SDK retries, no fallback, no
correctness-triggered extra calls. All 280 calls are made regardless of
correctness. Integrity failures stop collection with partial records
preserved. GitHub re-run is refused. `--confirm 280` is required.

## 9. Software checks, described as what they are

The test oracle derives every gated key from the displayed stipulation
sentences and does not import the material pools or call the production
truth function. A stress test swaps the give and keep rule templates in
memory and confirms the oracle then disagrees with the production keys on
all 40 policy_determined items, which the v3.0 oracle could not do. This
establishes consistency between rendered stipulations and keys. It is a
finite template parser, not a semantic reasoner: it cannot establish that a
stipulation is a good control, and its earlier acceptance of "reliably" is
the reason textual review remains necessary.

## 10. Cross-references

- v2 plan: `docs/paired-ordinal-v2.md`; v2 run 36190042216; v2 post-collection
  review as supplied to the researcher (not in the repository at baseline).
- Implementation: `src/wtrbench/paired/natural.py`; tests:
  `tests/test_paired_natural_v3.py`; samples: `docs/paired-natural-v3.2-samples.md`;
  freeze: `protocols/paired-natural-v3.2.json`; workflow:
  `.github/workflows/paired-natural-v3.2.yml`.

## 11. Pre-collection revision log

- v3.0 → v3.1: keys moved from plausible inference to stipulation; C/D
  semantics revised; exploratory deeds category separated; oracle rebuilt
  on displayed text; decision rule made consistent; pilot default scope set
  to the last reviewed 144-request design.
- v3.1 → v3.2: allocation rules made exception-free (equality keys were not
  entailed by "reliably follows"); the dimension-control description
  corrected (they share evidence but are not question-only contrasts); the
  distinct-prompt explanation corrected (duplication is in `insufficient`,
  not the equality controls); exploratory pair counts labelled
  `joint_as_expected`; denominators stated as designed. No item, category or
  gate changed beyond the rule wording.

- Deployment review (25 September 2026, before collection): corrected the
  generated Markdown report's remaining stale attribution of duplicate prompts
  to the equality categories. It now agrees with section 5 and the existing
  per-category test. Corrected two stale v3.1 references in sections 2 and 7.
  The existing manifest test now verifies the committed freeze and exports
  the complete offline schedule, so CI exercises both check and generate.
  Prompts, item IDs, private keys, schedule, request bodies and gate are
  unchanged from the submitted v3.2 package; only documentation/report prose,
  the software check, and corresponding source hashes changed.
