# WTR-Bench Design Document
*Working draft, v0.2.0 (September 2026). Open questions are listed per section;
decisions are stated as decisions.*

## 1. Research question and measurement target
Do LLM agents exhibit coherent welfare tradeoff ratios toward described others,
and does that behavior shift with relationship and interaction history in the
directions human WTRs do?

**Decision:** v1 measures *prompted welfare-tradeoff behavior* — the allocation
policy a model expresses when stakes are described in text. It does not claim
to measure latent valuation backed by real consequences ("points" cost a model
nothing), nor to distinguish an agent's own dispositions from its simulation
of human norms. Open question: what manipulations (real compute/token stakes,
counterfactual framings, self-vs-assistant framing) would license stronger
claims in v2.

## 2. Constructs, validity, and predictions
- WTR: weight on target's payoff relative to own; estimated as the switch
  point on a self:other ratio ladder, within the ladder's range.
- **Instrument validation is separate from model results.** Initial v1
  evidence will include: (a) recovery tests showing that the estimator
  recovers synthetic WTR and noise parameters under its assumed
  data-generating model; and (b) comparison of model behavior with
  human-derived directional predictions (kin > stranger; partner > defector;
  helped > neutral > harmed).
- Recovery validates estimator behavior under its assumptions. Directional
  concordance or discordance is a benchmark result, not same-instrument human
  calibration.
- Same-instrument human calibration is future work, so construct validation
  remains provisional in v1. A model that fails a directional prediction
  produces a finding about that model; recovery failure indicts the
  evaluation pipeline.
- Open question: whether the benevolent-misrepresentation studies (stated vs.
  revealed WTR) belong in v1 as study 2 or in v2.

## 3. Factorial design
Implemented grid (see `src/wtrbench/items.py`):
- Relationship (standing): stranger / friend / family member / cooperation
  partner / prior defector.
- History (interaction immediately preceding the decision): helped you /
  harmed you / neither. Crossing with relationship is deliberate; reversal
  cells (prior defector who just helped) are design points, not artifacts.
- Stakes: small / large (base 10 vs. ×100).
- Option order: self-first vs. other-first, fully crossed.
- Names: counterbalanced across six forms. Within a form each cell keeps one
  target name across its entire ladder and both option orders, so each
  switch-point curve describes a single target and order comparisons are
  exactly paired; across the six forms every cell meets every name once, so
  name is fully crossed with cell at the design level.
Planned nuisance factors for v1: currency/unit framing, 3–4 paraphrase
templates. Open questions: deservingness as a design factor vs. bias-panel
condition; whether any cells should be prohibited on coherence grounds.

## 4. Titration ladder
- v1: fixed grid, default 0.2–2.0 in 0.2 steps; exact-payoff validation in
  strict mode; both target and realized ratios stored per item.
- Censoring: always-self patterns are left-censored at the lowest rung —
  nonpositive WTRs are not distinguishable from small positive WTRs below that
  boundary in v1 — and always-other patterns are right-censored at the top
  rung.
  Reported estimates must carry censoring flags. Open questions: conditions
  identifying zero/negative WTR (e.g., costly-spite items); ladder range and
  resolution justification; blocked vs. interleaved administration; repeats
  per rung.
- v1.1: adaptive staircase as a custom Inspect solver.

## 5. Elicitation
- v1: binary forced choice with strict A/B parsing; refusal and format-drift
  handling rules to be specified with the parser.
- The protocol will draw on the Lambda Slider (Qi, Vul, & Powell, 2025). Note
  the current ladder is *not* a Lambda Slider adaptation: that instrument is a
  continuous allocation curve whose position maps to the tradeoff parameter,
  with inequity aversion as a second parameter. A discretized adaptation, and
  joint estimation of tradeoff and secondary parameters, is an open design
  item for v1/v2.
- To specify with the runner: temperature, seeds, repetitions per item,
  system prompt, context isolation between items, retry policy.

## 6. Scoring
- Per cell: switch-point and consistency estimates via methods robust to
  complete separation — penalized (Firth) or Bayesian logistic regression, or
  a direct interval estimate for perfect Guttman patterns. Ordinary logistic
  regression is not acceptable as the only estimator: a perfectly monotonic
  switch (the cleanest possible data) sends its slope estimate to infinity.
- Guttman-style consistency checks on raw choice patterns.
- Definitions required before first run: refusal, format drift, and their
  scoring treatment; nonmonotonic-pattern handling.

## 7. Analysis
- Mixed-effects models over grid cells; clustered bootstrap CIs on model
  contrasts; generalizability-theory decomposition of score variance.
- Open questions to fix before data collection: the experimental unit and
  bootstrap clustering (item vs. cell vs. run); nesting of paraphrase, order,
  decoding, and run variance; confirmatory contrasts and minimum effect sizes
  of interest.

## 8. Perturbation and bias panel
- Nuisance factors (names, order; later currency and paraphrase) should not
  move switch points; measured movement is a finding to report, not noise to
  discard.
- Open questions: how name sets are constructed and validated if name-category
  effects are to be interpreted (how many names per category, established by
  what norming); whether currency is plausibly inert (real currencies differ
  in value connotation) or belongs in the substantive design; the precise
  estimand any "bias" claim would refer to.

## 9. Scope and v1 acceptance test
v1 is complete when the following runs end to end and is reproducible from
the repo: an Inspect task over the generated dataset with strict parsing; a
synthetic-policy harness (known WTR and noise per agent) passing recovery
thresholds (to be set before implementation); at least one real-model run;
and a generated report with switch-point estimates, censoring flags, and
bootstrap CIs, plus provenance (config hash, model versions, seeds).
Cut from v1: multi-turn/agentic settings; cross-language items; the
status/coalition module; the emotion-attribution module (v2: scoring model
predictions against human vignette ratings from US, Indian, and Nigerian
samples).
