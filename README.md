# WTR-Bench

![CI](https://github.com/msblanders/wtr-bench/actions/workflows/ci.yml/badge.svg)

**A psychometric benchmark for welfare-tradeoff consistency in LLM agents — in development.**

Do LLM agents exhibit coherent welfare tradeoff ratios (WTRs) toward other agents — and does their prompted allocation behavior shift with relationship and interaction history in the directions human WTRs do? WTR-Bench treats that as a measurement problem: the goal is for every model score to ship with the machinery behind it — switch-point estimates from titration ladders, consistency checks, variance decomposition across prompt perturbations, and bootstrapped confidence intervals — so that differences between models are claims that can be defended.

The welfare tradeoff ratio is a well-characterized construct from evolutionary psychology: the weight an agent places on another's welfare relative to its own, which in humans moves lawfully with kinship, cooperation history, and stakes. **What validates the instrument is not any particular model result.** Initial validity evidence will come from two sources: recovery tests against synthetic response policies with known WTR and noise parameters (the estimator must recover what was planted, under its assumed data-generating model), and comparison of model behavior against human-derived directional predictions (kin > stranger; partner > defector). Same-instrument human calibration — humans completing an equivalent instrument — is future work, so construct validation remains provisional in v1. A model that fails the directional predictions is a *finding* about that model; the instrument is indicted by recovery failure.

## Status — pre-alpha (September 2026)

| | |
|---|---|
| **Implemented** | Typed, deterministic item generation over the full design: 30 substantive cells (relationship × recent-interaction history × stakes) × 10-rung ratio ladder × 2 option orders = 600 items per form, in six counterbalanced forms (3,600 items total). Within a form, each cell keeps one target name across its whole ladder and both option orders; across forms, every cell meets every name. Exact-payoff validation (strict mode), argument validation, content-addressed item IDs (hash covers the rendered prompt), and 13 tests pinning grid coverage, target continuity, counterbalancing, determinism, ID semantics, and payoff integrity. Package builds; lint, type, and test checks run in CI. |
| **Design requirements drafted** (see [design doc](docs/wtr-bench-design.md)) | Elicitation protocol; switch-point scoring (penalized/Bayesian logistic or interval estimate, with censoring rules); analysis plan (mixed models, clustered bootstrap, generalizability decomposition); bias panel. Requirements, not yet full specifications: estimators, parser rules, clustering units, and recovery thresholds remain to be fixed. |
| **Planned for v1** | An end-to-end vertical slice: [Inspect](https://inspect.aisi.org.uk) task with strict A/B parsing, synthetic policies with known parameters, recovery tests, and one generated report with uncertainty. Currency and paraphrase perturbation factors. |

No model results are reported yet.

## Design at a glance

- **Items:** forced-choice payoff divisions. Relationship (stranger / friend / family member / cooperation partner / prior defector) and immediately-preceding interaction (helped / harmed / neither) are crossed factors, so reversal cells (a prior defector who just helped you) are deliberate design points. Option order is fully crossed. Names are counterbalanced across six forms: within a form, every switch-point curve describes a single named target across the whole ladder and both orders; across forms, name is fully crossed with cell.
- **Titration:** each cell is probed across a self:other ratio ladder (default 0.2–2.0). Boundary patterns are censored: an always-self pattern is left-censored at the lowest rung — nonpositive WTRs cannot be distinguished from small positive WTRs below that boundary — and an always-other pattern is right-censored at the top rung.
- **Elicitation (planned):** the v1 protocol will draw on the Lambda Slider instrument (Qi, Vul, & Powell, 2025); the current ladder is a binary forced-choice titration, and a discretized continuous-allocation adaptation is an open design item, not yet implemented.
- **Scoring & inference (design requirements):** switch point and consistency per cell via estimators robust to perfect separation; Guttman-style consistency checks; mixed-effects models over the grid; clustered bootstrap CIs on model contrasts; generalizability-theory decomposition of score variance.
- **Measurement target:** v1 measures *prompted welfare-tradeoff behavior* — the allocation policy a model expresses under described stakes — not latent valuation backed by real consequences. That distinction, and what would license stronger claims, is discussed in the design doc.

## Development

```
uv sync --all-groups            # add --extra eval for inspect-ai + anthropic
uv run pytest && uv run ruff check . && uv run mypy src
```

After first sync, commit `uv.lock` so CI resolves pinned dependencies.

## Author

[Mitchell Landers](https://scholar.google.com/citations?user=NeyqJzUAAAAJ) — PhD (Psychology, University of Chicago); social emotions, psychometrics, and the measurement of evaluative dispositions in humans and machines. [msblanders.github.io/website](https://msblanders.github.io/website/)

## References

- Qi, Vul, & Powell (2025). *PLOS ONE* — the Lambda Slider instrument the elicitation design draws on.
- Tooby, Cosmides, Sell, Lieberman, & Sznycer (2008) — welfare tradeoff ratio theory.
- Miller (2024), "Adding Error Bars to Evals" — the statistical stance this benchmark takes seriously.

## License

MIT.
