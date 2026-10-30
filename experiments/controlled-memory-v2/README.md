# Controlled external memory: can we impose distinct update rules?

Exploratory follow-up to the [first pilot](../functional-learning-v1/results/run-40969709564/README.md). The first pilot's wrong-rule prompt often elicited correct updating, and prose broke its strict parser. This run makes the memory manipulation executable and validates the downstream reader before comparing performance.

## Scope and question

**Primary question:** Does the same Claude reader use distinct externally computed memories faithfully, including the deliberately corrupted memory, and use them in several decisions?

This is a system integration and manipulation-validation experiment. Learning occurs in a programmer-specified external estimator. Claude reads its output. It does not learn weights or discover the update rule. Accurate probability readout is largely copying and is not itself evidence of learning. A successful run establishes a usable experimental platform; it does not establish EFLA novelty, an evolved module, or an internal IRV.

## Common world, different memories

Reuse the first pilot's world generator unchanged, with new seeds **1000–1007**. Eight paired independent worlds, two regimes, checkpoints of **0, 2, 8, 24** episodes per partner, four arms: **256 pilot requests**. Smoke fixtures use separate seeds 9000 and 9001, for **8 additional requests**. No selection of pilot seeds based on performance.

There are four partners and three settings, of which two appear in the histories. Voluntary attempts/declines inform inclination; success/failure among actual attempts informs execution. Assigned attempts give no choice evidence, and declines give no execution evidence. The shared world shares both quantities across settings. In the context-specific world only inclination varies by setting. Independent uniform priors are used for all distinct latent rates. Inclination is a voluntary-attempt probability, not a numerical WTR.

The updater reads each nested history and compresses it into a table containing two probability estimates per partner/setting. Counts have Beta(1,1) prior smoothing. Recomputing counts from a prefix is equivalent to adding the observations incrementally; the reader never sees the history, counts, arm label, regime, seed, checkpoint, reference output or true rates.

| Updater | Choice estimate | Execution estimate | Purpose |
|---|---|---|---|
| Functional | Pool voluntary choices across settings | Pool actual execution outcomes across settings | Proposed fixed decomposition and sharing |
| Local | Separate voluntary choices by setting | Pool actual execution outcomes | Correct routing without cross-setting choice transfer |
| Adaptive | Bayesian average of pooled and local choice estimates | Pool actual execution outcomes | Strong baseline that learns whether to share |
| Wrong routing | Pool execution outcomes, store as choice | Pool voluntary choices, store as execution | Enforced channel-swap negative control |

The adaptive model has equal prior weight on two world-level hypotheses: all partners share choice tendencies across settings, or each has independent setting-specific tendencies. Update the global hypothesis weight using all voluntary-choice observations across partners. Integrate each ordered Bernoulli sequence under Beta(1,1), without binomial multiplicity factors. Ability evidence cancels because its model is identical under both hypotheses. Predictions average posterior means with the posterior hypothesis probability. This is a well-specified Bayesian rival with knowledge of the candidate structures, **not** a domain-general learned architecture. It uses more internal statistics; equal output table size is not equal computational capacity.

All memories have the same table shape and semantic labels, rounded to six decimals. Wrong routing changes the values in code, rather than asking Claude to follow an implausible update instruction. Arm prompts differ only in the table values. Only the `body` field of a saved request is transmitted.

## Reader and decisions

Use `claude-sonnet-4-6`, temperature 0, thinking disabled, maximum 1536 output tokens. Use the Messages API's [JSON schema output format](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), with required numeric probability fields and Boolean decision fields. Numeric bounds, completeness, model identity, duplicate keys, and normal termination remain checked locally. No reasoning field, prose extraction, output repair, or retry.

Every fresh reader context receives the table and returns:

- 24 probabilities: each partner × each setting × choice/execution. These directly measure memory readout fidelity.
- 16 decisions: four per partner. Commission a voluntary delivery (success probability w×a), commission an assigned delivery (a), buy a backup (1−w×a), or book participation (w). Each pays a known upfront fee and receives a benefit of 10 on the relevant event. Declining gives zero; ties decline. Fees are sampled independently of true rates and fixed across arms, regimes and checkpoints. Settings rotate across decision types.

These decisions test using memories in distinct expected-value computations. They are deliberately simple and do not constitute four independent psychological constructs. The model is explicitly told how voluntary delivery probabilities compose. No claim of discovering that causal relation is possible.

Swapping w and a leaves their product unchanged. Therefore the voluntary-delivery and backup reference policies are exactly invariant to the channel swap; assigned-delivery and participation policies can change. This is a specificity check, not an expectation that every output should move together.

## Frozen validation and analysis

**Smoke gate:** collect all eight disjoint smoke requests first. Every response must parse strictly. For each request, every probability must be within **0.02** of its assigned table value, and at least **90%** of decisions must agree with the deterministic memory-based policy. For each wrong-routing fixture, prediction MSE to its assigned memory must be smaller than distance to correct pooled memory. Otherwise stop before any pilot request. This gate checks fidelity only; no comparative accuracy result selects whether to proceed.

**Primary pilot validation:** all 256 responses must be collected and valid. In each arm, at least 95% of requests must have every probability within 0.02 of its assigned memory, and mean decision agreement must be at least 90%. At least 95% of nonzero-budget wrong-rule requests with distinct correct/wrong references (reference MSE separation > 1e−8) must be closer to the assigned wrong memory. Report exact counts, maximum errors, and agreement, not just pass/fail. A failed manipulation blocks a claim that the study compared the implemented procedures successfully.

**Exploratory performance:** MSE against latent generating probabilities, split into seen choice, transfer choice and execution. Also expected decision regret in reward units: optimal expected payoff under true parameters minus the payoff of the selected action. Report learning curves for model outputs and deterministic memory-based policies separately. Code references are not model observations.

The main exploratory rival contrast is **adaptive minus functional**, averaged equally over nonzero checkpoints, separately in each regime. Also report local-minus-functional and wrong-minus-functional. Positive differences favor functional pooling. Use paired world-level bootstrap intervals (2,000 resamples), with seed as the replication unit; decisions, partners, regimes and checkpoints are not independent replications. Eight worlds, one model and one wording do not support a broad confirmatory claim. No superiority threshold or publication claim is attached to this pilot.

This is a prospective frozen exploratory protocol, not an external preregistration. Memory fidelity, rather than a favorable performance ranking, determines whether the experimental manipulation worked. Advantages of a correctly specified estimator in its own generator are expected; the adaptive baseline and mismatch condition expose boundaries, not proof of theoretical novelty.

## Execution and budget

```bash
python3 -m unittest discover -s tests -p test_controlled_memory.py -v
python3 experiments/controlled-memory-v2/experiment.py generate --out runs/controlled-memory-v2 --seeds 8
python3 runs/controlled-memory-v2/experiment.py collect --out runs/controlled-memory-v2 --budget-usd 25
python3 runs/controlled-memory-v2/experiment.py report --out runs/controlled-memory-v2
```

Generation freezes source, unchanged world generator, protocol, exact request bodies, hashes, and deterministic reference results. It makes no API calls. Collect/report use the frozen source. Credentials come from GitHub secret `WTR_BENCH` (fallback `ANTHROPIC_API_KEY`), exposed only as the process environment variable `ANTHROPIC_API_KEY`.

The collector has a **$25 local spending guard for all 264 requests together**, using a conservative byte-based input allowance plus the full output limit. Prices checked October 29, 2026: [$3 input / $15 output per million tokens](https://platform.claude.com/docs/en/about-claude/pricing). The exact allowance is printed in the manifest before collection; it is not a provider billing cap. Usage and raw responses are saved. Unexpected cache usage, incomplete output, schema failure, model mismatch, transport failure or missing usage stops further requests. No automatic retries. An exclusive ledger blocks reruns of the same directory; generating a new directory does not reset spending.

The dedicated branch `run/controlled-memory-v2-20261029` launches only with the exact commit message `Run controlled-memory-v2 pilot once`. The workflow refuses GitHub run attempts beyond the first and preserves artifacts even on failure. Ordinary pushes and pull requests do not spend credits. Never repeat the launch message to restart a partial run without inspecting its artifact.

No API observations have been collected at this protocol's creation. Deterministic tests and reference outputs must not be described as empirical model results.
