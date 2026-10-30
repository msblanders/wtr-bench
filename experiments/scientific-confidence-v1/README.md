# Scientific confidence v1

This exploratory pilot asks whether an explicit contrastive evidence audit improves an LLM's
probabilities beyond a strong calibration checklist. It is motivated by evidence synthesis:
keeping track of independent studies, comparing explanations, and separating confidence in a
mechanism from predictions of a future result. It is not an Elicit product evaluation or an
affiliated project. Code and protocol were developed with AI assistance.

## Frozen hypothesis and comparison

**Hypothesis:** making a model construct a unique-study ledger, compare each observation with
each explanation's prediction, and aggregate the resulting likelihoods reduces probability error.

The primary comparison is `contrastive_audit` minus `calibration_checklist` in mean squared
Euclidean distance to the exact posterior. Negative values favor the audit. This distance is
the excess expected multiclass Brier loss conditional on the supplied evidence and model.
A generic review is a secondary baseline. An answer-supplied oracle-posterior readout is a
diagnostic of the final prediction step, not a competing reasoning method.

Each main arm uses two calls: a preparatory assessment, then a common final structured response.
The final response receives the full dossier and its own preparation. Every main arm receives
the same mathematical formulas and 1,400 output tokens per call. Actual token usage, time,
truncation, and cost are recorded: this matches budgets, not actual computation. There is no
calculator, retrieval, weight update, reward model, or hidden extended-thinking budget.
The model is fixed to `claude-sonnet-4-6`, temperature 0, thinking disabled, to reuse verified
account access. This is not a claim about the newest model or about training reasoning models.

## Cases and independent verification

32 cases, eight in each stratum: independent replications, randomized/observational contrasts,
unequal precision, and duplicate reports. These strata describe designs, not guaranteed observed
conflicts. No cases are selected based on the model's answers, true mechanism, or observed effects.
Hypothesis IDs are randomly assigned; priors vary. Cases use disjoint random seeds. Each case has
four independent underlying studies, even when eight reports are displayed.

Three mutually exclusive, exhaustive hypotheses predict known Normal means: a constant positive
causal effect; selection bias that produces an observational association but no randomized effect;
or a context-specific causal effect (positive in A and negative in B). All three are supplied to
the model. Data are generated conditional on a mechanism sampled from the stated prior. The
oracle computes likelihoods for unique studies and applies Bayes' rule. A future randomized study
has a hidden sampled outcome and an exactly calculable posterior predictive tail probability.

`cases.json` contains only model-visible inputs. `gold.json` contains generating mechanisms,
future outcomes, strata, and oracle probabilities. Experimental prompts never receive gold.
Only the explicitly labeled diagnostic receives the oracle posterior (not the future probability).
Unit tests compare the oracle with independently multiplied Gaussian densities, check dependence
and order invariance, and verify the Brier-regret identity. No LLM judges the primary outcome.

## Analysis fixed before collection

- Primary: paired case-level difference in posterior regret, with a 10,000-resample percentile
  bootstrap interval. The independent unit is the case, not a report or API call.
- Secondary: predictive probability regret, realized mechanism and future-outcome Brier scores,
  subgroup means, cost, invalid/missing responses, and preparation truncation.
- Bootstrap intervals are descriptive for this small designed mixture, not a claim of general
  scientific efficacy. The pilot is not powered for a specified minimum effect.
- The parser accepts only finite probabilities in [0,1]; sums within 0.005 of 1 are normalized,
  with the correction recorded. Other outputs count as invalid, with no repair/retry.
- Primary paired scores use cases valid in both arms. Attrition is always shown; any differential
  attrition prevents an unqualified efficacy claim. Raw responses remain available.
- All cases are pilot data. There is no posthoc calibration fitted to the evaluation cases.
  A later confirmatory study needs new cases, a separate calibration split, repeated samples,
  a fitted temperature-calibration baseline, operator ablations, and another model.

## Execution and cost control

```bash
python -m unittest discover -s tests -p test_scientific_confidence.py -v
python experiments/scientific-confidence-v1/experiment.py generate --out /tmp/science-pilot
# Requires ANTHROPIC_API_KEY; explicitly makes paid calls:
python /tmp/science-pilot/experiment.py collect --out /tmp/science-pilot --budget-usd 25
python /tmp/science-pilot/experiment.py report --out /tmp/science-pilot
```

224 planned API calls, at most four concurrent requests. The first planned task is also the
infrastructure smoke check; continuation never depends on its probability score. The frozen
source, inputs, and protocol are hashed. No automatic resumption, provider fallback, or API
retries. An infrastructure error halts further sending and preserves partial results. Before
each call the collector reserves a conservative cost using UTF-8 input bytes plus 4,096 tokens
of overhead and the maximum output allowance. Ambiguous failures retain their reservation.
The guard is $25, using $3/M input and $15/M output; no prompt caching or batch pricing is used.
Recorded costs are estimates from returned usage at these prices, not account invoices.

GitHub Actions uses the existing repository API secret without exposing it. Paid execution is
limited to one named run branch, an exact trigger commit message, and run attempt 1. Other
branches only receive the ordinary repository CI. Results are uploaded even on partial failure.
The experiment has its own branch, workflow, and output directory, independent of other pilots.

## What a result would mean

A gain would support this particular inference-time procedure on supplied, correctly specified
models. It would not establish improved scientific discovery, explanation generation, robustness
to omitted mechanisms, literature retrieval, or real-world causal inference. A null result is
useful: an explicit formula plus a strong checklist may already suffice, or arithmetic and
representation may dominate. Examine the frozen raw errors before deciding the next intervention.

If a useful procedure transfers to new cases, the next training experiment can reward proper
probability scores on held-out outcomes. Simulated oracle probabilities can supply a lower-noise
development target. Models must then be tested with misspecified candidate sets and real evidence.
We should not infer that better-looking probability language has improved reasoning.

Sources informing the approach (not evidence this operator works):

- Gneiting & Raftery, proper scoring rules: https://doi.org/10.1198/016214506000001437
- Linguistic Calibration of Language Models, ICML 2024: https://proceedings.mlr.press/v235/band24a.html
- Reinforcement Learning with Calibration Rewards: https://arxiv.org/abs/2507.16806
- Model configuration/pricing: https://platform.claude.com/docs/en/models/sonnet-4-6/overview
- API tool schema: https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools
