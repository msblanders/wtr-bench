# WTR-Bench: audit of the fixed Qwen thinking extensions

Run: [36281301593](https://github.com/msblanders/wtr-bench/actions/runs/36281301593).
Review date: 2026-09-26 Pacific / 2026-09-27 UTC.
Collection commit: `0b1f88787f031d43e52953807852f5c03fee4545`, attempt 1.
Archive paths below refer to the complete review bundle; selected machine-readable
[comparison data](../results/thinking-36281301593/comparison.json) and verification summaries
are also committed here.

Both jobs completed successfully. This review made no model calls and altered no
collected record, frozen protocol or repository source.

## Finding

**Qwen3-32B thinking reproduced the primary ordinal behavioral pattern:** all
48 giving responses favored the person who tried but was unable; 41/48 same-task
ability responses favored the capable refuser and seven abstained. Both predicted
net directions occurred within all six scenarios, meeting the prospectively fixed
descriptive criterion. There were 41/48 matched predicted crossovers, with no
reverse crossovers.

**Qwen3-14B thinking improved mainly on ability and did not meet the six-scenario
criterion.** It favored the capable refuser in 43/48 ability responses, but selected
the unable/tried person on giving only 5/48 times and abstained on 43/48. It had
4/48 matched predicted crossovers and both net signs in 4/6 scenarios.

The exact final-answer pattern is independently verified below. Neither outcome
identifies an internal welfare-tradeoff variable. The earlier negative Qwen
non-thinking result stays in the comparison. The extensions were specified after
that result, with new configurations fixed before collection, on the same reused
six scenarios rather than fresh held-out scenarios.

## Four-configuration comparison

All response denominators are scheduled items, not selected valid subsets. Giving
means selecting unable/tried; same-task ability means selecting able/refusing.
A matched crossover requires both selections on the same scenario/name/order/pass.

| Configuration | Giving: predicted choice / 48 | Giving D / 48 | Ability: predicted choice / 48 | Ability D / 48 | Matched crossovers / 48 | Scenarios with both net signs / 6 |
|---|---:|---:|---:|---:|---:|---:|
| Sonnet 4.5, original | 48 | 0 | 46 | 2 | 46 | 6 |
| Qwen3-14B, non-thinking | 4 | 38 | 4 | 38 | 0 | 0 |
| Qwen3-14B, thinking | 5 | 43 | 43 | 5 | 4 | 4 |
| Qwen3-32B, thinking | 48 | 0 | 41 | 7 | 41 | 6 |

The old 14B giving distribution also contains four opposite-direction choices and
two C responses; its ability distribution contains six opposite-direction choices.
Neither new thinking condition selected the opposite direction on either primary
probe. That does not make abstentions correct or remove them from the denominator.

The 14B primary D count fell from 76/96 to 48/96, but this was driven by ability:
ability D fell 38→5 while giving D increased 38→43. The 32B primary D count was
7/96. The predeclared categories are therefore:

- 14B: `D_lower__six_scenario_criterion_not_met`.
- 32B: `D_lower__six_scenario_criterion_met`.

There is no uniform model-size gradient: 14B thinking made 43 predicted ability
choices versus 41 for 32B, while 32B differed sharply on giving. These small,
selected sets do not support a population-level difference or a scaling law.

## Scenario-level primary results

Each cell contains eight scheduled responses. In the new conditions, every primary
response not counted as the predicted choice is D; there are no C, invalid or
missing primary responses.

| Scenario | 14B giving / 8 | 14B ability / 8 | 14B crossovers / 8 | 32B giving / 8 | 32B ability / 8 | 32B crossovers / 8 |
|---|---:|---:|---:|---:|---:|---:|
| Couch | 2 | 8 | 2 | 8 | 8 | 8 |
| Faucet | 1 | 8 | 1 | 8 | 6 | 6 |
| Spreadsheet | 0 | 7 | 0 | 8 | 8 | 8 |
| Translation | 1 | 8 | 1 | 8 | 5 | 5 |
| Dog | 0 | 8 | 0 | 8 | 8 | 8 |
| Presentation | 1 | 4 | 0 | 8 | 6 | 6 |

The 14B presentation scenario has both net signs but no matched crossover: the
single predicted giving answer and the predicted ability answers occur on different
forms. This illustrates why the six-scenario indicator is reported together with
all matched crossovers, rather than being treated as a standalone success score.

## What the explanations add

I read all **288 final brief bases**, each a distinct prompt/final-output group,
without blinding to the answers. No exact-output duplication was reused. I also
read **15 selected separate reasoning traces**: three 14B and twelve 32B traces,
including every 32B same-task D answer. The selection and item IDs are recorded in
`audit/explanation-review-summary.json` and each condition's `explanation-notes.jsonl`.
This is a post-collection assistant review, without an independent human coder or
validated error codebook. Labels overlap and are not a new quantitative endpoint.
The other reasoning traces were retained and checked for presence, not read in full.

**14B's giving abstentions largely concern cross-context inference.** All 43 D brief
bases treat the helping history as insufficient evidence for the later points
choice. For example, the second couch/name-0/order-0 response (14B G018,
`paired-pilot-v1-5daae9003c3737fe2d63`) contrasts inability with refusal, but says
there is no direct evidence about willingness to give points. Its trace entertains
the willingness inference before rejecting its application across contexts. The
same prompt's first pass (G017) chooses the predicted person after weighing that
inference against abstention. This suggests a difference in what evidence the
response treats as sufficient; it does not show that 14B cannot describe the
unable/unwilling distinction. The social items have a prediction, not stipulated
correct answers, so these giving abstentions are not automatically scoring errors.

**32B's giving explanations usually make the intended willingness inference.**
For the first couch giving response (G017, `paired-pilot-v1-b56ac19be99f445b0efa`),
the final basis links the attempt despite a physical limitation to willingness to
assist. On the ability question the preferred person flips because the limitation
persists and effort is stipulated for both. Thus the primary answers do more than
pick the same favorable character on every question.

The rationale is not identical in every case. In the second dog/name-1/order-0
giving response (32B G046, `paired-pilot-v1-c2220b1f448f77fcdd86`), the final basis
invokes possible guilt and a desire to compensate after failed dog care. This
additional, unstipulated inference yields the predicted choice too. Correct-direction
answers are compatible with multiple psychological accounts, including task-specific
semantic rules and compensatory expectations.

**All seven 32B ability abstentions treat the capable refuser's knowledge as unknown.**
They occur in faucet (2), translation (3) and presentation (2). The stories say the
refuser “could easily have done it.” Several traces reinterpret that as having time
rather than having the relevant skill, or acknowledge possible ability and then
reject it as unstated. These are premise-interpretation failures relative to the
intended ability statement, not opposite-direction judgments. The same pattern
appears in the five 14B ability abstentions. One additional 32B predicted-direction
basis (G105) calls knowledge unspecified. Occasional misdescriptions remain even
when the selected letter matches the prediction; no letter was repaired from text.

## The different-task limitation remains

| Configuration | Unable/tried | Able/refusing | Equal C | Insufficient D |
|---|---:|---:|---:|---:|
| Sonnet original | 9 | 3 | 9 | 27 |
| Qwen14B non-thinking | 0 | 0 | 1 | 47 |
| Qwen14B thinking | 0 | 0 | 3 | 45 |
| Qwen32B thinking | 9 | 0 | 6 | 33 |

Every row totals 48. The 32B selection of unable/tried occurs in couch→application
(2), faucet→ride (2), spreadsheet→plants (2), dog→faucet (2) and
presentation→furniture (1). These brief bases use willingness, commitment or
reliability to predict success even though both people are stipulated to make a
real effort. Some tasks may invite a diligence reading, but the dog→faucet and
presentation→furniture selections show this problem also occurs on clearer skill
changes. The clean abstentions seen on those tasks in Sonnet did not replicate
uniformly in 32B. The primary dissociation should not be described as complete
selectivity across all three probes.

The C explanations also sometimes infer equality from absence of a described
relevant difference, reopening the intended distinction between positive evidence
of equality and insufficient information. These responses are preserved, not
recoded as D. Do not use this probe to claim a clean general ability factor.

## Presentation and repetition

Each entry below is disagreements / 24 comparable and scheduled pairs. The pair
comparisons overlap; none is an independent-scenario sample size.

| Condition | Probe | Name | Order | Repeat |
|---|---|---:|---:|---:|
| 14B thinking | Giving | 5 | 5 | 5 |
| 14B thinking | Same-task ability | 3 | 5 | 3 |
| 14B thinking | Different-task ability | 3 | 3 | 3 |
| 32B thinking | Giving | 0 | 0 | 0 |
| 32B thinking | Same-task ability | 5 | 7 | 5 |
| 32B thinking | Different-task ability | 14 | 11 | 8 |

All 32B giving judgments are stable across the scheduled names, orders and repeats.
Ability and different-task judgments are less stable. Because these conditions
sample at temperature 0.6, name/order mismatches also contain sampling variation;
they cannot all be called causal name/order effects.

## Technical and provenance audit

- Exact GitHub ZIP digests match; all **41 internal artifact checksums per condition**
  match, as do all **25 frozen source hashes per condition**.
- Both artifacts preserve the original 144 item objects and identical system/user
  messages and final schema. Their item stream is byte-identical to Sonnet's.
- All 290 responses, including two canaries, are HTTP 200, correctly identified,
  uniquely identified within condition and finish with `stop`. Both canaries return
  valid JSON plus separate reasoning; both happen to answer A, but correctness was
  not a gate.
- All 288 social replies pass the original final-answer contract; none is missing,
  malformed or truncated. Each includes nonempty separate reasoning text.
- Independent standard-library analysis reconstructs A/B bindings from the displayed
  names and story, then reproduces all **288 answer mappings, 36 cells, 432 overlapping
  presentation pairs and 96 matched crossovers** without importing the project scorer.
- Frozen-source replay in separate copies reproduces eight output files byte-for-byte:
  report JSON/Markdown, answer CSV and pair audit for each condition. Originals remain
  unchanged. The replay uses the archived scorer in addition to the independent audit.
- No provider fingerprint is supplied. The exposed model IDs and reported FP8 precision
  match, but hosted weight/tokenizer revisions remain independently unverified.
- Provider completion-token counts (including reasoning) range from 316–2,236 for
  14B and 299–2,588 for 32B, well below the 32,768 cap. There is no observed truncation
  explanation for the remaining abstentions.

Provider-reported estimated cost including the canaries: **$0.03330084 + $0.034222
= $0.06752284**, approximately **6.75 US cents total**. Total usage is 99,074 prompt
and 222,053 completion tokens, 321,127 tokens combined. This is the provider's usage
estimate, not an independently checked account invoice.

## Interpretation and next step

The bounded follow-up was informative. The primary ordinal dissociation now occurs
on Sonnet and on an open-weight model's hosted thinking configuration. The two 14B
conditions show that distinguishing task ability and making a cross-context giving
inference can come apart under this instrument. Neither finding identifies why:
reasoning, sampling and token allowance were changed together relative to the old
14B condition; the 14B/32B contrast also changes learned weights and parameter count.
The model's written explanation is not a causal account of its computation.

Qwen3-32B is now a **candidate for the later mechanism study**, not a validated
mechanistic target. First reproduce the behavior on the actual local checkpoint,
precision and serving stack used for activation access. Hosted success does not
automatically transfer to that implementation. The six reused scenarios and single
points tradeoff also do not establish a maintained partner-specific valuation,
a scalar WTR, the model's own preferences, directed relational selectivity, or
broad generalization to other social contexts.

The present note can report all four configurations now. No additional same-item
collection is needed to complete this prospectively specified family. The more
substantive next work is the mechanism-recovery proposal and controlled learner
study already discussed, with the original negative and both extensions retained.

## Suggested results paragraph

On six selected social scenarios, Claude Sonnet 4.5 favored a person who attempted
but was unable to help on future giving judgments in 48/48 responses, while favoring
a capable refuser on same-task ability judgments in 46/48. A fixed Qwen3-14B
non-thinking replication did not reproduce this pattern. In a subsequent
prospectively specified follow-up using the same 144 items per configuration,
Qwen3-14B with thinking selected the capable refuser on 43/48 ability judgments but
mostly abstained on giving (43/48), yielding four matched crossovers. Qwen3-32B with
thinking favored the unable helper on all 48 giving judgments and the capable
refuser on 41/48 ability judgments, yielding 41 matched crossovers and both predicted
net directions in every scenario; the remaining seven ability responses abstained.
Different-task judgments remained mixed. These results establish the predicted
behavioral dissociation in two model configurations on this item set, while leaving
its internal mechanism unresolved. The follow-up changes in reasoning, sampling
and token allowance were bundled, and presentation variants and repeats are not
independent scenarios.

## Reproduction and files

Run `python3 audit/audit.py` from this extracted bundle to recompute the independent
checks and frozen-source replay. It uses Python 3.11+ and the standard library;
no API key, inference call or live network access is required. It recreates only
`reproduced/` and audit outputs, leaving `original/` untouched. Run
`python3 audit/annotate.py` to reproduce the saved, explicitly post hoc review labels.
Neither script reproduces the model generation itself.

- `original-zips/`: both unmodified GitHub ZIPs.
- `original/`: both extracted artifacts with their own hashes and complete frozen source.
- `sonnet-reference/`, `qwen-nonthinking-reference/`: earlier records used for comparison.
- `audit/`: independent script, verification reports, per-item explanations and trace-review disclosure.
- `github-metadata.json`: retrieved run, jobs and artifact metadata.
- `SHA256SUMS.txt`: checksums for this review bundle, excluding itself.

GitHub artifact digests:

- 14B: `f22abbb5e94c7598e9c1fc00061db4e72869126b0373ce9b24b3cb5b51820d53`.
- 32B: `3ad0dc4ac6ea4260d03656ca313458fecac0b8cc6b5bb173614b30897b838cfb`.
